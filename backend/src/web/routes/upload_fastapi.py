"""
File Upload API for XMI, XML, and CSV ingestion
"""

import os
import shutil
import uuid
import pandas as pd
from pathlib import Path
from typing import Optional
import tempfile

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from loguru import logger
from pydantic import BaseModel, Field

from src.parsers.semantic_loader import SemanticXMILoader
from src.parsers.express import ExpressParser, ExpressNeo4jConverter
from src.web.services import get_neo4j_service
from src.web.utils.responses import Neo4jJSONResponse
from src.web.services.upload_job_store import get_job_store
from src.web.services.step_ingest_service import StepIngestConfig, StepIngestService
from src.web.services.ontology_ingest_service import OntologyIngestService, OntologyIngestConfig

# Import V2 ingesters
import sys
SCRIPTS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_PATH))

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Storage configuration
UPLOAD_DIR = Path("data/uploads")
RAW_DATA_DIR = Path("data/raw")
ALLOWED_EXTENSIONS = {".xmi", ".xml", ".csv", ".json", ".exp", ".xsd", ".stp", ".step", ".stpx", ".owl", ".ttl", ".rdf", ".nq"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


class UploadResponse(BaseModel):
    """Response model for file upload"""

    success: bool
    message: str
    filename: str
    file_size: int
    file_type: str
    job_id: Optional[str] = None
    stats: Optional[dict] = None


class UploadStatus(BaseModel):
    """Status model for upload job"""

    job_id: str
    status: str = Field(description="pending, processing, completed, failed")
    filename: str
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    stats: Optional[dict] = None
    error: Optional[str] = None


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check filename
    if not file.filename or len(file.filename) > 255:
        return False, "Invalid filename"

    return True, "OK"


async def process_xmi_file(file_path: Path, job_id: str) -> dict:
    """Process XMI file in background using V2 Pydantic-based ingester"""
    job_store = get_job_store()
    try:
        await job_store.update(
            job_id,
            {
                "status": "processing",
                "progress": 10,
                "message": "Initializing XMI V2 ingester...",
            },
        )

        def _process_xmi_v2_sync():
            # Import V2 ingester (path already in sys.path from module init)
            from ingest_xmi_v2 import XMIIngesterV2
            
            # Get Neo4j connection
            neo4j_service = get_neo4j_service()
            
            # Create a connection wrapper for V2 ingester
            from backend.src.graph.connection import Neo4jConnection
            from backend.src.utils.config import Config
            config = Config()
            conn = Neo4jConnection(
                uri=config.neo4j_uri,
                user=config.neo4j_user,
                password=config.neo4j_password
            )
            conn.connect()
            
            try:
                # Initialize V2 ingester
                ingester = XMIIngesterV2(connection=conn, dry_run=False)
                
                # Ingest file
                stats = ingester.ingest_file(file_path)
                
                return {
                    "nodes_created": stats.get("nodes_created", 0),
                    "relationships_created": stats.get("relationships_created", 0),
                    "elements_by_type": stats.get("elements_by_type", {}),
                    "relationships_by_type": stats.get("relationships_by_type", {}),
                    "ingester_version": "V2 (Pydantic)",
                }
            finally:
                conn.close()

        await job_store.update(
            job_id, {"progress": 30, "message": "Parsing XMI with V2 ingester..."}
        )

        stats = await run_in_threadpool(_process_xmi_v2_sync)

        await job_store.update(
            job_id, {"progress": 90, "message": "Finalizing import..."}
        )

        # Move file to raw data directory
        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully imported {file_path.name}",
                "stats": stats,
            },
        )

        logger.success(f"✓ Processed XMI file (V2): {file_path.name} - {stats}")
        return stats

    except Exception as e:
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to process file: {str(e)}",
            },
        )
        logger.error(f"✗ Failed to process XMI file: {e}")
        raise


