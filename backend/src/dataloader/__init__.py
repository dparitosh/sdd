"""
MBSEsmrl Dataloader — Independent FastAPI Batch Processing Utility
===================================================================
A standalone FastAPI application for data ingestion and batch processing.

Can be deployed independently as:
  - A standalone service (uvicorn src.dataloader.app:app)
  - A FaaS function (via Mangum handler)
  - A CLI tool (python -m src.dataloader.cli)

Domains:
  - XMI (UML/SysML) ingestion
  - XSD (W3C XML Schema) ingestion
  - STEP (ISO 10303-21/28) ingestion
  - EXPRESS (.exp) schema ingestion
  - OWL/RDF ontology ingestion
  - OSLC vocabulary seeding
  - Semantic layer augmentation
  - SDD (Simulation Data Dossier) loading
  - Cross-schema linking (AP239↔AP242↔AP243)
  - Schema migrations (versioned)
  - Full pipeline orchestration
"""
