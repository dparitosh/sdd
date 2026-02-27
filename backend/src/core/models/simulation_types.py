"""
Simulation & parameter-related shared types.

Canonical Pydantic schemas for simulation runs, models, parameters,
constraints, units, and validation structures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Parameter types ──────────────────────────────────────────────

class Multiplicity(BaseModel):
    """Lower/upper bound for a parameter multiplicity."""
    lower: Optional[str] = None
    upper: Optional[str] = None


class ParameterOwner(BaseModel):
    """Owning class/block reference for a parameter."""
    name: str
    id: str


class ParameterConstraint(BaseModel):
    """Constraint attached to a simulation parameter."""
    id: str
    name: str
    body: Optional[str] = None
    type: Optional[str] = None


class SimulationParameter(BaseModel):
    """Full simulation parameter with type info and constraints."""
    id: str
    name: str
    property_type: Optional[str] = None
    data_type: Optional[str] = None
    type_id: Optional[str] = None
    visibility: Optional[str] = None
    multiplicity: Optional[Multiplicity] = None
    default_value: Optional[Any] = None
    aggregation: Optional[str] = None
    is_derived: Optional[bool] = None
    is_read_only: Optional[bool] = None
    owner: Optional[ParameterOwner] = None
    constraints: Optional[List[ParameterConstraint]] = None


class SimulationParametersResponse(BaseModel):
    """Paginated parameter list response."""
    total: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    parameters: List[SimulationParameter] = Field(default_factory=list)


class ParameterValueInput(BaseModel):
    """User-supplied parameter value for validation."""
    id: str
    value: Any = None


class ValidationRequest(BaseModel):
    """Request body for parameter validation."""
    parameters: List[ParameterValueInput]


class ValidationResult(BaseModel):
    """Validation outcome for a single parameter."""
    parameter_id: str
    parameter_name: Optional[str] = None
    value: Any = None
    valid: bool = True
    violations: List[str] = Field(default_factory=list)
    constraints_checked: int = 0


class ValidationResponse(BaseModel):
    """Aggregate validation response."""
    total_parameters: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    results: List[ValidationResult] = Field(default_factory=list)


# ── Unit types ───────────────────────────────────────────────────

class UnitType(BaseModel):
    """Unit of measurement / enumeration type."""
    id: str
    name: str
    type: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    usage_count: int = 0
    literals: Optional[List[str]] = None


class UnitProperty(BaseModel):
    """Property that uses a specific unit type."""
    id: str
    name: str
    data_type: Optional[str] = None
    owner_class: Optional[str] = None


class UnitTypesInfo(BaseModel):
    total: int = 0
    types: List[UnitType] = Field(default_factory=list)


class UnitPropertiesInfo(BaseModel):
    total: int = 0
    properties: List[UnitProperty] = Field(default_factory=list)


class UnitsResponse(BaseModel):
    """Combined unit types + properties response."""
    unit_types: UnitTypesInfo = Field(default_factory=UnitTypesInfo)
    unit_properties: UnitPropertiesInfo = Field(default_factory=UnitPropertiesInfo)


# ── Simulation model summaries ───────────────────────────────────

class SimulationModelSummary(BaseModel):
    """Lightweight simulation model reference."""
    id: str
    name: str
    parameter_count: int = 0
    constraint_count: int = 0


class SimulationModelsResponse(BaseModel):
    total: int = 0
    models: List[SimulationModelSummary] = Field(default_factory=list)


class SimulationResultSummary(BaseModel):
    """Simulation result / output summary."""
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    created_on: Optional[str] = None
    last_modified: Optional[str] = None
    model_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None


class SimulationResultsResponse(BaseModel):
    total: int = 0
    results: List[SimulationResultSummary] = Field(default_factory=list)


# ── Simulation run types ─────────────────────────────────────────

class SimulationRunSummary(BaseModel):
    """Lightweight simulation run reference."""
    id: str
    sim_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    solver_version: Optional[str] = None
    credibility_level: Optional[str] = None
    mesh_elements: Optional[int] = None
    cpu_hours: Optional[float] = None
    generated_artifacts: List[str] = Field(default_factory=list)
    ap_level: Optional[str] = None


class SimulationRunDetail(BaseModel):
    """Full simulation run with dossier and artifact associations."""
    id: str
    sim_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timestamp: Optional[str] = None
    status: Optional[str] = None
    solver_version: Optional[str] = None
    credibility_level: Optional[str] = None
    mesh_elements: Optional[int] = None
    convergence_tolerance: Optional[float] = None
    cpu_hours: Optional[float] = None
    dossier_id: Optional[str] = None
    dossier_name: Optional[str] = None
    generated_artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    ap_level: Optional[str] = None
    ap_schema: Optional[str] = None


class CreateSimulationRunInput(BaseModel):
    """Input schema for creating a new simulation run."""
    id: str
    sim_type: str
    timestamp: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    run_status: str = "Running"
    solver_version: Optional[str] = None
    credibility_level: str = "PC2"
    mesh_elements: Optional[int] = None
    convergence_tolerance: Optional[float] = None
    cpu_hours: Optional[float] = None
    dossier_id: Optional[str] = None


# ── KPI / metrics (new canonical types) ─────────────────────────

class KPIData(BaseModel):
    """Key Performance Indicator measurement."""
    name: str
    value: float
    unit: Optional[str] = None
    target: Optional[float] = None
    threshold_low: Optional[float] = None
    threshold_high: Optional[float] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None