async def process_csv_file(file_path: Path, job_id: str) -> dict:
    """Process CSV file in background"""
    job_store = get_job_store()
    try:
        await job_store.update(
            job_id,
            {"status": "processing", "progress": 10, "message": "Reading CSV file..."},
        )

        def _process_csv_sync():
            df = pd.read_csv(file_path)
            # Infer label
            label = file_path.stem
            # Sanitize label (basic)
            label = "".join(x for x in label if x.isalnum() or x in "_")

            if "id" not in df.columns:
                df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]

            # Convert to list of dicts, replacing NaN with None
            records = df.where(pd.notnull(df), None).to_dict("records")

            neo4j_service = get_neo4j_service()

            query = f"""
            UNWIND $batch AS row
            MERGE (n:`{label}` {{id: row.id}})
            SET n += row
            RETURN count(n) as count
            """

            result = neo4j_service.execute_query(query, {"batch": records})
            count = result[0]["count"] if result else 0
            return {"nodes_created": count, "label": label}

        stats = await run_in_threadpool(_process_csv_sync)

        await job_store.update(
            job_id, {"progress": 90, "message": "Importing data..."}
        )

        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully imported {file_path.name}",
                "stats": stats,
            },
        )
        logger.success(f"✓ Processed CSV file: {file_path.name} - {stats}")
        return stats

    except Exception as e:
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to process file: {str(e)}",
            },
        )
        logger.error(f"✗ Failed to process CSV file: {e}")
        raise


async def process_exp_file(file_path: Path, job_id: str) -> dict:
    """Process EXPRESS schema file in background"""
    job_store = get_job_store()
    try:
        await job_store.update(
            job_id,
            {
                "status": "processing",
                "progress": 10,
                "message": "Initializing EXPRESS parser...",
            },
        )

        def _process_exp_sync():
            # Parse EXPRESS file
            parser = ExpressParser()
            result = parser.parse_file(str(file_path))
            
            if not result.success or not result.parsed_schema:
                raise ValueError(f"Failed to parse EXPRESS file: {result.error}")
            
            schema = result.parsed_schema
            
            # Get Neo4j connection and create graph nodes
            neo4j_service = get_neo4j_service()
            
            # Generate Cypher statements using the converter
            label_prefix = ""  # Could be AP239_, AP242_, etc. based on schema
            if "ap239" in schema.name.lower():
                label_prefix = "AP239_"
            elif "ap242" in schema.name.lower():
                label_prefix = "AP242_"
            elif "ap243" in schema.name.lower():
                label_prefix = "AP243_"
            
            statements = ExpressNeo4jConverter.schema_to_cypher(
                schema,
                label_prefix=label_prefix,
                include_relationships=True
            )
            
            # Execute Cypher statements
            nodes_created = 0
            relationships_created = 0
            
            for stmt in statements:
                try:
                    result = neo4j_service.execute_query(stmt)
                    if "MERGE (s:" in stmt or "MERGE (e:" in stmt or "MERGE (t:" in stmt:
                        nodes_created += 1
                    elif "MERGE (" in stmt and ")-[" in stmt:
                        relationships_created += 1
                except Exception as stmt_error:
                    logger.warning(f"Statement warning: {stmt_error}")
                    continue
            
            return {
                "schema_name": schema.name,
                "entities": len(schema.entities),
                "types": len(schema.types),
                "imports": len(schema.imports),
                "nodes_created": nodes_created,
                "relationships_created": relationships_created,
                "parse_time_ms": result.parse_time_ms if hasattr(result, 'parse_time_ms') else 0,
            }

        await job_store.update(
            job_id, {"progress": 30, "message": "Parsing EXPRESS schema..."}
        )

        stats = await run_in_threadpool(_process_exp_sync)

        await job_store.update(
            job_id, {"progress": 90, "message": "Finalizing import..."}
        )

        # Move file to raw data directory
        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully imported EXPRESS schema: {stats.get('schema_name', file_path.name)}",
                "stats": stats,
            },
        )
        logger.success(f"✓ Processed EXPRESS file: {file_path.name} - {stats}")
        return stats

    except Exception as e:
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to process EXPRESS file: {str(e)}",
            },
        )
        logger.error(f"✗ Failed to process EXPRESS file: {e}")
        raise


