#!/usr/bin/env python3
"""Ingest a Teamcenter ReqIF XML export into Neo4j.

Parses OMG ReqIF v1.x files and creates:
  :ReqIFFile               — the source file
  :RequirementSpecification — the specification container
  :Requirement              — individual requirement objects
  :ReqIFDataType            — data type definitions

Relationships:
  (:ReqIFFile)-[:CONTAINS]->(:RequirementSpecification)
  (:RequirementSpecification)-[:CONTAINS_REQUIREMENT]->(:Requirement)
  (:Requirement)-[:CHILD_OF]->(:Requirement)   [hierarchy from SPEC-HIERARCHY]

Usage:
    python scripts/ingest_reqif.py "<path-to-reqif.xml>"
    python scripts/ingest_reqif.py "D:\...\Bearing_Req_01 (2022_08_05 01_07_01 UTC).xml"
"""
from __future__ import annotations

import os, sys, pathlib, argparse, re, uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

_backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

sys.stdout.reconfigure(line_buffering=True)

# Load .env
_env_file = _backend_dir.parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _k = _k.strip()
        if _k and _k not in os.environ:
            os.environ[_k] = _v.strip()

from neo4j import GraphDatabase


# ── XHTML text stripper ─────────────────────────────────────────────────

class _TextStripper(HTMLParser):
    """Extract plain text from XHTML fragments."""
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def strip_xhtml(xhtml: str) -> str:
    """Strip XHTML tags and return plain text."""
    s = _TextStripper()
    s.feed(xhtml)
    return s.get_text()


# ── ReqIF namespace ─────────────────────────────────────────────────────

REQIF_NS = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
XHTML_NS = "http://www.w3.org/1999/xhtml"

def _ns(tag: str) -> str:
    return f"{{{REQIF_NS}}}{tag}"

def _xns(tag: str) -> str:
    return f"{{{XHTML_NS}}}{tag}"


# ── Parser ───────────────────────────────────────────────────────────────

