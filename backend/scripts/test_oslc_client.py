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
    logger.info("Initializing OSLC Client...")
    client = OSLCClient()
    
    # Target our own server (assuming it's running on port 5000 or 8000)
    # The default app_fastapi.py runs on port 5000 according to the __main__ block
    target_url = "http://localhost:5000/oslc/catalog" 
    
    logger.info(f"Connecting to {target_url}...")
    try:
        provider = await client.discover(target_url)
        logger.info(f"Discovery successful!")
        logger.info(f"Provider Title: {provider.get('title', 'Unknown')}")
        logger.info(f"Services found: {len(provider.get('services', []))}")
        
        for svc in provider.get('services', []):
            logger.info(f" - Service: {svc.get('domain')}")
            for creation in svc.get('creation_factories', []):
                logger.info(f"   + Creation Factory: {creation.get('creation')}")
            for query in svc.get('query_capabilities', []):
                logger.info(f"   + Query Capability: {query.get('query_base')}")
                
    except Exception as e:
        logger.error(f"Client test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
