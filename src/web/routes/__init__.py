"""
Web Routes - Blueprint-based route modules
"""

from .core import core_bp
from .smrl_v1 import smrl_bp

__all__ = ["smrl_bp", "core_bp"]
