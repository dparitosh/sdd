"""
OSLC Service
Handles the core logic for Open Services for Lifecycle Collaboration (OSLC).
Generates Service Provider Catalogs, Service Providers, and Resource Shapes.
Supports Content Negotiation (RDF/XML, Turtle, JSON-LD).
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import json
from loguru import logger
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCTERMS, FOAF, XSD
from fastapi import Request

from src.web.utils.runtime_config import get_public_base_url

# Define standard OSLC Namespaces
OSLC = Namespace("http://open-services.net/ns/core#")
OSLC_RM = Namespace("http://open-services.net/ns/rm#")
OSLC_AM = Namespace("http://open-services.net/ns/am#")
OSLC_QM = Namespace("http://open-services.net/ns/qm#")
OSLC_CM = Namespace("http://open-services.net/ns/cm#")
MBSE = Namespace("http://mbse-mossec.com/ns/core#")

class OSLCService:
    def __init__(self, base_url: str | None = None):
        resolved = base_url or get_public_base_url()
        self.base_url = resolved.rstrip("/")
        
    def generate_rootservices(self) -> Graph:
        """
        Generate the Root Services document (Entry Point).
        This tells external tools where the specific catalogues are (RM, AM, etc.).
        """
        g = Graph()
        g.bind("oslc", OSLC)
        g.bind("dcterms", DCTERMS)
        
        root_uri = URIRef(f"{self.base_url}/oslc/rootservices")
        g.add((root_uri, RDF.type, OSLC.ServiceDescriptor))
        g.add((root_uri, DCTERMS.title, Literal("MBSE/MOSSEC Root Services")))
        g.add((root_uri, DCTERMS.description, Literal("Entry point for MBSE Graph OSLC Services")))
        
        # Link to Catalog
        catalog_uri = URIRef(f"{self.base_url}/oslc/catalog")
        g.add((root_uri, OSLC.serviceProviderCatalog, catalog_uri))
        
        return g

    def generate_service_provider_catalog(self) -> Graph:
        """
        Generate the Service Provider Catalog.
        Lists all the Projects (Service Providers) hosted this server.
        """
        g = Graph()
        g.bind("oslc", OSLC)
        g.bind("dcterms", DCTERMS)
        
        catalog_uri = URIRef(f"{self.base_url}/oslc/catalog")
        g.add((catalog_uri, RDF.type, OSLC.ServiceProviderCatalog))
        g.add((catalog_uri, DCTERMS.title, Literal("MBSE Service Provider Catalog")))
        g.add((catalog_uri, OSLC.domain, URIRef(str(OSLC_RM))))
        # g.add((catalog_uri, OSLC.domain, URIRef(str(OSLC_AM)))) # Uncomment when AM is ready
        
        # In a real scenario, we would loop through "Projects" in Neo4j
        # For now, we expose a single "Default Project" Service Provider
        sp_uri = URIRef(f"{self.base_url}/oslc/sp/default")
        g.add((catalog_uri, OSLC.serviceProvider, sp_uri))
        
        # Define the Service Provider inline details
        g.add((sp_uri, RDF.type, OSLC.ServiceProvider))
        g.add((sp_uri, DCTERMS.title, Literal("Default MBSE Project")))
        g.add((sp_uri, OSLC.details, sp_uri))
        
        return g

    def generate_service_provider(self, project_id: str) -> Graph:
        """
        Generate the details for a specific Service Provider (Project).
        This lists the Services (Selection, Creation, Query) available.
        """
        g = Graph()
        g.bind("oslc", OSLC)
        
        sp_uri = URIRef(f"{self.base_url}/oslc/sp/{project_id}")
        g.add((sp_uri, RDF.type, OSLC.ServiceProvider))
        g.add((sp_uri, DCTERMS.title, Literal(f"Project {project_id}")))
        
        # -- Requirements Management Service --
        rm_service = URIRef(f"{sp_uri}/service/rm")
        g.add((sp_uri, OSLC.service, rm_service))
        g.add((rm_service, RDF.type, OSLC.Service))
        g.add((rm_service, OSLC.domain, URIRef(str(OSLC_RM))))

        # Query Capability
        query_cap = URIRef(f"{rm_service}/query")
        g.add((rm_service, OSLC.queryCapability, query_cap))
        g.add((query_cap, RDF.type, OSLC.QueryCapability))
        g.add((query_cap, DCTERMS.title, Literal("Requirement Query Capability")))
        g.add((query_cap, OSLC.queryBase, URIRef(f"{self.base_url}/oslc/rm/requirements")))
        
        # Selection Dialog
        sel_dialog = URIRef(f"{rm_service}/selector")
        g.add((rm_service, OSLC.selectionDialog, sel_dialog))
        g.add((sel_dialog, RDF.type, OSLC.Dialog))
        g.add((sel_dialog, DCTERMS.title, Literal("Select Requirement")))
        g.add((sel_dialog, OSLC.dialogURI, URIRef(f"{self.base_url}/oslc/dialogs/rm/select")))
        
        return g

    def serialize_response(self, graph: Graph, accept_header: str) -> Dict[str, str]:
        """
        Helper to serialize RDF graph based on Accept header content negotiation.
        """
        if "application/ld+json" in accept_header or "application/json" in accept_header:
            return {
                "content": graph.serialize(format="json-ld"),
                "media_type": "application/ld+json"
            }
        elif "text/turtle" in accept_header:
            return {
                "content": graph.serialize(format="turtle"),
                "media_type": "text/turtle"
            }
        else:
            # Default to RDF/XML (Standard OSLC preference)
            return {
                "content": graph.serialize(format="xml"),
                "media_type": "application/rdf+xml"
            }