async def process_step_file(file_path: Path, job_id: str) -> dict:
    """Process STEP file in background (stores a raw instance/reference graph)."""
    job_store = get_job_store()
    try:
        await job_store.update(
            job_id,
            {
                "status": "processing",
                "progress": 10,
                "message": "Initializing STEP ingester...",
            },
        )

        def _process_step_sync() -> dict:
            svc = StepIngestService(StepIngestConfig(batch_size=500))
            stats = svc.ingest_file(file_path)
            return {
                "file_uri": stats.file_uri,
                "format": stats.format,
                "file_schema": stats.file_schema,
                "instances_upserted": stats.instances_upserted,
                "refs_upserted": stats.refs_upserted,
            }

        await job_store.update(job_id, {"progress": 30, "message": "Parsing and ingesting STEP..."})

        stats = await run_in_threadpool(_process_step_sync)

        await job_store.update(job_id, {"progress": 90, "message": "Finalizing import..."})

        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully imported STEP file: {file_path.name}",
                "stats": stats,
            },
        )

        logger.success(f"✓ Processed STEP file: {file_path.name} - {stats}")
        return stats

    except Exception as e:  # noqa: BLE001 pylint: disable=broad-exception-caught
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to process STEP file: {str(e)}",
            },
        )
        logger.error(f"✗ Failed to process STEP file: {e}")
        raise


async def process_xsd_file(file_path: Path, job_id: str) -> dict:
    """Process XSD schema file in background using XSDIngester"""
    job_store = get_job_store()
    try:
        await job_store.update(
            job_id,
            {
                "status": "processing",
                "progress": 10,
                "message": "Initializing XSD parser...",
            },
        )

        def _process_xsd_sync():
            from lxml import etree
            
            # Parse XSD file
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            XSD = '{http://www.w3.org/2001/XMLSchema}'
            
            # Get schema info
            target_ns = root.get('targetNamespace', '')
            schema_name = file_path.stem
            
            # Extract elements
            elements = []
            relationships = []
            
            # Schema node
            schema_id = f"schema:{schema_name}"
            elements.append({
                'id': schema_id,
                'type': 'XSDSchema',
                'name': schema_name,
                'target_namespace': target_ns,
                'source_file': str(file_path),
            })
            
            # Process complexTypes
            for ct in root.findall(f'{XSD}complexType'):
                name = ct.get('name', '')
                if not name:
                    continue
                ct_id = f"ct:{schema_name}:{name}"
                
                # Check for base type
                base_type = ''
                cc = ct.find(f'{XSD}complexContent')
                if cc is not None:
                    ext = cc.find(f'{XSD}extension')
                    if ext is not None:
                        base_type = ext.get('base', '')
                    rest = cc.find(f'{XSD}restriction')
                    if rest is not None:
                        base_type = rest.get('base', '')
                
                elements.append({
                    'id': ct_id,
                    'type': 'XSDComplexType',
                    'name': name,
                    'schema': schema_name,
                    'base_type': base_type.split(':')[-1] if base_type else '',
                    'is_abstract': ct.get('abstract', 'false') == 'true',
                })
                
                relationships.append({
                    'from_id': schema_id,
                    'to_id': ct_id,
                    'type': 'DEFINES',
                })
                
                # Process nested elements
                for seq in ct.findall(f'.//{XSD}sequence'):
                    for elem in seq.findall(f'{XSD}element'):
                        elem_name = elem.get('name', '')
                        if elem_name:
                            elem_id = f"le:{schema_name}:{ct_id}:{elem_name}"
                            elements.append({
                                'id': elem_id,
                                'type': 'XSDElement',
                                'name': elem_name,
                                'schema': schema_name,
                                'type_ref': elem.get('type', '').split(':')[-1] if elem.get('type') else '',
                                'min_occurs': elem.get('minOccurs', '1'),
                                'max_occurs': elem.get('maxOccurs', '1'),
                            })
                            relationships.append({
                                'from_id': ct_id,
                                'to_id': elem_id,
                                'type': 'CONTAINS',
                            })
            
            # Process simpleTypes
            for st in root.findall(f'{XSD}simpleType'):
                name = st.get('name', '')
                if not name:
                    continue
                st_id = f"st:{schema_name}:{name}"
                
                base_type = ''
                rest = st.find(f'{XSD}restriction')
                if rest is not None:
                    base_type = rest.get('base', '')
                
                elements.append({
                    'id': st_id,
                    'type': 'XSDSimpleType',
                    'name': name,
                    'schema': schema_name,
                    'base_type': base_type.split(':')[-1] if base_type else '',
                })
                
                relationships.append({
                    'from_id': schema_id,
                    'to_id': st_id,
                    'type': 'DEFINES',
                })
            
            # Process global elements
            for elem in root.findall(f'{XSD}element'):
                name = elem.get('name', '')
                if not name:
                    continue
                elem_id = f"ge:{schema_name}:{name}"
                
                elements.append({
                    'id': elem_id,
                    'type': 'XSDElement',
                    'name': name,
                    'schema': schema_name,
                    'type_ref': elem.get('type', '').split(':')[-1] if elem.get('type') else '',
                    'is_global': True,
                })
                
                relationships.append({
                    'from_id': schema_id,
                    'to_id': elem_id,
                    'type': 'DEFINES',
                })
            
            # Import to Neo4j
            neo4j_service = get_neo4j_service()
            
            # Create nodes in batch
            for elem in elements:
                elem_type = elem.pop('type')
                cypher = f"""
                    MERGE (n:{elem_type}:XSDElement {{id: $id}})
                    SET n += $props
                """
                neo4j_service.execute_query(cypher, {'id': elem['id'], 'props': elem})
            
            # Create relationships in batch
            for rel in relationships:
                cypher = f"""
                    MATCH (a:XSDElement {{id: $from_id}})
                    MATCH (b:XSDElement {{id: $to_id}})
                    MERGE (a)-[r:{rel['type']}]->(b)
                """
                neo4j_service.execute_query(cypher, {
                    'from_id': rel['from_id'],
                    'to_id': rel['to_id'],
                })
            
            return {
                "schema_name": schema_name,
                "target_namespace": target_ns,
                "nodes_created": len(elements),
                "relationships_created": len(relationships),
            }

        await job_store.update(
            job_id, {"progress": 30, "message": "Parsing XSD schema..."}
        )

        stats = await run_in_threadpool(_process_xsd_sync)

        await job_store.update(
            job_id, {"progress": 90, "message": "Finalizing import..."}
        )

        # Move file to raw data directory
        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully imported XSD schema: {stats.get('schema_name', file_path.name)}",
                "stats": stats,
            },
        )
        logger.success(f"✓ Processed XSD file: {file_path.name} - {stats}")
        return stats

    except Exception as e:
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to process XSD file: {str(e)}",
            },
        )
        logger.error(f"✗ Failed to process XSD file: {e}")
        raise


