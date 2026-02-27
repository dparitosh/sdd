"""
OSLC service layer.

Combines OSLC provider, client, and TRS services.
Currently delegates to the web service layer.
"""
from src.web.services.oslc_service import OSLCService  # noqa: F401
from src.web.services.oslc_trs_service import TRSService  # noqa: F401
from src.web.services.oslc_client import OSLCClient  # noqa: F401
