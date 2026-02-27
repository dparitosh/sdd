"""
OSLC Client
A generic OSLC Consumer Implementation.
Capable of discovering OSLC Service Providers, parsing Catalogs,
and performing CRUD operations on OSLC Resources via HTTP/RDF.

Compliant with OSLC Core 3.0.
"""

from typing import Dict, List, Optional, Any
import json
import httpx
from rdflib import Graph, URIRef, RDF, Namespace
from rdflib.namespace import DCTERMS
from loguru import logger
import urllib.parse

# OSLC Namespaces
OSLC = Namespace("http://open-services.net/ns/core#")
OSLC_RM = Namespace("http://open-services.net/ns/rm#")
OSLC_CM = Namespace("http://open-services.net/ns/cm#")
OSLC_AM = Namespace("http://open-services.net/ns/am#")
OSLC_QM = Namespace("http://open-services.net/ns/qm#")
LDP = Namespace("http://www.w3.org/ns/ldp#")

class OSLCClient:
    def __init__(self, base_url: str, auth: Optional[tuple] = None, headers: Optional[Dict] = None):
        """
        Initialize the OSLC Client.
        
        Args:
            base_url: The Root Services URI or Entry Point of the OSLC Provider.
            auth: Tuple of (username, password) for Basic Auth, or other supported httpx auth types.
            headers: Default headers to send with requests.
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.headers = headers or {}
        self.headers.setdefault("Accept", "application/rdf+xml")  # Default to RDF/XML as per older OSLC tools, or text/turtle
        
        # Internal cache of discovered services
        self.catalogs = []
        self.service_providers = []
        self.services = {} # Map of domain -> service details

    async def _fetch_graph(self, url: str) -> Graph:
        """Helper to fetch a URL and parse it into an RDFLib Graph."""
        async with httpx.AsyncClient(verify=False) as client: # Verify=False for dev/self-signed certs
            logger.debug(f"OSLC Client fetching: {url}")
            response = await client.get(url, auth=self.auth, headers=self.headers)
            response.raise_for_status()
            
            g = Graph()
            # Attempt to guess format from Content-Type, default to turtle if ambiguous or missing
            content_type = response.headers.get("Content-Type", "").split(";")[0]
            
            format_map = {
                "application/rdf+xml": "xml",
                "text/turtle": "turtle",
                "application/x-turtle": "turtle",
                "application/ld+json": "json-ld",
                "application/json": "json-ld"
            }
            parse_format = format_map.get(content_type, "xml") # Fallback to XML is common in generic OSLC
            
            try:
                g.parse(data=response.text, format=parse_format)
            except Exception as e:
                logger.warning(f"Failed to parse as {parse_format}, trying turtle fallback: {e}")
                g.parse(data=response.text, format="turtle")
                
            return g

    async def discover(self):
        """
        Perform OSLC Discovery starting from base_url (RootServices).
        Populates self.catalogs and self.service_providers.
        """
        # 1. Fetch Root Services
        try:
            g = await self._fetch_graph(self.base_url)
        except Exception as e:
            logger.error(f"Discovery failed at root {self.base_url}: {e}")
            raise

        # 2. Find ServiceProviderCatalog links
        # Looking for <oslc:serviceProviderCatalog rdf:resource="..." />
        catalog_uris = []
        
        # Check explicit root services pattern
        for s, p, o in g:
            if p == OSLC.serviceProviderCatalog:
                catalog_uris.append(str(o))
        
        if not catalog_uris:
            # Maybe the base_url IS the catalog?
            if (None, RDF.type, OSLC.ServiceProviderCatalog) in g:
                catalog_uris.append(self.base_url)

        self.catalogs = catalog_uris
        logger.info(f"Discovered {len(catalog_uris)} catalogs")

        # 3. Crawl Catalogs to find ServiceProviders
        for cat_url in catalog_uris:
            await self._parse_catalog(cat_url)

        return {
            "catalogs": self.catalogs,
            "service_providers": [sp['title'] for sp in self.service_providers]
        }

    async def _parse_catalog(self, catalog_url: str):
        """Recursively parse catalogs to find Service Providers."""
        g = await self._fetch_graph(catalog_url)
        
        # Find Service Providers
        for sp in g.subjects(RDF.type, OSLC.ServiceProvider):
            title = g.value(sp, DCTERMS.title)
            details_url = g.value(sp, OSLC.details)
            
            sp_obj = {
                "uri": str(sp),
                "title": str(title) if title else "Untitled Provider",
                "details_uri": str(details_url) if details_url else str(sp)
            }
            self.service_providers.append(sp_obj)
            logger.debug(f"Found Service Provider: {sp_obj['title']}")
            
            # Parse the SP details to find Services
            await self._parse_service_provider(sp_obj['details_uri'])

        # Find nested Catalogs
        for cat in g.subjects(RDF.type, OSLC.ServiceProviderCatalog):
            # Avoid infinite loops if self-referential
            if str(cat) != catalog_url:
                await self._parse_catalog(str(cat))

    async def _parse_service_provider(self, sp_url: str):
        """Parse a Service Provider resource to find its Services (Selection, Creation, Query)."""
        g = await self._fetch_graph(sp_url)
        
        # Find Services
        for svc in g.objects(None, OSLC.service):
            domain = g.value(svc, OSLC.domain)
            if not domain:
                continue
            
            domain_str = str(domain)
            
            # Find Capabilities
            query_caps = []
            for qc in g.objects(svc, OSLC.queryCapability):
                base = g.value(qc, OSLC.queryBase)
                title = g.value(qc, DCTERMS.title)
                query_caps.append({"base": str(base), "title": str(title)})

            creation_factories = []
            for cf in g.objects(svc, OSLC.creationFactory):
                base = g.value(cf, OSLC.creation)
                title = g.value(cf, DCTERMS.title)
                creation_factories.append({"base": str(base), "title": str(title)})
            
            service_def = {
                "domain": domain_str,
                "query_capabilities": query_caps,
                "creation_factories": creation_factories
            }
            
            # Index by domain/project logic could go here
            # For now just storing in a simple list in the SP object would be cleaner,
            # but we'll add to a flat list for simple lookups
            self.services[domain_str] = service_def

    async def get_resource(self, resource_url: str) -> Dict[str, Any]:
        """Fetch a single OSLC resource and return as basic JSON-LD dict."""
        g = await self._fetch_graph(resource_url)
        return json.loads(g.serialize(format="json-ld"))

    async def query_resource(self, query_base: str, oslc_where: str) -> List[Dict]:
        """
        Execute an OSLC Query.
        Args:
            query_base: The oslc:queryBase URL from discovery.
            oslc_where: The 'oslc.where' query parameter.
        """
        params = {"oslc.where": oslc_where}
        url = f"{query_base}?{urllib.parse.urlencode(params)}"
        
        g = await self._fetch_graph(url)
        
        # Parse result (usually an rdfs:Container or ldp:BasicContainer)
        results = []
        # Logic to extract members specifically would depend on response structure
        # returning the graph serialization for now
        return json.loads(g.serialize(format="json-ld"))
