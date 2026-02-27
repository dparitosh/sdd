import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.web.services.oslc_client import OSLCClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_client():
    # Target our own server (assuming it's running on port 5000)
    # The default app_fastapi.py runs on port 5000 according to the __main__ block
    target_url = "http://localhost:5000/oslc/catalog" 

    logger.info(f"Initializing OSLC Client with base_url={target_url}")
    client = OSLCClient(target_url)
    
    logger.info(f"Connect/Discovering...")
    try:
        summary = await client.discover()
        logger.info(f"Discovery successful!")
        logger.info(f"Catalogs found: {summary.get('catalogs')}")
        logger.info(f"Providers found: {summary.get('service_providers')}")
        
        logger.info(f"Services Details ({len(client.services)} domains found):")
        for domain, svc in client.services.items():
            logger.info(f" - Domain: {domain}")
            for creation in svc.get('creation_factories', []):
                logger.info(f"   + Creation Factory: {creation.get('title')} ({creation.get('base')})")
            for query in svc.get('query_capabilities', []):
                logger.info(f"   + Query Capability: {query.get('title')} ({query.get('base')})")
                
    except Exception as e:
        logger.error(f"Client test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