class ReqIFParser:
    """Parse a ReqIF file into structured dicts."""

    def __init__(self, filepath: str):
        self.filepath = pathlib.Path(filepath)
        self.tree = ET.parse(str(self.filepath))
        self.root = self.tree.getroot()
        # Handle namespace: the root might be {ns}REQ-IF or just REQ-IF
        self.ns = ""
        if self.root.tag.startswith("{"):
            self.ns = self.root.tag.split("}")[0] + "}"

        self.header: Dict[str, str] = {}
        self.datatypes: List[Dict[str, Any]] = []
        self.spec_types: List[Dict[str, Any]] = []
        self.spec_objects: Dict[str, Dict[str, Any]] = {}  # id -> object
        self.specifications: List[Dict[str, Any]] = []
        self.attr_defs: Dict[str, Dict[str, str]] = {}  # attr-def id -> {long_name, type}
        self.enum_values: Dict[str, str] = {}  # enum-value id -> long_name

    def _t(self, tag: str) -> str:
        """Namespace-qualified tag."""
        return f"{self.ns}{tag}"

    def parse(self):
        """Full parse of the ReqIF file."""
        self._parse_header()
        self._parse_datatypes()
        self._parse_spec_types()
        self._parse_spec_objects()
        self._parse_specifications()
        return self

    def _parse_header(self):
        header_el = self.root.find(f".//{self._t('REQ-IF-HEADER')}")
        if header_el is not None:
            self.header = {
                "identifier": header_el.get("IDENTIFIER", ""),
                "creation_time": self._child_text(header_el, "CREATION-TIME"),
                "tool_id": self._child_text(header_el, "REQ-IF-TOOL-ID"),
                "version": self._child_text(header_el, "REQ-IF-VERSION"),
                "source_tool": self._child_text(header_el, "SOURCE-TOOL-ID"),
                "title": self._child_text(header_el, "TITLE"),
            }

    def _child_text(self, el: ET.Element, tag: str) -> str:
        child = el.find(self._t(tag))
        return (child.text or "").strip() if child is not None else ""

    def _parse_datatypes(self):
        dt_container = self.root.find(f".//{self._t('DATATYPES')}")
        if dt_container is None:
            return
        for child in dt_container:
            tag = child.tag.replace(self.ns, "")
            dt = {
                "tag": tag,
                "identifier": child.get("IDENTIFIER", ""),
                "long_name": child.get("LONG-NAME", ""),
                "description": child.get("DESC", ""),
            }
            # Parse enum values
            if "ENUMERATION" in tag:
                for ev in child.findall(f".//{self._t('ENUM-VALUE')}"):
                    ev_id = ev.get("IDENTIFIER", "")
                    ev_name = ev.get("LONG-NAME", "")
                    self.enum_values[ev_id] = ev_name
                    dt.setdefault("values", []).append({"id": ev_id, "name": ev_name})
            self.datatypes.append(dt)

    def _parse_spec_types(self):
        st_container = self.root.find(f".//{self._t('SPEC-TYPES')}")
        if st_container is None:
            return
        for child in st_container:
            tag = child.tag.replace(self.ns, "")
            st = {
                "tag": tag,
                "identifier": child.get("IDENTIFIER", ""),
                "long_name": child.get("LONG-NAME", ""),
            }
            # Parse attribute definitions
            attrs_container = child.find(self._t("SPEC-ATTRIBUTES"))
            if attrs_container is None:
                # Try without namespace prefix for SPEC-ATTRIBUTES
                for possible in child:
                    ptag = possible.tag.replace(self.ns, "")
                    if "ATTRIBUTE-DEFINITION" in ptag:
                        attr_id = possible.get("IDENTIFIER", "")
                        attr_name = possible.get("LONG-NAME", "")
                        self.attr_defs[attr_id] = {"long_name": attr_name, "type": ptag}
            else:
                for attr_el in attrs_container:
                    attr_id = attr_el.get("IDENTIFIER", "")
                    attr_name = attr_el.get("LONG-NAME", "")
                    attr_tag = attr_el.tag.replace(self.ns, "")
                    self.attr_defs[attr_id] = {"long_name": attr_name, "type": attr_tag}
            self.spec_types.append(st)

    def _parse_spec_objects(self):
        so_container = self.root.find(f".//{self._t('SPEC-OBJECTS')}")
        if so_container is None:
            return
        for so_el in so_container:
            so_id = so_el.get("IDENTIFIER", "")
            so_name = so_el.get("LONG-NAME", "")

            # Parse VALUES
            props: Dict[str, str] = {}
            values_el = so_el.find(self._t("VALUES"))
            if values_el is not None:
                for val in values_el:
                    val_tag = val.tag.replace(self.ns, "")
                    # Get the attribute definition reference
                    def_el = val.find(f".//{self._t('DEFINITION')}")
                    attr_ref = ""
                    if def_el is not None:
                        for ref_child in def_el:
                            attr_ref = ref_child.text or ""
                    attr_name = self.attr_defs.get(attr_ref, {}).get("long_name", attr_ref)

                    if "XHTML" in val_tag:
                        # Extract XHTML content
                        the_value_el = val.find(self._t("THE-VALUE"))
                        if the_value_el is not None:
                            xhtml_text = ET.tostring(the_value_el, encoding="unicode", method="html")
                            props[attr_name] = strip_xhtml(xhtml_text)
                    elif "ENUMERATION" in val_tag:
                        # Enum value reference
                        enum_refs = val.findall(f".//{self._t('ENUM-VALUE-REF')}")
                        vals = [self.enum_values.get(er.text or "", er.text or "") for er in enum_refs]
                        props[attr_name] = ", ".join(vals) if vals else val.get("THE-VALUE", "")
                    else:
                        props[attr_name] = val.get("THE-VALUE", "")

            # Determine spec-object type
            type_el = so_el.find(f".//{self._t('TYPE')}")
            obj_type = ""
            if type_el is not None:
                for ref_child in type_el:
                    obj_type = ref_child.text or ""

            self.spec_objects[so_id] = {
                "identifier": so_id,
                "long_name": so_name,
                "type": obj_type,
                "properties": props,
            }

    def _parse_specifications(self):
        spec_container = self.root.find(f".//{self._t('SPECIFICATIONS')}")
        if spec_container is None:
            return
        for spec_el in spec_container:
            spec_id = spec_el.get("IDENTIFIER", "")
            spec_name = spec_el.get("LONG-NAME", "")

            # Parse VALUES for spec
            spec_props: Dict[str, str] = {}
            values_el = spec_el.find(self._t("VALUES"))
            if values_el is not None:
                for val in values_el:
                    val_tag = val.tag.replace(self.ns, "")
                    def_el = val.find(f".//{self._t('DEFINITION')}")
                    attr_ref = ""
                    if def_el is not None:
                        for ref_child in def_el:
                            attr_ref = ref_child.text or ""
                    attr_name = self.attr_defs.get(attr_ref, {}).get("long_name", attr_ref)
                    props_val = val.get("THE-VALUE", "")
                    if props_val:
                        spec_props[attr_name] = props_val

            # Parse hierarchy (CHILDREN)
            hierarchy = self._parse_hierarchy(spec_el)

            self.specifications.append({
                "identifier": spec_id,
                "long_name": spec_name,
                "properties": spec_props,
                "hierarchy": hierarchy,
            })

    def _parse_hierarchy(self, parent_el: ET.Element) -> List[Dict[str, Any]]:
        """Recursively parse SPEC-HIERARCHY elements from CHILDREN."""
        result = []
        children_el = parent_el.find(self._t("CHILDREN"))
        if children_el is None:
            return result
        for sh_el in children_el:
            sh_tag = sh_el.tag.replace(self.ns, "")
            if "SPEC-HIERARCHY" not in sh_tag:
                continue
            sh_id = sh_el.get("IDENTIFIER", "")
            # Get the OBJECT reference
            obj_el = sh_el.find(f".//{self._t('OBJECT')}")
            obj_ref = ""
            if obj_el is not None:
                for ref_child in obj_el:
                    obj_ref = ref_child.text or ""
            sub_children = self._parse_hierarchy(sh_el)
            result.append({
                "hierarchy_id": sh_id,
                "object_ref": obj_ref,
                "children": sub_children,
            })
        return result


