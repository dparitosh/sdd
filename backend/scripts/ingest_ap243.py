#!/usr/bin/env python3
"""
AP243 Knowledge Graph Ingestion Script
============================================================================
ISO 10303-243: MoSSEC - Modeling and Simulation for Systems Engineering Core

Purpose:
    Parse AP243/MoSSEC EXPRESS schema modules and create Knowledge Graph nodes 
    for systems modeling, simulation, and MBSE (Model-Based Systems Engineering).

Data Source:
    smrlv12/data/modules/ap243_* directories containing:
    - arm.exp (Application Reference Model)
    - mim.exp (Module Interpreted Model)

Node Types Created:
    Level 1 (Systems Engineering Core):
    - System, Subsystem, SystemElement
    - Function, FunctionalElement, FunctionalUnit
    - Interface, Port, Connection
    - Behavior, State, Transition
    - Parameter, Variable, Constraint

Relationships Created:
    - REALIZES (Function to Component)
    - CONNECTS_TO (Interface relationships)
    - ALLOCATED_TO (Allocation relationships)
    - FLOWS_TO (Signal/Data flow)
    - HAS_STATE, TRANSITIONS_TO (Behavior)

Usage:
    python backend/scripts/ingest_ap243.py [--dry-run] [--clear]

Configuration:
    Uses .env for Neo4j connection settings
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from loguru import logger

from backend.scripts.base_ingester import BaseSchemaIngester


class AP243Ingester(BaseSchemaIngester):
    """
    Ingests AP243 MoSSEC (Systems Engineering) schemas into Neo4j.
    
    Key domains:
    - System Architecture
    - Functional Modeling
    - Interface Definition
    - Behavior Modeling
    - Simulation Configuration
    """
    
    def get_module_names(self) -> List[str]:
        """AP243/MoSSEC module directories in SMRL"""
        return [
            # Core AP243 modules
            "ap243_mossec",
            "ap243_model_simulation_system_engineering",
            # Systems Modeling modules
            "system_modelling",
            "system_structure", 
            "system_breakdown",
            "functional_breakdown",
            "functional_decomposition",
            # Interface modules
            "interface_definition",
            "interface_specification",
            "connection_definition",
            "port_specification",
            # Behavior modules
            "behavior_definition",
            "state_definition",
            "state_machine_definition",
            "activity_specification",
            # Analysis modules  
            "analysis_definition",
            "simulation_definition",
            "parameter_definition",
            "constraint_definition",
            # Supporting modules
            "value_with_unit",
            "qualified_measure",
            "measure_representation",
        ]
    
    def get_label_map(self) -> Dict[str, str]:
        """Map EXPRESS entity names to Neo4j labels"""
        return {
            # Systems
            "System": "System",
            "SystemElement": "SystemElement",
            "Subsystem": "Subsystem",
            "SystemBreakdown": "SystemBreakdown",
            "SystemView": "SystemView",
            "SystemContext": "SystemContext",
            # Functions
            "Function": "Function",
            "FunctionalElement": "FunctionalElement",
            "FunctionalUnit": "FunctionalUnit",
            "FunctionalBreakdown": "FunctionalBreakdown",
            "FunctionDefinition": "FunctionDefinition",
            "FunctionalArchitecture": "FunctionalArchitecture",
            # Interfaces & Ports
            "Interface": "Interface",
            "InterfaceDefinition": "InterfaceDefinition",
            "InterfaceSpecification": "InterfaceSpecification",
            "Port": "Port",
            "PortDefinition": "PortDefinition",
            "Connection": "Connection",
            "ConnectionDefinition": "ConnectionDefinition",
            "Connector": "Connector",
            "Link": "Link",
            # Behavior
            "Behavior": "Behavior",
            "BehaviorDefinition": "BehaviorDefinition",
            "State": "State",
            "StateDefinition": "StateDefinition",
            "StateMachine": "StateMachine",
            "Transition": "Transition",
            "Activity": "Activity",
            "ActivityDefinition": "ActivityDefinition",
            "Action": "Action",
            # Analysis & Simulation
            "Analysis": "Analysis",
            "AnalysisModel": "AnalysisModel",
            "Simulation": "Simulation",
            "SimulationModel": "SimulationModel",
            "SimulationRun": "SimulationRun",
            # Parameters & Constraints
            "Parameter": "Parameter",
            "ParameterDefinition": "ParameterDefinition",
            "ParameterValue": "ParameterValue",
            "Variable": "Variable",
            "Constraint": "Constraint",
            "ConstraintDefinition": "ConstraintDefinition",
            # Values
            "Value": "Value",
            "ValueWithUnit": "ValueWithUnit",
            "QualifiedMeasure": "QualifiedMeasure",
            "MeasureRepresentation": "MeasureRepresentation",
            # Allocation
            "Allocation": "Allocation",
            "AllocationRelationship": "AllocationRelationship",
            "FunctionToComponentAllocation": "FunctionAllocation",
            # Flow
            "Flow": "Flow",
            "DataFlow": "DataFlow",
            "SignalFlow": "SignalFlow",
            "MaterialFlow": "MaterialFlow",
            "EnergyFlow": "EnergyFlow",
            # Requirements (from SysML alignment)
            "Requirement": "Requirement",
            "Stakeholder": "Stakeholder",
            "UseCase": "UseCase",
            "Scenario": "Scenario",
        }
    
    def get_ap_level(self) -> str:
        return "AP243"
    
    def get_standard(self) -> str:
        return "ISO 10303-243"
    
    def get_domain(self) -> str:
        return "MoSSEC - Modeling and Simulation for Systems Engineering"


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ingest AP243/MoSSEC EXPRESS schemas into Neo4j Knowledge Graph"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse schemas without writing to Neo4j"
    )
    parser.add_argument(
        "--smrl-root",
        type=str,
        default=None,
        help="Path to SMRL root directory (default: PROJECT_ROOT/smrlv12)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine SMRL root
    if args.smrl_root:
        smrl_root = Path(args.smrl_root)
    else:
        smrl_root = PROJECT_ROOT / "smrlv12"
    
    if not smrl_root.exists():
        logger.error(f"SMRL root not found: {smrl_root}")
        sys.exit(1)
    
    # Load environment
    load_dotenv()
    
    # Create and run ingester
    ingester = AP243Ingester(
        smrl_root=smrl_root,
        dry_run=args.dry_run,
        verbose=args.verbose or True
    )
    
    try:
        stats = ingester.ingest()
        
        if stats["schemas_failed"] > 0:
            sys.exit(1)
            
    finally:
        ingester.close()


if __name__ == "__main__":
    main()
