"""AP242 Semantic Decomposition Service.

Extracts higher-level product structure from raw StepInstance nodes:
  - :AP242Product       -- from PRODUCT entities (part numbers, names)
  - :AP242Assembly      -- from NEXT_ASSEMBLY_USAGE_OCCURRENCE (BOM)
  - :AP242Shape         -- from SHAPE_REPRESENTATION (geometry metadata)

This creates semantic nodes that bridge the raw STEP instance graph to the
MBSE domain knowledge graph (Part, Assembly, Requirement nodes).

Usage:
    python backend/scripts/ap242_semantic_decomposition.py
    python backend/scripts/ap242_semantic_decomposition.py --dry-run
"""

from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from neo4j import GraphDatabase
from loguru import logger

# ──────────────────────────────────────────────────────────────────────
# Helpers: lightweight Part-21 argument parsing
# ──────────────────────────────────────────────────────────────────────

def _split_top_level_args(raw_args: str) -> list[str]:
    """Split comma-separated top-level STEP arguments.
    
    Respects nested parens and single-quoted strings.
    """
    parts: list[str] = []
    depth = 0
    in_string = False
    buf: list[str] = []
    
    for ch in raw_args:
        if ch == "'" and not in_string:
            in_string = True
            buf.append(ch)
        elif ch == "'" and in_string:
            in_string = False
            buf.append(ch)
        elif in_string:
            buf.append(ch)
        elif ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth -= 1
            buf.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    
    if buf:
        parts.append(''.join(buf).strip())
    return parts


def _unquote(s: str) -> str | None:
    """Remove surrounding single quotes. Returns None for $ or *."""
    s = s.strip()
    if s in ('$', '*', ''):
        return None
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    return s


def _extract_refs(s: str) -> list[int]:
    """Extract #NNN references from a string."""
    return [int(m.group(1)) for m in re.finditer(r'#(\d+)', s)]


# ──────────────────────────────────────────────────────────────────────
# Semantic decomposer
# ──────────────────────────────────────────────────────────────────────

