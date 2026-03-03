"""Teamcenter PLMXML ingestion service.

Parses PLMXML v4/v5/v6 exports from Siemens Teamcenter and serializes the
complete object model into Neo4j as a typed property graph.

Supported source formats
------------------------
- PLMXML v5  (xmlns="http://www.plmxml.org/Schemas/PLMXMLSchema")
- PLMXML v6  (same namespace, different schemaVersion attribute)
- Namespace-free PLMXML (older TC exports)

Node labels created
-------------------
  :PLMXMLFile      — the PLMXML file itself
  :PLMXMLItem      — TC Item (Part, Assembly, Document, …)
  :PLMXMLRevision  — TC ItemRevision
  :PLMXMLBOMLine   — BOMViewOccurrence / OccurrenceGroup
  :PLMXMLDataSet   — Dataset attached to a revision (UGMASTER, DirectModel, PDF, …)

Traceability edges
------------------
  (:PLMXMLFile)      -[:CONTAINS]->         (:PLMXMLItem)
  (:PLMXMLItem)      -[:HAS_REVISION]->      (:PLMXMLRevision)
  (:PLMXMLRevision)  -[:HAS_BOM_LINE]->      (:PLMXMLBOMLine)
  (:PLMXMLBOMLine)   -[:REFERENCES]->        (:PLMXMLItem)
  (:PLMXMLRevision)  -[:HAS_DATASET]->       (:PLMXMLDataSet)
  (:PLMXMLDataSet)   -[:LINKED_STEP_FILE]->> (:StepFile)   [if STEP file already ingested]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from loguru import logger

from src.web.services import get_neo4j_service

# Lazy imports for optional embedding/vector dependencies
_embeddings_instance = None
_vectorstore_instance = None


def _get_embeddings():
    """Lazy-load OllamaEmbeddings to avoid import failure when Ollama is down."""
    global _embeddings_instance
    if _embeddings_instance is None:
        from src.agents.embeddings_ollama import OllamaEmbeddings
        _embeddings_instance = OllamaEmbeddings()
    return _embeddings_instance


def _get_vectorstore():
    """Lazy-load ElasticsearchVectorStore."""
    global _vectorstore_instance
    if _vectorstore_instance is None:
        from src.agents.vectorstore_es import ElasticsearchVectorStore
        _vectorstore_instance = ElasticsearchVectorStore()
    return _vectorstore_instance


# ---------------------------------------------------------------------------
# PLMXML namespace helpers
# ---------------------------------------------------------------------------

_PLMXML_NS_V5 = "http://www.plmxml.org/Schemas/PLMXMLSchema"
_PLMXML_NS_RE = re.compile(r"\{([^}]*plmxml[^}]*)\}", re.IGNORECASE)

_TAG_ALIASES = {
    # canonical tag → list of localnames (without namespace) to try
    "Item":                ["Item"],
    "ItemRevision":        ["ItemRevision"],
    "BOMViewOccurrence":   ["BOMViewOccurrence", "OccurrenceGroup", "Occurrence"],
    "BOMView":             ["BOMView", "BOMViewRevision"],
    "DataSet":             ["DataSet"],
    "UserData":            ["UserData"],
    "UserValue":           ["UserValue"],
    "ExternalFile":        ["ExternalFile"],
    "ProductDef":          ["ProductDef", "Product"],
}


def _ns(tag: str, ns: str) -> str:
    """Build {namespace}Tag string."""
    return f"{{{ns}}}{tag}" if ns else tag


def _detect_ns(root: ET.Element) -> str:
    """Return the PLMXML namespace or empty string for namespace-free files."""
    m = _PLMXML_NS_RE.match(root.tag)
    return m.group(1) if m else ""


def _local(tag: str) -> str:
    """Strip namespace from a tag like {http://...}Item → Item."""
    return tag.split("}")[-1] if "}" in tag else tag


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PLMXMLFileMeta:
    schema_version: str
    date: str
    author: str
    source_system: str


@dataclass
class PLMXMLItemRow:
    uid: str           # PLMXML id= attribute
    item_id: str       # itemId= attribute (TC item number)
    name: str
    item_type: str     # Part / Assembly / Document / …
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class PLMXMLRevisionRow:
    uid: str
    parent_item_uid: str
    revision: str
    name: str
    status: str
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class PLMXMLBOMLineRow:
    uid: str
    parent_rev_uid: str
    ref_uid: str       # points to PLMXMLItem uid (idref)
    quantity: float
    find_num: str
    unit: str
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class PLMXMLDataSetRow:
    uid: str
    parent_rev_uid: str
    name: str
    ds_type: str       # UGMASTER, DirectModel, PDF, …
    member: str        # filename / member string
    external_files: List[str] = field(default_factory=list)


@dataclass
class PLMXMLIngestResult:
    file_uri: str
    schema_version: str
    items_upserted: int
    revisions_upserted: int
    bom_lines_upserted: int
    datasets_upserted: int
    step_links_created: int
    classified_count: int = 0
    unclassified_count: int = 0
    vectors_indexed: int = 0
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class PLMXMLIngestConfig:
    batch_size: int = 200
    create_step_links: bool = True   # link DataSets to :StepFile nodes when name matches


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class _PLMXMLParser:
    """
    Event-style walker over an ElementTree root.
    Handles both namespaced and non-namespaced PLMXML files.
    Builds flat lists of typed row objects for batch Neo4j upsert.
    """

    def __init__(self, root: ET.Element):
        self.root = root
        self.ns = _detect_ns(root)
        self.file_meta = self._parse_meta()

    # -- meta ----------------------------------------------------------------

    def _parse_meta(self) -> PLMXMLFileMeta:
        r = self.root
        return PLMXMLFileMeta(
            schema_version=r.get("schemaVersion", r.get("version", "unknown")),
            date=r.get("date", ""),
            author=r.get("author", ""),
            source_system=r.get("sourceSystem", "Teamcenter"),
        )

    # -- helpers -------------------------------------------------------------

    def _tag(self, local: str) -> str:
        return _ns(local, self.ns)

    def _iter_local(self, parent: ET.Element, *local_names: str):
        """Yield child elements matching any of the given local tag names."""
        for child in parent:
            if _local(child.tag) in local_names:
                yield child

    def _user_data(self, element: ET.Element) -> Dict[str, str]:
        """Collect <UserData><UserValue title="X" value="Y"/></UserData> pairs."""
        attrs: Dict[str, str] = {}
        for ud in self._iter_local(element, "UserData"):
            for uv in self._iter_local(ud, "UserValue"):
                title = uv.get("title") or uv.get("name")
                value = uv.get("value") or uv.get("displayValue") or uv.text or ""
                if title:
                    attrs[title] = value
        return attrs

    def _resolve_idref(self, idref: str) -> str:
        """Normalise an IDREF (strip leading #)."""
        return idref.lstrip("#") if idref else ""

    def _iter_items(self) -> List[PLMXMLItemRow]:
        items: List[PLMXMLItemRow] = []
        for el in self.root.iter():
            local = _local(el.tag)
            # v4/v5: <Item>, v6: <Product>
            if local not in ("Item", "Product"):
                continue
            uid = el.get("id", "")
            if not uid:
                continue
            # v4 uses itemId, type; v6 uses productId, subType
            item_id = (
                el.get("itemId")
                or el.get("productId")
                or el.get("id_display", uid)
            )
            item_type = (
                el.get("type")
                or el.get("subType")
                or el.get("object_type", "Item")
            )
            items.append(PLMXMLItemRow(
                uid=uid,
                item_id=item_id,
                name=el.get("name", el.get("object_name", "")),
                item_type=item_type,
                attributes=self._user_data(el),
            ))
        return items

    def _iter_revisions(self, item_uid_set: set) -> List[PLMXMLRevisionRow]:
        """
        ItemRevision / ProductRevision may be a child of Item/Product, or a
        top-level element with masterRef pointing back to the parent.
        """
        revs: List[PLMXMLRevisionRow] = []
        _ITEM_TAGS = ("Item", "Product")
        _REV_TAGS  = ("ItemRevision", "ProductRevision")

        # Pass 1: children of Item/Product elements
        for el in self.root.iter():
            if _local(el.tag) not in _ITEM_TAGS:
                continue
            item_uid = el.get("id", "")
            for rev_el in el:
                if _local(rev_el.tag) not in _REV_TAGS:
                    continue
                uid = rev_el.get("id", "")
                if not uid:
                    continue
                revs.append(PLMXMLRevisionRow(
                    uid=uid,
                    parent_item_uid=item_uid,
                    revision=(
                        rev_el.get("revision")
                        or rev_el.get("productRevisionId")
                        or rev_el.get("item_revision_id", "")
                    ),
                    name=rev_el.get("name", rev_el.get("object_name", "")),
                    status=rev_el.get("release_status", rev_el.get("releaseStatus", "")),
                    attributes=self._user_data(rev_el),
                ))
        # Pass 2: top-level ItemRevision/ProductRevision with masterRef
        seen = {r.uid for r in revs}
        for rev_el in self.root.iter():
            if _local(rev_el.tag) not in _REV_TAGS:
                continue
            uid = rev_el.get("id", "")
            if not uid or uid in seen:
                continue
            master_ref = self._resolve_idref(rev_el.get("masterRef", ""))
            revs.append(PLMXMLRevisionRow(
                uid=uid,
                parent_item_uid=master_ref if master_ref in item_uid_set else "",
                revision=(
                    rev_el.get("revision")
                    or rev_el.get("productRevisionId")
                    or rev_el.get("item_revision_id", "")
                ),
                name=rev_el.get("name", rev_el.get("object_name", "")),
                status=rev_el.get("release_status", rev_el.get("releaseStatus", "")),
                attributes=self._user_data(rev_el),
            ))
        return revs

    def _iter_bom_lines(self, rev_uid_set: set) -> List[PLMXMLBOMLineRow]:
        lines: List[PLMXMLBOMLineRow] = []

        _REV_TAGS = ("ItemRevision", "ProductRevision")
        _OCC_TAGS = ("BOMViewOccurrence", "OccurrenceGroup", "Occurrence",
                     "ProductInstance")

        # --- v4/v5 path: occurrences nested under ItemRevision > BOMView ---
        for el in self.root.iter():
            if _local(el.tag) not in _REV_TAGS:
                continue
            rev_uid = el.get("id", "")
            if not rev_uid:
                continue
            # BOMView child
            for bv in self._iter_local(el, "BOMView", "BOMViewRevision"):
                for occ in bv.iter():
                    if _local(occ.tag) not in _OCC_TAGS:
                        continue
                    occ_uid = occ.get("id", "")
                    ref = self._resolve_idref(
                        occ.get("instancedRef", occ.get("refId", occ.get("partRef", "")))
                    )
                    attrs = self._user_data(occ)
                    qty_str = occ.get("quantity", attrs.get("Quantity", "1"))
                    try:
                        qty = float(qty_str) if qty_str else 1.0
                    except (ValueError, TypeError):
                        qty = 1.0
                    lines.append(PLMXMLBOMLineRow(
                        uid=occ_uid or f"{rev_uid}_bom_{len(lines)}",
                        parent_rev_uid=rev_uid,
                        ref_uid=ref,
                        quantity=qty,
                        find_num=occ.get("findNumber",
                                        occ.get("sequenceNumber",
                                                attrs.get("FindNumber", ""))),
                        unit=occ.get("unit", attrs.get("Unit", "EA")),
                        attributes=attrs,
                    ))

        # --- v6 path: <InstanceGraph> at top-level, containing <ProductInstance> ---
        seen_bom = {l.uid for l in lines}
        for ig in self.root.iter():
            if _local(ig.tag) != "InstanceGraph":
                continue
            # InstanceGraph.rootRefs points to the parent revision(s)
            root_refs_raw = ig.get("rootRefs", "")
            default_rev_uid = self._resolve_idref(root_refs_raw.split()[0]) if root_refs_raw else ""

            for pi in ig:
                if _local(pi.tag) != "ProductInstance":
                    continue
                occ_uid = pi.get("id", "")
                if not occ_uid or occ_uid in seen_bom:
                    continue

                part_ref = self._resolve_idref(pi.get("partRef", ""))
                attrs = self._user_data(pi)
                qty_str = pi.get("quantity", attrs.get("Quantity", "1"))
                try:
                    qty = float(qty_str) if qty_str else 1.0
                except (ValueError, TypeError):
                    qty = 1.0

                lines.append(PLMXMLBOMLineRow(
                    uid=occ_uid,
                    parent_rev_uid=default_rev_uid,
                    ref_uid=part_ref,
                    quantity=qty,
                    find_num=pi.get("sequenceNumber",
                                   pi.get("findNumber",
                                          attrs.get("FindNumber", ""))),
                    unit=pi.get("unit", attrs.get("Unit", "EA")),
                    attributes=attrs,
                ))
                seen_bom.add(occ_uid)

        return lines

    def _iter_datasets(self) -> List[PLMXMLDataSetRow]:
        datasets: List[PLMXMLDataSetRow] = []
        _REV_TAGS = ("ItemRevision", "ProductRevision")
        for el in self.root.iter():
            if _local(el.tag) not in _REV_TAGS:
                continue
            rev_uid = el.get("id", "")
            if not rev_uid:
                continue
            for ds_el in self._iter_local(el, "DataSet"):
                uid = ds_el.get("id", "")
                if not uid:
                    uid = f"{rev_uid}_ds_{len(datasets)}"
                ext_files = [
                    ef.get("locationRef", ef.get("href", ef.text or ""))
                    for ef in self._iter_local(ds_el, "ExternalFile")
                ]
                datasets.append(PLMXMLDataSetRow(
                    uid=uid,
                    parent_rev_uid=rev_uid,
                    name=ds_el.get("name", ""),
                    ds_type=ds_el.get("type", ds_el.get("datasetType", "")),
                    member=ds_el.get("member", ""),
                    external_files=ext_files,
                ))
        return datasets

    def parse(self):
        """Return (items, revisions, bom_lines, datasets)."""
        items = self._iter_items()
        item_uid_set = {i.uid for i in items}
        revisions = self._iter_revisions(item_uid_set)
        rev_uid_set = {r.uid for r in revisions}
        bom_lines = self._iter_bom_lines(rev_uid_set)
        datasets = self._iter_datasets()
        return items, revisions, bom_lines, datasets


# ---------------------------------------------------------------------------
# Neo4j writer
# ---------------------------------------------------------------------------

_UPSERT_FILE = """
MERGE (f:PLMXMLFile {file_uri: $file_uri})
SET f.name             = $name,
    f.schema_version   = $schema_version,
    f.date             = $date,
    f.author           = $author,
    f.source_system    = $source_system,
    f.ingested_at      = datetime()
RETURN f
"""

_UPSERT_ITEMS = """
UNWIND $rows AS row
MERGE (n:PLMXMLItem {uid: row.uid})
SET n.item_id    = row.item_id,
    n.name       = row.name,
    n.item_type  = row.item_type,
    n += row.attributes
WITH n, row
MATCH (f:PLMXMLFile {file_uri: row.file_uri})
MERGE (f)-[:CONTAINS]->(n)
"""

_UPSERT_REVISIONS = """
UNWIND $rows AS row
MERGE (r:PLMXMLRevision {uid: row.uid})
SET r.revision   = row.revision,
    r.name       = row.name,
    r.status     = row.status,
    r.item_id    = row.item_id,
    r += row.attributes
WITH r, row
MATCH (item:PLMXMLItem {uid: row.parent_item_uid})
MERGE (item)-[:HAS_REVISION]->(r)
"""

_UPSERT_BOM_LINES = """
UNWIND $rows AS row
MERGE (b:PLMXMLBOMLine {uid: row.uid})
SET b.quantity   = row.quantity,
    b.find_num   = row.find_num,
    b.unit       = row.unit,
    b += row.attributes
WITH b, row
MATCH (r:PLMXMLRevision {uid: row.parent_rev_uid})
MERGE (r)-[:HAS_BOM_LINE]->(b)
WITH b, row
OPTIONAL MATCH (ref_item:PLMXMLItem {uid: row.ref_uid})
FOREACH (_ IN CASE WHEN ref_item IS NOT NULL THEN [1] ELSE [] END |
    MERGE (b)-[:REFERENCES]->(ref_item)
)
"""

_UPSERT_DATASETS = """
UNWIND $rows AS row
MERGE (d:PLMXMLDataSet {uid: row.uid})
SET d.name        = row.name,
    d.ds_type     = row.ds_type,
    d.member      = row.member,
    d.ext_files   = row.ext_files
WITH d, row
MATCH (r:PLMXMLRevision {uid: row.parent_rev_uid})
MERGE (r)-[:HAS_DATASET]->(d)
"""

_LINK_STEP = """
UNWIND $rows AS row
MATCH (d:PLMXMLDataSet {uid: row.ds_uid})
MATCH (sf:StepFile)
WHERE sf.name CONTAINS row.stem OR sf.file_uri CONTAINS row.stem
MERGE (d)-[:LINKED_STEP_FILE]->(sf)
RETURN count(*) AS linked
"""

# Exact match: cls.name == item_type
_CLASSIFY_EXACT = """
MATCH (item:PLMXMLItem {uid: $uid})
MATCH (cls:ExternalOwlClass)
WHERE cls.name = $item_type
  AND cls.ap_level IN ['AP242', 'AP243']
MERGE (item)-[:CLASSIFIED_AS {
  source: 'plmxml_ingest',
  ap_level: cls.ap_level,
  confidence: 'exact'
}]->(cls)
RETURN count(*) AS linked
"""

# Fuzzy fallback: case-insensitive partial match
_CLASSIFY_FUZZY = """
MATCH (item:PLMXMLItem {uid: $uid})
WHERE NOT (item)-[:CLASSIFIED_AS]->(:ExternalOwlClass)
MATCH (cls:ExternalOwlClass)
WHERE cls.ap_level IN ['AP242', 'AP243']
  AND toLower(cls.name) CONTAINS toLower($item_type)
WITH item, cls
ORDER BY size(cls.name) ASC
LIMIT 1
MERGE (item)-[:CLASSIFIED_AS {
  source: 'plmxml_ingest',
  ap_level: cls.ap_level,
  confidence: 'fuzzy'
}]->(cls)
RETURN count(*) AS linked
"""

# Mark remaining items as unclassified
_MARK_UNCLASSIFIED = """
MATCH (item:PLMXMLItem {uid: $uid})
WHERE NOT (item)-[:CLASSIFIED_AS]->(:ExternalOwlClass)
SET item.unclassified = true
RETURN count(*) AS marked
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PLMXMLIngestService:
    """Ingest a Teamcenter PLMXML export into the Neo4j knowledge graph."""

    def __init__(self, config: PLMXMLIngestConfig | None = None):
        self.config = config or PLMXMLIngestConfig()
        self.neo4j = get_neo4j_service()

    # -- public API ----------------------------------------------------------

    def ingest_file(
        self,
        path: Path,
        *,
        file_label: Optional[str] = None,
    ) -> PLMXMLIngestResult:
        """Parse *path* (PLMXML .xml/.plmxml) and upsert all objects into Neo4j."""
        if not path.exists():
            raise FileNotFoundError(f"PLMXML file not found: {path}")

        logger.info(f"PLMXMLIngest: parsing {path.name} ({path.stat().st_size // 1024} KB)")

        try:
            tree = ET.parse(str(path))
        except ET.ParseError as exc:
            raise ValueError(f"Invalid PLMXML/XML: {exc}") from exc

        root = tree.getroot()
        parser = _PLMXMLParser(root)
        items, revisions, bom_lines, datasets = parser.parse()

        meta = parser.file_meta
        file_uri = str(path.resolve())
        name = file_label or path.name

        logger.info(
            f"PLMXMLIngest: found {len(items)} items, {len(revisions)} revisions, "
            f"{len(bom_lines)} BOM lines, {len(datasets)} datasets"
        )

        errors: List[str] = []

        # 1. File node
        self._run(_UPSERT_FILE, {
            "file_uri": file_uri,
            "name": name,
            "schema_version": meta.schema_version,
            "date": meta.date,
            "author": meta.author,
            "source_system": meta.source_system,
        })

        # 2. Items
        items_done = self._upsert_batched(
            _UPSERT_ITEMS,
            [
                {
                    "uid": i.uid,
                    "item_id": i.item_id,
                    "name": i.name,
                    "item_type": i.item_type,
                    "file_uri": file_uri,
                    "attributes": {k: str(v) for k, v in i.attributes.items()},
                }
                for i in items
            ],
            errors,
        )

        # 3. Revisions (need items in graph first)
        item_uid_set = {i.uid for i in items}
        revs_done = self._upsert_batched(
            _UPSERT_REVISIONS,
            [
                {
                    "uid": r.uid,
                    "revision": r.revision,
                    "name": r.name,
                    "status": r.status,
                    "item_id": r.parent_item_uid,
                    "parent_item_uid": r.parent_item_uid,
                    "attributes": {k: str(v) for k, v in r.attributes.items()},
                }
                for r in revisions
                if r.parent_item_uid in item_uid_set
            ],
            errors,
        )

        # 4. BOM lines
        rev_uid_set = {r.uid for r in revisions}
        bom_done = self._upsert_batched(
            _UPSERT_BOM_LINES,
            [
                {
                    "uid": b.uid,
                    "parent_rev_uid": b.parent_rev_uid,
                    "ref_uid": b.ref_uid,
                    "quantity": b.quantity,
                    "find_num": b.find_num,
                    "unit": b.unit,
                    "attributes": {k: str(v) for k, v in b.attributes.items()},
                }
                for b in bom_lines
                if b.parent_rev_uid in rev_uid_set
            ],
            errors,
        )

        # 5. DataSets
        ds_done = self._upsert_batched(
            _UPSERT_DATASETS,
            [
                {
                    "uid": d.uid,
                    "parent_rev_uid": d.parent_rev_uid,
                    "name": d.name,
                    "ds_type": d.ds_type,
                    "member": d.member,
                    "ext_files": d.external_files,
                }
                for d in datasets
                if d.parent_rev_uid in rev_uid_set
            ],
            errors,
        )

        # 6. Cross-link DataSets → :StepFile
        step_links = 0
        if self.config.create_step_links:
            step_links = self._link_step_files(datasets, errors)

        # 7. Ontology classification (CLASSIFIED_AS edges)
        classified, unclassified = self._link_ontology_classes(items, errors)

        # 8. OpenSearch vectorization (non-blocking)
        vectors_indexed = self._vectorize_nodes(items, revisions, errors)

        # 9. TRS change event (non-blocking)
        self._notify_trs(file_uri, "create", errors)

        result = PLMXMLIngestResult(
            file_uri=file_uri,
            schema_version=meta.schema_version,
            items_upserted=items_done,
            revisions_upserted=revs_done,
            bom_lines_upserted=bom_done,
            datasets_upserted=ds_done,
            step_links_created=step_links,
            classified_count=classified,
            unclassified_count=unclassified,
            vectors_indexed=vectors_indexed,
            errors=errors,
        )
        logger.info(
            f"PLMXMLIngest done: {items_done} items, {revs_done} revs, "
            f"{bom_done} BOM lines, {ds_done} datasets, {step_links} STEP links, "
            f"{classified} classified, {unclassified} unclassified, "
            f"{vectors_indexed} vectors"
        )
        return result

    # -- Neo4j helpers -------------------------------------------------------

    def _run(self, cypher: str, params: Dict[str, Any]):
        with self.neo4j.driver.session(database=self.neo4j.database) as session:
            session.run(cypher, **params)

    def _upsert_batched(
        self,
        cypher: str,
        rows: List[Dict[str, Any]],
        errors: List[str],
    ) -> int:
        if not rows:
            return 0
        bs = self.config.batch_size
        done = 0
        for i in range(0, len(rows), bs):
            batch = rows[i : i + bs]
            try:
                with self.neo4j.driver.session(database=self.neo4j.database) as session:
                    session.run(cypher, rows=batch)
                done += len(batch)
            except Exception as exc:
                msg = f"Batch upsert failed at row {i}: {exc}"
                logger.error(msg)
                errors.append(msg)
        return done

    def _link_step_files(
        self, datasets: List[PLMXMLDataSetRow], errors: List[str]
    ) -> int:
        """
        For each DataSet of type UGMASTER / DirectModel or whose member / external_files
        name ends in .stp/.step/.stpx, try to link to an existing :StepFile node.
        """
        step_exts = (".stp", ".step", ".stpx", ".stp_ap")
        link_rows = []
        for ds in datasets:
            candidates = [ds.member] + ds.external_files
            for cand in candidates:
                if cand and cand.lower().endswith(step_exts):
                    stem = Path(cand).stem  # filename without extension
                    if stem:
                        link_rows.append({"ds_uid": ds.uid, "stem": stem})
                        break

        if not link_rows:
            return 0

        linked = 0
        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                result = session.run(_LINK_STEP, rows=link_rows)
                record = result.single()
                linked = int(record["linked"]) if record else 0
        except Exception as exc:
            msg = f"STEP link query failed: {exc}"
            logger.warning(msg)
            errors.append(msg)
        return linked

    def _link_ontology_classes(
        self, items: List[PLMXMLItemRow], errors: List[str]
    ) -> Tuple[int, int]:
        """Create CLASSIFIED_AS edges from PLMXMLItem nodes to ExternalOwlClass.

        Strategy:
          1. Exact match: ``cls.name == item.item_type``
          2. Fuzzy fallback: ``toLower(cls.name) CONTAINS toLower(item_type)``
          3. If no match: ``SET item.unclassified = true``

        Returns (classified_count, unclassified_count).
        """
        if not items:
            return 0, 0

        classified = 0
        unclassified = 0

        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                for item in items:
                    if not item.item_type:
                        # No type to classify — mark unclassified
                        session.run(_MARK_UNCLASSIFIED, uid=item.uid)
                        unclassified += 1
                        continue

                    # Strategy 1: exact match
                    result = session.run(
                        _CLASSIFY_EXACT,
                        uid=item.uid,
                        item_type=item.item_type,
                    )
                    record = result.single()
                    exact_linked = int(record["linked"]) if record else 0

                    if exact_linked > 0:
                        classified += 1
                        continue

                    # Strategy 2: fuzzy fallback
                    result = session.run(
                        _CLASSIFY_FUZZY,
                        uid=item.uid,
                        item_type=item.item_type,
                    )
                    record = result.single()
                    fuzzy_linked = int(record["linked"]) if record else 0

                    if fuzzy_linked > 0:
                        classified += 1
                        continue

                    # No match — mark unclassified
                    session.run(_MARK_UNCLASSIFIED, uid=item.uid)
                    unclassified += 1

        except Exception as exc:
            msg = f"Ontology classification failed: {exc}"
            logger.warning(msg)
            errors.append(msg)

        logger.info(
            f"Ontology classification: {classified} classified, "
            f"{unclassified} unclassified"
        )
        return classified, unclassified

    def _vectorize_nodes(
        self,
        items: List[PLMXMLItemRow],
        revisions: List[PLMXMLRevisionRow],
        errors: List[str],
    ) -> int:
        """Embed PLMXMLItem text descriptions and upsert into OpenSearch.

        Text template per item:
            "item_id: {item_id} name: {name} type: {item_type} revision: {rev_id}"

        On OpenSearch / Ollama failure the error is logged but ingestion continues
        (non-blocking).

        Returns the number of vectors successfully indexed.
        """
        if not items:
            return 0

        # Build revision lookup: parent_item_uid → first revision id
        rev_lookup: Dict[str, str] = {}
        for r in revisions:
            if r.parent_item_uid not in rev_lookup:
                rev_lookup[r.parent_item_uid] = r.revision

        # Build text documents
        texts: List[str] = []
        uids: List[str] = []
        meta_list: List[Dict[str, Any]] = []
        for item in items:
            rev_id = rev_lookup.get(item.uid, "")
            text = (
                f"item_id: {item.item_id} "
                f"name: {item.name} "
                f"type: {item.item_type} "
                f"revision: {rev_id}"
            )
            texts.append(text)
            uids.append(item.uid)
            meta_list.append({
                "labels": ["PLMXMLItem"],
                "item_type": item.item_type,
                "name": item.name,
                "ap_level": "AP242",
            })

        # Generate embeddings
        try:
            embedder = _get_embeddings()
            embeddings = embedder.embed(texts)
        except Exception as exc:  # noqa: BLE001
            msg = f"Vectorization: embedding generation failed — {exc}"
            logger.warning(msg)
            errors.append(msg)
            return 0

        if len(embeddings) != len(texts):
            msg = (
                f"Vectorization: embedding count mismatch "
                f"(expected {len(texts)}, got {len(embeddings)})"
            )
            logger.warning(msg)
            errors.append(msg)
            return 0

        # Upsert into OpenSearch
        index_name = os.getenv("VECTORSTORE_INDEX", "embeddings")
        indexed = 0
        try:
            vs = _get_vectorstore()
            for uid, text, emb, meta in zip(uids, texts, embeddings, meta_list):
                try:
                    vs.upsert(index_name, uid, text, emb, meta)
                    indexed += 1
                except Exception as exc:  # noqa: BLE001
                    # Write pending file for retry
                    pending_dir = Path("data/vectorize_progress")
                    pending_dir.mkdir(parents=True, exist_ok=True)
                    (pending_dir / f"{uid}.pending").write_text(text, encoding="utf-8")
                    logger.debug(
                        f"Vectorization: upsert failed for {uid}, "
                        f"wrote pending file — {exc}"
                    )
        except Exception as exc:  # noqa: BLE001
            msg = f"Vectorization: OpenSearch upsert failed — {exc}"
            logger.warning(msg)
            errors.append(msg)

        logger.info(f"Vectorization: {indexed}/{len(texts)} vectors indexed")
        return indexed

    def _notify_trs(
        self, resource_uri: str, change_type: str, errors: List[str]
    ) -> None:
        """Fire a TRS change event (non-blocking, best-effort).

        Uses ``asyncio`` to call the async ``append_change_event`` from
        the sync ``ingest_file`` context.
        """
        import asyncio

        try:
            from src.web.services.oslc_trs_service import OSLCTRSService
            trs = OSLCTRSService()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(trs.append_change_event(resource_uri, change_type))
            else:
                asyncio.run(trs.append_change_event(resource_uri, change_type))

            logger.debug(f"TRS event dispatched: {change_type} {resource_uri}")
        except Exception as exc:  # noqa: BLE001
            msg = f"TRS notification failed (non-blocking): {exc}"
            logger.debug(msg)
            errors.append(msg)
