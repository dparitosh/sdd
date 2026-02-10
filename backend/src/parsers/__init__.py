"""XMI and EXPRESS parsers package"""

# Lazy imports to avoid dependency issues
def _get_xmi_parser():
    from .xmi_parser import XMIParser
    return XMIParser

# Direct subpackage access (no top-level import needed)
# from .express import ExpressParser  # Use: from src.parsers.express import ExpressParser

__all__ = ["XMIParser"]

# For backwards compatibility, expose XMIParser at package level
# only when explicitly requested
def __getattr__(name):
    if name == "XMIParser":
        return _get_xmi_parser()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