class AP242SemanticDecomposer:
    """Extract AP242 product structure from raw StepInstance nodes."""

    def __init__(self, driver, database: str, dry_run: bool = False):
        self.driver = driver
        self.database = database
        self.dry_run = dry_run
        self.stats: dict[str, int] = {}

    def run_q(self, q: str, params: dict | None = None) -> list[dict]:
        if self.dry_run:
            logger.debug(f"[DRY-RUN] {q[:80]}")
            return [{"cnt": 0}]
        with self.driver.session(database=self.database) as s:
            return [r.data() for r in s.run(q, params or {})]

    def run_all(self):
        """Execute all decomposition steps."""
        self.extract_products()
        self.extract_product_definitions()
        self.extract_assembly_structure()
        self.extract_shape_representations()
        self.extract_property_definitions()
        self.link_products_to_parts()
        self.print_summary()

    # ──────────────────────────────────────────────────
    # Step 1: PRODUCT → :AP242Product
    # ──────────────────────────────────────────────────
    def extract_products(self):
        """Extract PRODUCT entities → :AP242Product nodes.
        
        PRODUCT(id, name, description, (context_refs))
        """
        logger.info("Step 1: Extracting PRODUCT → :AP242Product")
        
        rows = self.run_q("""
            MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'PRODUCT'})
            MATCH (f:StepFile)-[:CONTAINS]->(si)
            RETURN si.raw_args AS args, si.step_id AS sid, si.file_uri AS furi,
                   f.name AS fname, elementId(si) AS si_eid
        """)
        
        created = 0
        for row in rows:
            parts = _split_top_level_args(row['args'])
            if len(parts) < 3:
                continue
            
            product_id = _unquote(parts[0]) or ''
            product_name = _unquote(parts[1]) or ''
            description = _unquote(parts[2]) or ''
            
            if not product_name:
                continue
            
            self.run_q("""
                MERGE (p:AP242Product {product_id: $pid, file_uri: $furi})
                SET p.name = $name,
                    p.description = $desc,
                    p.step_id = $sid,
                    p.source_file = $fname,
                    p.ap_level = 'AP242',
                    p.updated_on = datetime()
                WITH p
                MATCH (si:StepInstance {file_uri: $furi, step_id: $sid})
                MERGE (p)-[:DERIVED_FROM]->(si)
            """, {
                'pid': product_id,
                'furi': row['furi'],
                'name': product_name,
                'desc': description,
                'sid': row['sid'],
                'fname': row['fname'],
            })
            created += 1
        
        self.stats['ap242_products'] = created
        logger.info(f"  Created {created} AP242Product nodes")

    # ──────────────────────────────────────────────────
    # Step 2: PRODUCT_DEFINITION → :AP242ProductDefinition
    # ──────────────────────────────────────────────────
    def extract_product_definitions(self):
        """Extract PRODUCT_DEFINITION → :AP242ProductDefinition.
        
        PRODUCT_DEFINITION(id, description, formation_ref, context_ref)
        Links to the PRODUCT via PRODUCT_DEFINITION_FORMATION.
        """
        logger.info("Step 2: Extracting PRODUCT_DEFINITION → :AP242ProductDefinition")
        
        rows = self.run_q("""
            MATCH (si:StepInstance)-[:INSTANCE_OF]->(t:StepEntityType {name: 'PRODUCT_DEFINITION'})
            MATCH (f:StepFile)-[:CONTAINS]->(si)
            RETURN si.raw_args AS args, si.step_id AS sid, si.file_uri AS furi, f.name AS fname
        """)
        
        created = 0
        for row in rows:
            parts = _split_top_level_args(row['args'])
            if len(parts) < 4:
                continue
            
            pd_id = _unquote(parts[0]) or ''
            description = _unquote(parts[1]) or ''
            formation_refs = _extract_refs(parts[2])
            context_refs = _extract_refs(parts[3])
            
            formation_sid = formation_refs[0] if formation_refs else None
            
            self.run_q("""
                MERGE (pd:AP242ProductDefinition {file_uri: $furi, step_id: $sid})
                SET pd.pd_id = $pd_id,
                    pd.description = $desc,
                    pd.source_file = $fname,
                    pd.ap_level = 'AP242',
                    pd.updated_on = datetime()
                WITH pd
                MATCH (si:StepInstance {file_uri: $furi, step_id: $sid})
                MERGE (pd)-[:DERIVED_FROM]->(si)
            """, {
                'furi': row['furi'],
                'sid': row['sid'],
                'pd_id': pd_id,
                'desc': description,
                'fname': row['fname'],
            })
            created += 1
            
            # Link to AP242Product via formation reference chain
            if formation_sid:
                self.run_q("""
                    MATCH (pd:AP242ProductDefinition {file_uri: $furi, step_id: $sid})
                    MATCH (form_si:StepInstance {file_uri: $furi, step_id: $form_sid})
                    -[:STEP_REF]->(prod_si:StepInstance)
                    -[:INSTANCE_OF]->(:StepEntityType {name: 'PRODUCT'})
                    MATCH (p:AP242Product {file_uri: $furi})-[:DERIVED_FROM]->(prod_si)
                    MERGE (pd)-[:DEFINES_PRODUCT]->(p)
                """, {
                    'furi': row['furi'],
                    'sid': row['sid'],
                    'form_sid': formation_sid,
                })
        
        self.stats['ap242_product_defs'] = created
        logger.info(f"  Created {created} AP242ProductDefinition nodes")

    # ──────────────────────────────────────────────────
    # Step 3: NEXT_ASSEMBLY_USAGE_OCCURRENCE → assembly hierarchy
    # ──────────────────────────────────────────────────
    def extract_assembly_structure(self):
        """Extract assembly BOM from NEXT_ASSEMBLY_USAGE_OCCURRENCE.
        
        NAUO(id, name, description, relating_pd_ref, related_pd_ref, ref_designator)
        Creates :ASSEMBLES relationships between AP242ProductDefinition nodes.
        """
        logger.info("Step 3: Extracting assembly structure from NAUO")
        
        rows = self.run_q("""
            MATCH (si:StepInstance)-[:INSTANCE_OF]->
                  (t:StepEntityType {name: 'NEXT_ASSEMBLY_USAGE_OCCURRENCE'})
            MATCH (f:StepFile)-[:CONTAINS]->(si)
            RETURN si.raw_args AS args, si.step_id AS sid, si.file_uri AS furi, f.name AS fname
        """)
        
        created = 0
        for row in rows:
            parts = _split_top_level_args(row['args'])
            if len(parts) < 5:
                continue
            
            nauo_id = _unquote(parts[0]) or ''
            component_name = _unquote(parts[1]) or nauo_id
            description = _unquote(parts[2]) or ''
            parent_refs = _extract_refs(parts[3])  # relating product_definition
            child_refs = _extract_refs(parts[4])   # related product_definition
            
            parent_sid = parent_refs[0] if parent_refs else None
            child_sid = child_refs[0] if child_refs else None
            
            if not parent_sid or not child_sid:
                continue
            
            # Create the assembly relationship via raw StepInstance references
            # Also create :AP242AssemblyOccurrence node for the component
            self.run_q("""
                MERGE (ao:AP242AssemblyOccurrence {file_uri: $furi, step_id: $sid})
                SET ao.name = $name,
                    ao.description = $desc,
                    ao.nauo_id = $nauo_id,
                    ao.source_file = $fname,
                    ao.ap_level = 'AP242',
                    ao.parent_step_id = $parent_sid,
                    ao.child_step_id = $child_sid,
                    ao.updated_on = datetime()
                WITH ao
                MATCH (si:StepInstance {file_uri: $furi, step_id: $sid})
                MERGE (ao)-[:DERIVED_FROM]->(si)
            """, {
                'furi': row['furi'],
                'sid': row['sid'],
                'name': component_name,
                'desc': description,
                'nauo_id': nauo_id,
                'fname': row['fname'],
                'parent_sid': parent_sid,
                'child_sid': child_sid,
            })
            created += 1
            
            # Link parent → child via PRODUCT_DEFINITION references
            self.run_q("""
                MATCH (ao:AP242AssemblyOccurrence {file_uri: $furi, step_id: $sid})
                OPTIONAL MATCH (parent_pd:AP242ProductDefinition {file_uri: $furi, step_id: $parent_sid})
                OPTIONAL MATCH (child_pd:AP242ProductDefinition {file_uri: $furi, step_id: $child_sid})
                FOREACH (_ IN CASE WHEN parent_pd IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (ao)-[:PARENT_ASSEMBLY]->(parent_pd))
                FOREACH (_ IN CASE WHEN child_pd IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (ao)-[:CHILD_COMPONENT]->(child_pd))
            """, {
                'furi': row['furi'],
                'sid': row['sid'],
                'parent_sid': parent_sid,
                'child_sid': child_sid,
            })
        
        self.stats['ap242_assembly_occurrences'] = created
        logger.info(f"  Created {created} AP242AssemblyOccurrence nodes")

    # ──────────────────────────────────────────────────
    # Step 4: SHAPE_REPRESENTATION → :AP242Shape
    # ──────────────────────────────────────────────────
    def extract_shape_representations(self):
        """Extract SHAPE_REPRESENTATION → :AP242Shape.
        
        SHAPE_REPRESENTATION(name, items_list, context_ref)
        """
        logger.info("Step 4: Extracting SHAPE_REPRESENTATION → :AP242Shape")
        
        rows = self.run_q("""
            MATCH (si:StepInstance)-[:INSTANCE_OF]->
                  (t:StepEntityType {name: 'SHAPE_REPRESENTATION'})
            MATCH (f:StepFile)-[:CONTAINS]->(si)
            RETURN si.raw_args AS args, si.step_id AS sid, si.file_uri AS furi, f.name AS fname
        """)
        
        created = 0
        for row in rows:
            parts = _split_top_level_args(row['args'])
            if len(parts) < 2:
                continue
            
            shape_name = _unquote(parts[0]) or 'unnamed_shape'
            
            self.run_q("""
                MERGE (sh:AP242Shape {file_uri: $furi, step_id: $sid})
                SET sh.name = $name,
                    sh.source_file = $fname,
                    sh.ap_level = 'AP242',
                    sh.updated_on = datetime()
                WITH sh
                MATCH (si:StepInstance {file_uri: $furi, step_id: $sid})
                MERGE (sh)-[:DERIVED_FROM]->(si)
            """, {
                'furi': row['furi'],
                'sid': row['sid'],
                'name': shape_name,
                'fname': row['fname'],
            })
            created += 1
        
        # Link shapes to product definitions via SHAPE_DEFINITION_REPRESENTATION
        linked = self.run_q("""
            MATCH (sdr_si:StepInstance)-[:INSTANCE_OF]->
                  (:StepEntityType {name: 'SHAPE_DEFINITION_REPRESENTATION'})
            MATCH (sdr_si)-[:STEP_REF]->(shape_si:StepInstance)
                  -[:INSTANCE_OF]->(:StepEntityType {name: 'SHAPE_REPRESENTATION'})
            MATCH (sdr_si)-[:STEP_REF]->(pds_si:StepInstance)
                  -[:INSTANCE_OF]->(:StepEntityType {name: 'PRODUCT_DEFINITION_SHAPE'})
            MATCH (pds_si)-[:STEP_REF]->(pd_si:StepInstance)
                  -[:INSTANCE_OF]->(:StepEntityType {name: 'PRODUCT_DEFINITION'})
            MATCH (sh:AP242Shape)-[:DERIVED_FROM]->(shape_si)
            MATCH (pd:AP242ProductDefinition)-[:DERIVED_FROM]->(pd_si)
            MERGE (pd)-[:HAS_SHAPE]->(sh)
            RETURN count(*) AS cnt
        """)
        link_count = linked[0]['cnt'] if linked else 0
        
        self.stats['ap242_shapes'] = created
        self.stats['pd_shape_links'] = link_count
        logger.info(f"  Created {created} AP242Shape nodes, {link_count} PD→Shape links")

    # ──────────────────────────────────────────────────
    # Step 5: PROPERTY_DEFINITION → property nodes
    # ──────────────────────────────────────────────────
    def extract_property_definitions(self):
        """Extract PROPERTY_DEFINITION summary stats (too many to create individual nodes).
        
        Instead, count properties per product and add as metadata.
        """
        logger.info("Step 5: Counting PROPERTY_DEFINITION per product")
        
        result = self.run_q("""
            MATCH (prop_si:StepInstance)-[:INSTANCE_OF]->
                  (:StepEntityType {name: 'PROPERTY_DEFINITION'})
            MATCH (f:StepFile)-[:CONTAINS]->(prop_si)
            RETURN f.name AS fname, count(prop_si) AS cnt
            ORDER BY cnt DESC
        """)
        
        total = sum(r['cnt'] for r in result)
        self.stats['property_definitions'] = total
        logger.info(f"  Found {total} PROPERTY_DEFINITION instances across {len(result)} files")
        for r in result[:5]:
            logger.info(f"    {r['fname']}: {r['cnt']} properties")

    # ──────────────────────────────────────────────────
    # Step 6: Link AP242 products to existing :Part nodes
    # ──────────────────────────────────────────────────
    def link_products_to_parts(self):
        """Link AP242Product nodes to existing :Part nodes by name similarity."""
        logger.info("Step 6: Linking AP242Product → Part/Assembly nodes")
        
        # Direct name match
        result = self.run_q("""
            MATCH (p:AP242Product)
            MATCH (part:Part)
            WHERE toLower(p.name) CONTAINS toLower(part.name) 
               OR toLower(part.name) CONTAINS toLower(p.name)
            MERGE (p)-[:MAPS_TO_PART]->(part)
            RETURN count(*) AS cnt
        """)
        cnt = result[0]['cnt'] if result else 0
        self.stats['product_part_links'] = cnt
        logger.info(f"  Linked {cnt} AP242Product → Part nodes")
        
        # Link AP242Product to existing Assembly
        result = self.run_q("""
            MATCH (p:AP242Product)
            MATCH (a:Assembly)
            WHERE toLower(p.name) CONTAINS toLower(a.name) 
               OR toLower(a.name) CONTAINS toLower(p.name)
            MERGE (p)-[:MAPS_TO_ASSEMBLY]->(a)
            RETURN count(*) AS cnt
        """)
        cnt2 = result[0]['cnt'] if result else 0
        self.stats['product_assembly_links'] = cnt2
        logger.info(f"  Linked {cnt2} AP242Product → Assembly nodes")

    def print_summary(self):
        logger.info("=" * 60)
        logger.info("AP242 Semantic Decomposition Summary")
        logger.info("=" * 60)
        for k, v in self.stats.items():
            logger.info(f"  {k:40s}: {v}")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="AP242 Semantic Decomposition")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    pwd = os.environ.get('NEO4J_PASSWORD', 'tcs12345')
    db = os.environ.get('NEO4J_DATABASE', 'mossec')

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    logger.info(f"Connected to {uri}, database={db}")

    decomposer = AP242SemanticDecomposer(driver, db, dry_run=args.dry_run)
    decomposer.run_all()

    driver.close()
    logger.info("Done.")


if __name__ == "__main__":
    main()