async def process_ontology_file(file_path: Path, job_id: str) -> dict:
    """Process Ontology RDF/OWL file in background"""
    job_store = get_job_store()
    try:
        await job_store.update(
            job_id,
            {"status": "processing", "progress": 10, "message": "Initializing Ontology ingestion service..."},
        )

        def _process_ontology_sync():
            service = OntologyIngestService()
            # Let rdflib guess format from extension or content, or provide hint
            rdf_format = None
            ext = file_path.suffix.lower()
            if ext == ".ttl":
                rdf_format = "turtle"
            elif ext == ".nq":
                rdf_format = "nquads"
            elif ext in [".rdf", ".owl"]:
                rdf_format = "xml"  # Basic heuristic
            
            # Start ingestion
            result = service.ingest_file(file_path, rdf_format=rdf_format)
            return result

        await job_store.update(
            job_id, {"progress": 30, "message": "Parsing and ingesting ontology..."}
        )

        stats = await run_in_threadpool(_process_ontology_sync)

        await job_store.update(
            job_id, {"progress": 90, "message": "Finalizing ontology import..."}
        )

        # Move file to raw data directory
        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": f"Successfully imported Ontology: {stats.get('ontology_name', file_path.name)}",
                "stats": stats,
            },
        )
        logger.success(f"✓ Processed Ontology file: {file_path.name} - {stats}")
        return stats

    except Exception as e:
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "message": f"Failed to process Ontology file: {str(e)}",
            },
        )
        logger.error(f"✗ Failed to process Ontology file: {e}")
        raise


