"""
OSLC Routes (FastAPI)
Endpoints for Open Services for Lifecycle Collaboration compliance.
Acts as an OSLC Server for RM (Requirements), AM (Architecture), and QM (Quality).
"""

import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, Query
from loguru import logger
from rdflib import Graph, URIRef, Literal, RDF
from rdflib.namespace import DCTERMS
from src.web.services import get_neo4j_service
from src.web.services.oslc_service import OSLCService, OSLC, OSLC_RM
from src.web.services.oslc_trs_service import OSLCTRSService

router = APIRouter(prefix="/oslc", tags=["OSLC Semantic Web"])

def get_trs_service() -> OSLCTRSService:
    return OSLCTRSService()

def get_oslc_service(request: Request) -> OSLCService:
    # Dynamically determine base URL from request
    base_url = str(request.base_url).rstrip("/")
    return OSLCService(base_url=base_url)

@router.get("/rootservices")
async def get_rootservices(
    request: Request,
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Entry Point (Root Services).
    Auto-discoverable by tools like IBM DOORS Next or Cameo.
    """
    logger.info(f"OSLC Discovery: RootServices [Accept: {accept}]")
    graph = oslc_service.generate_rootservices()
    result = oslc_service.serialize_response(graph, accept)
    return Response(content=result["content"], media_type=result["media_type"])

@router.get("/catalog")
async def get_service_provider_catalog(
    request: Request,
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Service Provider Catalog.
    Lists available projects/providers.
    """
    logger.info(f"OSLC Discovery: Catalog [Accept: {accept}]")
    graph = oslc_service.generate_service_provider_catalog()
    result = oslc_service.serialize_response(graph, accept)
    return Response(content=result["content"], media_type=result["media_type"])

@router.get("/sp/{project_id}")
async def get_service_provider(
    project_id: str,
    request: Request,
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Service Provider Details.
    Lists capabilities (Selection, Creation, Query) for a specific project.
    """
    logger.info(f"OSLC Discovery: ServiceProvider {project_id} [Accept: {accept}]")
    graph = oslc_service.generate_service_provider(project_id)
    result = oslc_service.serialize_response(graph, accept)
    return Response(content=result["content"], media_type=result["media_type"])

@router.get("/rm/requirements")
async def get_requirement_query_capability(
    request: Request,
    oslc_where: str = Query(None, alias="oslc.where"),
    oslc_select: str = Query(None, alias="oslc.select"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    accept: str = Header("application/rdf+xml"),
    oslc_service: OSLCService = Depends(get_oslc_service)
):
    """
    OSLC Query Capability for Requirements.
    Returns a paged list of Requirement resources matching the query.
    """
    logger.info(f"OSLC Query: Requirements where={oslc_where} [Accept: {accept}]")
    
    neo4j = get_neo4j_service()
    skip = (page - 1) * limit
    
    # 1. Build Cypher Query (Basic implementation ignoring complex oslc.where parsing for now)
    cypher = """
        MATCH (n:Requirement)
        RETURN n.id as id, n.name as name, n.description as description
        ORDER BY n.id
        SKIP $skip LIMIT $limit
    """
    
    # Note: Real oslc.where parsing would convert "dcterms:title=\"Engine\"" to Cypher
    # Here we just dump all requirements for the QueryBase
    
    results = neo4j.execute_query(cypher, {"skip": skip, "limit": limit})
    
    # 2. Build Response Graph
    g = Graph()
    g.bind("oslc", OSLC)
    g.bind("dcterms", DCTERMS)
    g.bind("rm", OSLC_RM)

    query_uri = str(request.url)
    base_uri = query_uri.split("?")[0]
    
    # ResponseInfo (Paging)
    response_info_uri = URIRef(query_uri)
    g.add((response_info_uri, RDF.type, OSLC.ResponseInfo))
    g.add((response_info_uri, DCTERMS.title, Literal("Requirements Query Results")))
    
    # Add members
    for row in results:
        res_uri = URIRef(f"{oslc_service.base_url}/api/v1/Requirement/{row['id']}")
        g.add((response_info_uri, OSLC.results, res_uri)) # or rdfs:member depending on OSLC version preference
        
        # Add basic details about each member
        g.add((res_uri, RDF.type, OSLC_RM.Requirement))
        if row['name']:
            g.add((res_uri, DCTERMS.title, Literal(row['name'])))
        if row['description']:
            g.add((res_uri, DCTERMS.description, Literal(row['description'])))
            
    # Serialize
    result = oslc_service.serialize_response(g, accept)
    return Response(content=result["content"], media_type=result["media_type"])

@router.get("/dialogs/rm/select")
async def get_selection_dialog(
    request: Request,
    api_key: str = Query(None) # Dialogs might check auth via param or cookie
):
    """
    OSLC Selection Dialog (HTML UI).
    In a full app, this returns an HTML page where user picks a requirement.
    For this API-first server, we return a simple HTML stub.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Select Requirement</title></head>
    <body>
        <h2>Select Requirement</h2>
        <p>This is a placeholder for the OSLC Selection Dialog UI.</p>
        <p>In a production app, this page would fetch data from <code>/oslc/rm/requirements</code> and execute <code>postMessage</code> to the parent window.</p>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")


# ── OSLC Creation Factory ────────────────────────────────────────────────────

@router.post("/rm/requirements", status_code=201)
async def create_requirement(
    request: Request,
    accept: str = Header("application/rdf+xml"),
    content_type: str = Header("application/rdf+xml", alias="content-type"),
    oslc_service: OSLCService = Depends(get_oslc_service),
    trs: OSLCTRSService = Depends(get_trs_service),
):
    """
    OSLC Creation Factory – POST a new Requirement resource.
    Accepts RDF/XML, Turtle, or JSON-LD payloads containing an oslc_rm:Requirement.
    Creates the resource in Neo4j and publishes a TRS Creation event.
    """
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Request body is empty")

    # Parse incoming RDF ─────────────────────────────────────────────────────
    incoming = Graph()
    try:
        if "json" in content_type:
            incoming.parse(data=body, format="json-ld")
        elif "turtle" in content_type:
            incoming.parse(data=body, format="turtle")
        else:
            incoming.parse(data=body, format="xml")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot parse RDF payload: {exc}")

    # Extract the first oslc_rm:Requirement from the graph ────────────────────
    subjects = list(incoming.subjects(RDF.type, OSLC_RM.Requirement))
    if not subjects:
        raise HTTPException(
            status_code=400,
            detail="Payload must contain at least one oslc_rm:Requirement resource",
        )
    req_subject = subjects[0]

    title = str(incoming.value(req_subject, DCTERMS.title) or "Untitled")
    description = str(incoming.value(req_subject, DCTERMS.description) or "")
    identifier = str(incoming.value(req_subject, DCTERMS.identifier) or "")

    # Persist to Neo4j ────────────────────────────────────────────────────────
    req_id = identifier or str(uuid.uuid4())
    neo4j = get_neo4j_service()
    cypher = """
        CREATE (r:Requirement {
            id: $id,
            name: $name,
            description: $description,
            created: datetime()
        })
        RETURN r.id AS id
    """
    neo4j.execute_query(cypher, {"id": req_id, "name": title, "description": description})

    # Build response RDF ──────────────────────────────────────────────────────
    res_uri = URIRef(f"{oslc_service.base_url}/api/v1/Requirement/{req_id}")
    g = Graph()
    g.bind("oslc", OSLC)
    g.bind("dcterms", DCTERMS)
    g.bind("rm", OSLC_RM)
    g.add((res_uri, RDF.type, OSLC_RM.Requirement))
    g.add((res_uri, DCTERMS.title, Literal(title)))
    g.add((res_uri, DCTERMS.identifier, Literal(req_id)))
    if description:
        g.add((res_uri, DCTERMS.description, Literal(description)))

    # Publish TRS creation event ──────────────────────────────────────────────
    try:
        trs.publish_event(str(res_uri), "creation")
    except Exception as exc:
        logger.warning(f"TRS publish failed (non-fatal): {exc}")

    logger.info(f"OSLC CreationFactory: created Requirement {req_id}")

    result = oslc_service.serialize_response(g, accept)
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        status_code=201,
        headers={"Location": str(res_uri)},
    )
