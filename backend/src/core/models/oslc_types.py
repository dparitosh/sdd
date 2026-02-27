"""
OSLC (Open Services for Lifecycle Collaboration) shared types.

Pydantic schemas for OSLC service provider, root services,
tracked resource set, and RDF data structures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OSLCServiceProvider(BaseModel):
    """OSLC Service Provider metadata."""
    title: str
    description: str = ""
    publisher: str = ""
    identifier: str = ""
    services: List[Dict[str, Any]] = Field(default_factory=list)


class OSLCRootServices(BaseModel):
    """OSLC Root Services document."""
    title: str = "MBSEsmrl OSLC Root Services"
    publisher: str = "MBSEsmrl"
    catalog_url: str = ""
    service_providers: List[OSLCServiceProvider] = Field(default_factory=list)


class TRSChangeEntry(BaseModel):
    """Single entry in a Tracked Resource Set changelog."""
    order: int
    changed: str  # resource URI
    change_type: str  # "Creation" | "Modification" | "Deletion"
    timestamp: Optional[datetime] = None


class TRSBase(BaseModel):
    """TRS Base — list of member URIs at a point in time."""
    base_url: str
    members: List[str] = Field(default_factory=list)
    cutoff_event: Optional[int] = None


class TRSChangelog(BaseModel):
    """TRS Changelog — ordered list of change entries."""
    changelog_url: str
    entries: List[TRSChangeEntry] = Field(default_factory=list)
