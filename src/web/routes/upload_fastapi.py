"""
File Upload API for XMI, XML, and CSV ingestion
"""

import os
import shutil
from pathlib import Path
from typing import Optional
import tempfile

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from src.parsers.semantic_loader import SemanticXMILoader
from src.web.services import get_neo4j_service
from src.web.utils.responses import Neo4jJSONResponse
from src.web.services.upload_job_store import get_job_store

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Storage configuration
UPLOAD_DIR = Path("data/uploads")
RAW_DATA_DIR = Path("data/raw")
ALLOWED_EXTENSIONS = {".xmi", ".xml", ".csv", ".json"}
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
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check filename
    if not file.filename or len(file.filename) > 255:
        return False, "Invalid filename"
    
    return True, "OK"


async def process_xmi_file(file_path: Path, job_id: str) -> dict:
    """Process XMI file in background"""
    job_store = get_job_store()
    try:
        await job_store.update(job_id, {
            "status": "processing",
            "progress": 10,
            "message": "Initializing XMI loader..."
        })
        
        # Get Neo4j connection
        neo4j_service = get_neo4j_service()
        conn = neo4j_service.driver
        
        await job_store.update(job_id, {
            "progress": 20,
            "message": "Loading XMI file..."
        })
        
        # Load XMI file
        loader = SemanticXMILoader(conn, enable_versioning=True)
        stats = loader.load_xmi_file(str(file_path))
        
        await job_store.update(job_id, {
            "progress": 90,
            "message": "Finalizing import..."
        })
        
        # Move file to raw data directory
        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)
        
        await job_store.update(job_id, {
            "status": "completed",
            "progress": 100,
            "message": f"Successfully imported {file_path.name}",
            "stats": stats
        })
        
        logger.success(f"✓ Processed XMI file: {file_path.name} - {stats}")
        return stats
        
    except Exception as e:
        await job_store.update(job_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Failed to process file: {str(e)}"
        })
        logger.error(f"✗ Failed to process XMI file: {e}")
        raise


async def process_csv_file(file_path: Path, job_id: str) -> dict:
    """Process CSV file in background"""
    job_store = get_job_store()
    try:
        await job_store.update(job_id, {
            "status": "processing",
            "progress": 10,
            "message": "Reading CSV file..."
        })
        
        # TODO: Implement CSV parsing and Neo4j import
        # For now, just copy to raw data directory
        
        await job_store.update(job_id, {
            "progress": 50,
            "message": "Importing data..."
        })
        
        destination = RAW_DATA_DIR / file_path.name
        shutil.copy(file_path, destination)
        
        await job_store.update(job_id, {
            "status": "completed",
            "progress": 100,
            "message": f"Successfully uploaded {file_path.name}",
            "stats": {"message": "CSV import not yet implemented, file saved for manual processing"}
        })
        
        logger.info(f"✓ Uploaded CSV file: {file_path.name}")
        return {"rows_imported": 0, "message": "CSV import coming soon"}
        
    except Exception as e:
        await job_store.update(job_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Failed to process file: {str(e)}"
        })
        logger.error(f"✗ Failed to process CSV file: {e}")
        raise


@router.post("/", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> UploadResponse:
    """
    Upload XMI, XML, or CSV file for ingestion into Neo4j
    
    **Supported Formats:**
    - `.xmi` - UML/SysML XMI models (Eclipse Papyrus, MagicDraw, etc.)
    - `.xml` - XML-based model files
    - `.csv` - Comma-separated values (coming soon)
    - `.json` - JSON-based model data (coming soon)
    
    **Processing:**
    - Files are validated and saved to uploads directory
    - XMI/XML files are processed immediately in background
    - Import statistics are returned via job status endpoint
    """
    try:
        # Validate file
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
        
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
            "message": "File uploaded, queued for processing"
        }
        await job_store.create(job_id, job_data)
        
        # Process file based on type
        if file_ext in [".xmi", ".xml"]:
            background_tasks.add_task(process_xmi_file, file_path, job_id)
            message = "XMI file uploaded successfully. Processing in background."
        elif file_ext == ".csv":
            background_tasks.add_task(process_csv_file, file_path, job_id)
            message = "CSV file uploaded successfully. Processing in background."
        else:
            message = "File uploaded successfully. Format not yet supported for automatic import."
        
        return UploadResponse(
            success=True,
            message=message,
            filename=file.filename,
            file_size=file_size,
            file_type=file_ext,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
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
        "job_persistence": "Redis (24h TTL)"
    }