# ── Neo4j Ingester ───────────────────────────────────────────────────────

class ReqIFNeo4jIngester:
    """Ingest parsed ReqIF data into Neo4j."""

    def __init__(self, driver, database: str = "mossec"):
        self.driver = driver
        self.database = database
        self.stats = {
            "reqif_file": 0,
            "specifications": 0,
            "requirements": 0,
            "contains_req_links": 0,
            "hierarchy_links": 0,
        }

    def run(self, cypher: str, params: dict = None) -> list:
        with self.driver.session(database=self.database) as s:
            result = s.run(cypher, params or {})
            return [r.data() for r in result]

    def ingest(self, parser: ReqIFParser, source_label: str = ""):
        filename = parser.filepath.name
        label = source_label or filename

        print(f"\nIngesting ReqIF: {filename}")
        print(f"  Tool: {parser.header.get('source_tool', 'unknown')}")
        print(f"  Title: {parser.header.get('title', 'N/A')}")
        print(f"  Spec objects: {len(parser.spec_objects)}")
        print(f"  Specifications: {len(parser.specifications)}")

        # 1. Create the ReqIFFile node
        self.run("""
            MERGE (f:ReqIFFile {filename: $filename})
            SET f.label = $label,
                f.source_tool = $source_tool,
                f.reqif_version = $reqif_version,
                f.creation_time = $creation_time,
                f.title = $title,
                f.ingested_at = datetime(),
                f.source = 'reqif_ingester'
            RETURN f.filename AS fn
        """, {
            "filename": filename,
            "label": label,
            "source_tool": parser.header.get("source_tool", ""),
            "reqif_version": parser.header.get("version", ""),
            "creation_time": parser.header.get("creation_time", ""),
            "title": parser.header.get("title", ""),
        })
        self.stats["reqif_file"] = 1
        print(f"  Created :ReqIFFile node")

        # 2. Create RequirementSpecification nodes
        for spec in parser.specifications:
            spec_name = spec["long_name"]
            spec_id = spec["identifier"]
            spec_props = spec["properties"]

            self.run("""
                MERGE (s:RequirementSpecification {identifier: $spec_id})
                SET s.name = $name,
                    s.revision = $revision,
                    s.creation_date = $creation_date,
                    s.date_modified = $date_modified,
                    s.source = 'reqif_ingester',
                    s.source_file = $filename,
                    s.ingested_at = datetime()
            """, {
                "spec_id": spec_id,
                "name": spec_name,
                "revision": spec_props.get("Revision", ""),
                "creation_date": spec_props.get("Creation Date", ""),
                "date_modified": spec_props.get("Date Modified", ""),
                "filename": filename,
            })

            # Link to ReqIFFile
            self.run("""
                MATCH (f:ReqIFFile {filename: $filename})
                MATCH (s:RequirementSpecification {identifier: $spec_id})
                MERGE (f)-[:CONTAINS]->(s)
            """, {"filename": filename, "spec_id": spec_id})

            self.stats["specifications"] += 1
            print(f"  Created :RequirementSpecification '{spec_name}'")

            # 3. Create Requirement nodes from hierarchies
            for idx, h_item in enumerate(spec["hierarchy"], start=1):
                self._create_requirement_from_hierarchy(
                    h_item, spec_id, filename, idx, parser, parent_id=None
                )

        print(f"\n  Summary:")
        print(f"    ReqIF file:       {self.stats['reqif_file']}")
        print(f"    Specifications:   {self.stats['specifications']}")
        print(f"    Requirements:     {self.stats['requirements']}")
        print(f"    Spec-Req links:   {self.stats['contains_req_links']}")
        print(f"    Hierarchy links:  {self.stats['hierarchy_links']}")

    def _create_requirement_from_hierarchy(
        self, h_item: dict, spec_id: str, filename: str,
        order: int, parser: ReqIFParser, parent_id: Optional[str]
    ):
        obj_ref = h_item["object_ref"]
        spec_obj = parser.spec_objects.get(obj_ref)
        if not spec_obj:
            print(f"    WARNING: hierarchy references unknown object {obj_ref}")
            return

        req_name = spec_obj["long_name"]
        props = spec_obj["properties"]

        # Generate a stable requirement ID
        req_id = f"BREQ-{order:02d}"

        # Extract text description from ReqIF.Text property
        description = props.get("ReqIF.Text", props.get("Description", ""))
        revision = props.get("Revision", "")

        self.run("""
            MERGE (r:Requirement {id: $req_id})
            SET r.name = $name,
                r.description = $description,
                r.revision = $revision,
                r.reqif_identifier = $reqif_id,
                r.source = 'ReqIF',
                r.source_file = $filename,
                r.source_tool = 'Teamcenter',
                r.type = 'Bearing',
                r.status = 'Approved',
                r.priority = 'High',
                r.ap_schema = 'AP239',
                r.ap_level = 'AP239',
                r.sort_order = $sort_order,
                r.ingested_at = datetime()
        """, {
            "req_id": req_id,
            "name": req_name,
            "description": description,
            "revision": revision,
            "reqif_id": obj_ref,
            "filename": filename,
            "sort_order": order,
        })

        # Link to specification
        self.run("""
            MATCH (s:RequirementSpecification {identifier: $spec_id})
            MATCH (r:Requirement {id: $req_id})
            MERGE (s)-[:CONTAINS_REQUIREMENT {sort_order: $order}]->(r)
        """, {"spec_id": spec_id, "req_id": req_id, "order": order})
        self.stats["requirements"] += 1
        self.stats["contains_req_links"] += 1

        # If there's a parent, create hierarchy link
        if parent_id:
            self.run("""
                MATCH (child:Requirement {id: $child_id})
                MATCH (parent:Requirement {id: $parent_id})
                MERGE (child)-[:CHILD_OF]->(parent)
            """, {"child_id": req_id, "parent_id": parent_id})
            self.stats["hierarchy_links"] += 1

        # Recurse into children
        for sub_order, sub_item in enumerate(h_item.get("children", []), start=1):
            self._create_requirement_from_hierarchy(
                sub_item, spec_id, filename, order * 100 + sub_order,
                parser, parent_id=req_id,
            )


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Ingest ReqIF XML into Neo4j")
    ap.add_argument("file", help="Path to the ReqIF XML file")
    ap.add_argument("--label", default="", help="Optional display label")
    args = ap.parse_args()

    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "tcs12345")
    db = os.environ.get("NEO4J_DATABASE", "mossec")

    filepath = pathlib.Path(args.file)
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    print(f"ReqIF Ingestion")
    print(f"  File: {filepath}")
    print(f"  Neo4j: {uri}, database={db}")
    print("=" * 60)

    # Parse
    parser = ReqIFParser(str(filepath))
    parser.parse()

    # Ingest
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        ingester = ReqIFNeo4jIngester(driver, database=db)
        ingester.ingest(parser, source_label=args.label or filepath.stem)
    finally:
        driver.close()

    print("\n" + "=" * 60)
    print("ReqIF ingestion complete.")


if __name__ == "__main__":
    main()