@router.post("/", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
) -> UploadResponse:
    """
    Upload XMI, XML, XSD, EXPRESS or CSV file for ingestion into Neo4j

    **Supported Formats:**
    - `.xmi` - UML/SysML XMI models (Eclipse Papyrus, MagicDraw, etc.)
    - `.xml` - XML-based model files
    - `.xsd` - XML Schema Definition files (ISO 10303-15 STEP, AP239, AP242)
    - `.exp` - EXPRESS schema files (ISO 10303 STEP)
    - `.csv` - Comma-separated values for bulk data import
    - `.stp`/`.step` - STEP Part 21 instance files (raw instance graph)
    - `.stpx` - STEP-XML Part 28 files (best-effort refs)

    **Processing:**
    - Files are validated and saved to uploads directory
    - All supported formats are processed in background
    - Import statistics are returned via job status endpoint
    """
    try:
        # Validate file
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
            )

        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        safe_filename = f"{Path(file.filename).stem}_{os.urandom(4).hex()}{file_ext}"
        file_path = UPLOAD_DIR / safe_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"📁 File uploaded: {safe_filename} ({file_size} bytes)")

        # Create job ID
        job_id = f"upload_{os.urandom(8).hex()}"

        # Initialize job status in persistent store
        job_store = get_job_store()
        job_data = {
            "job_id": job_id,
            "status": "pending",
            "filename": file.filename,
            "progress": 0,
            "message": "File uploaded, queued for processing",
        }
        await job_store.create(job_id, job_data)

        # Process file based on type
        if file_ext in [".xmi", ".xml"]:
            background_tasks.add_task(process_xmi_file, file_path, job_id)
            message = "XMI file uploaded successfully. Processing in background."
        elif file_ext == ".csv":
            background_tasks.add_task(process_csv_file, file_path, job_id)
            message = "CSV file uploaded successfully. Processing in background."
        elif file_ext == ".exp":
            background_tasks.add_task(process_exp_file, file_path, job_id)
            message = "EXPRESS schema file uploaded successfully. Processing in background."
        elif file_ext == ".xsd":
            background_tasks.add_task(process_xsd_file, file_path, job_id)
            message = "XSD schema file uploaded successfully. Processing in background."
        elif file_ext in [".stp", ".step", ".stpx"]:
            background_tasks.add_task(process_step_file, file_path, job_id)
            message = "STEP file uploaded successfully. Processing in background."
        elif file_ext in [".owl", ".ttl", ".rdf", ".nq"]:
            background_tasks.add_task(process_ontology_file, file_path, job_id)
            message = "Ontology/RDF file uploaded successfully. Processing in background."
        else:
            message = "File uploaded successfully. Format not yet supported for automatic import."

        return UploadResponse(
            success=True,
            message=message,
            filename=file.filename,
            file_size=file_size,
            file_type=file_ext,
            job_id=job_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}",
        )
    finally:
        await file.close()


@router.get("/status/{job_id}", response_model=UploadStatus)
async def get_upload_status(job_id: str) -> UploadStatus:
    """
    Get the status of an upload/processing job (persisted in Redis)

    **Status Values:**
    - `pending` - File uploaded, waiting to be processed
    - `processing` - Currently processing file
    - `completed` - Successfully processed
    - `failed` - Processing failed

    **Persistence:**
    Job status is stored in Redis and persists across server restarts.
    Jobs are automatically deleted after 24 hours.
    """
    job_store = get_job_store()
    job_data = await job_store.get(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    return UploadStatus(**job_data)


@router.get("/jobs", response_class=Neo4jJSONResponse)
async def list_upload_jobs():
    """
    List all active upload jobs (from Redis)

    Returns:
        Dictionary of job_id -> job_status for all active jobs
    """
    job_store = get_job_store()
    jobs = await job_store.list_all()
    return {"count": len(jobs), "jobs": jobs}


@router.delete("/job/{job_id}")
async def delete_upload_job(job_id: str):
    """Delete upload job from Redis"""
    job_store = get_job_store()
    deleted = await job_store.delete(job_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"success": True, "message": "Job deleted"}


@router.get("/health")
async def upload_health():
    """Health check for upload service"""
    job_store = get_job_store()
    jobs = await job_store.list_all()

    return {
        "status": "healthy",
        "upload_dir": str(UPLOAD_DIR.absolute()),
        "upload_dir_exists": UPLOAD_DIR.exists(),
        "raw_data_dir": str(RAW_DATA_DIR.absolute()),
        "raw_data_dir_exists": RAW_DATA_DIR.exists(),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "active_jobs": len(jobs),
        "job_persistence": "Redis (24h TTL)",
    }
