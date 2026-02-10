#!/usr/bin/env python3
"""
AP239 Knowledge Graph Ingestion Script
============================================================================
ISO 10303-239: Product Life Cycle Support

Purpose:
    Parse AP239 EXPRESS schema modules and create Knowledge Graph nodes in Neo4j
    for requirements management, analysis, approvals, documents, and lifecycle.

Data Source:
    smrlv12/data/modules/ap239_* directories containing:
    - arm.exp (Application Reference Model)
    - mim.exp (Module Interpreted Model)

Node Types Created:
    Level 1 (Systems Engineering Core):
    - Requirement, RequirementVersion, RequirementRelationship
    - Analysis, AnalysisModel, AnalysisVersion
    - Approval, ApprovalAssignment, Certification
    - Document, DocumentVersion, Evidence
    - Activity, ActivityMethod, Effectivity
    - Event, Condition, Justification

Relationships Created:
    - SATISFIES, VERIFIES, REFINES (Requirement traceability)
    - APPROVES, CERTIFIES (Approval workflow)
    - DOCUMENTS, TRACES_TO (Document traceability)
    - DECOMPOSES_INTO, APPLIES_TO (Hierarchy)

Usage:
    python backend/scripts/ingest_ap239_v2.py [--dry-run] [--clear]

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


class AP239Ingester(BaseSchemaIngester):
    """
    Ingests AP239 Product Life Cycle Support schemas into Neo4j.
    
    Key domains:
    - Requirements Management
    - Analysis and Verification
    - Approvals and Certification
    - Document Management
    - Activity/Task Management
    - Effectivity and Configuration
    """
    
    def get_module_names(self) -> List[str]:
        """AP239 module directories in SMRL"""
        return [
            "ap239_product_life_cycle_support",
            "ap239_activity_recording",
            "ap239_document_management", 
            "ap239_management_resource_information",
            "ap239_part_definition_information",
            "ap239_product_definition_information",
            "ap239_product_status_recording",
            "ap239_properties",
            "ap239_task_specification_resourced",
            "ap239_work_definition",
        ]
    
    def get_label_map(self) -> Dict[str, str]:
        """Map EXPRESS entity names to Neo4j labels"""
        return {
            # Requirements
            "Requirement": "Requirement",
            "RequirementVersion": "RequirementVersion",
            "RequirementSource": "RequirementSource",
            "RequirementAssignment": "RequirementAssignment",
            "RequirementRelationship": "RequirementRelationship",
            "TracedRequirement": "TracedRequirement",
            # Analysis
            "Analysis": "Analysis",
            "AnalysisModel": "AnalysisModel",
            "AnalysisVersion": "AnalysisVersion",
            "AnalysisRepresentationContext": "AnalysisContext",
            "VerificationResult": "VerificationResult",
            "ValidationResult": "ValidationResult",
            # Approvals
            "Approval": "Approval",
            "ApprovalAssignment": "ApprovalAssignment",
            "ApprovalRelationship": "ApprovalRelationship",
            "Certification": "Certification",
            "CertificationAssignment": "CertificationAssignment",
            "CertificationType": "CertificationType",
            # Documents
            "Document": "Document",
            "DocumentDefinition": "DocumentDefinition",
            "DocumentVersion": "DocumentVersion",
            "DocumentRelationship": "DocumentRelationship",
            "Evidence": "Evidence",
            "DigitalFile": "DigitalFile",
            "HardcopyDocument": "HardcopyDocument",
            # Lifecycle
            "Activity": "Activity",
            "ActivityMethod": "ActivityMethod",
            "ActivityAssignment": "ActivityAssignment",
            "ActivityRelationship": "ActivityRelationship",
            "Task": "Task",
            "TaskElement": "TaskElement",
            "WorkOrder": "WorkOrder",
            "WorkRequest": "WorkRequest",
            # Effectivity
            "Effectivity": "Effectivity",
            "DatedEffectivity": "DatedEffectivity",
            "EffectivityAssignment": "EffectivityAssignment",
            "SerialEffectivity": "SerialEffectivity",
            "LotEffectivity": "LotEffectivity",
            # Breakdown
            "BreakdownElement": "BreakdownElement",
            "BreakdownVersion": "BreakdownVersion",
            "Breakdown": "Breakdown",
            "BreakdownContext": "BreakdownContext",
            # Events & Conditions
            "Event": "Event",
            "EventAssignment": "EventAssignment",
            "Condition": "Condition",
            "ConditionEvaluation": "ConditionEvaluation",
            "ConditionAssignment": "ConditionAssignment",
            # Product
            "Product": "Product",
            "ProductVersion": "ProductVersion",
            "ProductDefinition": "ProductDefinition",
            "ProductConfiguration": "ProductConfiguration",
            # Properties
            "Property": "Property",
            "PropertyAssignment": "PropertyAssignment",
            "PropertyRepresentation": "PropertyRepresentation",
            # Other
            "Assumption": "Assumption",
            "Justification": "Justification",
            "Constraint": "Constraint",
            "Contract": "Contract",
            "Collection": "Collection",
            "Resource": "Resource",
            "ResourceItem": "ResourceItem",
        }
    
    def get_ap_level(self) -> str:
        return "AP239"
    
    def get_standard(self) -> str:
        return "ISO 10303-239"
    
    def get_domain(self) -> str:
        return "Product Life Cycle Support"


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ingest AP239 EXPRESS schemas into Neo4j Knowledge Graph"
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
    ingester = AP239Ingester(
        smrl_root=smrl_root,
        dry_run=args.dry_run,
        verbose=args.verbose or True  # Always verbose for standalone run
    )
    
    try:
        stats = ingester.ingest()
        
        # Exit code based on success
        if stats["schemas_failed"] > 0:
            sys.exit(1)
        
    finally:
        ingester.close()


if __name__ == "__main__":
    main()
