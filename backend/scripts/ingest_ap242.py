#!/usr/bin/env python3
"""
AP242 Knowledge Graph Ingestion Script
============================================================================
ISO 10303-242: Managed Model-Based 3D Engineering

Purpose:
    Parse AP242 EXPRESS schema modules and create Knowledge Graph nodes in Neo4j
    for 3D model management, design, manufacturing, and PLM.

Data Source:
    smrlv12/data/modules/ap242_* directories containing:
    - arm.exp (Application Reference Model)
    - mim.exp (Module Interpreted Model)

Node Types Created:
    Level 1 (3D Engineering Core):
    - Shape, ShapeRepresentation, GeometricModel
    - Part, Assembly, Component
    - ProductDefinition, ProductConfiguration
    - Document, File, ExternalReference
    - Annotation, PMI, Dimension, Tolerance

Relationships Created:
    - COMPOSED_OF (Assembly structure)
    - REPRESENTED_BY (Shape relationships)
    - ANNOTATES, DIMENSIONS (PMI associations)
    - REFERENCES (External file links)

Usage:
    python backend/scripts/ingest_ap242.py [--dry-run] [--clear]

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


class AP242Ingester(BaseSchemaIngester):
    """
    Ingests AP242 Managed Model-Based 3D Engineering schemas into Neo4j.
    
    Key domains:
    - 3D Shape and Geometry
    - Assembly and Product Structure
    - Product Manufacturing Information (PMI)
    - Model-Based Definition (MBD)
    - Design and Configuration Management
    """
    
    def get_module_names(self) -> List[str]:
        """AP242 module directories in SMRL"""
        return [
            "ap242_managed_model_based_3d_engineering",
            # Associated modules (may exist under different names)
            "geometric_model_relationship",
            "shape_property_assignment",
            "product_structure",
            "assembly_structure",
            "product_configuration_identification",
            "shape_appearance_layers",
            "geometric_tolerance",
            "dimensional_tolerance",
            "annotation_presentation",
            "draughting_elements",
            "shape_representation",
            "advanced_boundary_representation",
            "manifold_surface",
            "manifold_solid_brep",
            "tessellated_geometry",
            "constructive_solid_geometry",
            "surface_conditions",
            "visual_presentation",
        ]
    
    def get_label_map(self) -> Dict[str, str]:
        """Map EXPRESS entity names to Neo4j labels"""
        return {
            # Geometry & Shape
            "Shape": "Shape",
            "ShapeRepresentation": "ShapeRepresentation",
            "ShapeAspect": "ShapeAspect",
            "ShapeRelationship": "ShapeRelationship",
            "GeometricRepresentationItem": "GeometricItem",
            "AdvancedFace": "Face",
            "AdvancedBrepShapeRepresentation": "BrepShape",
            "ManifoldSolidBrep": "SolidBrep",
            "FacetedBrep": "FacetedBrep",
            "TessellatedShapeRepresentation": "TessellatedShape",
            "TriangulatedFace": "TriangulatedFace",
            # Product Structure
            "Product": "Product",
            "ProductDefinition": "ProductDefinition",
            "ProductVersion": "ProductVersion",
            "ProductDefinitionFormation": "ProductFormation",
            "ProductConfiguration": "ProductConfiguration",
            "ProductRelationship": "ProductRelationship",
            "NextAssemblyUsage": "AssemblyUsage",
            "AssemblyComponentUsage": "ComponentUsage",
            # Assembly
            "Assembly": "Assembly",
            "Component": "Component",
            "Part": "Part",
            "Subassembly": "Subassembly",
            "ProductDefinitionWithAssociatedDocuments": "ProductWithDocs",
            # Annotations & PMI
            "Annotation": "Annotation",
            "AnnotationOccurrence": "AnnotationOccurrence",
            "AnnotationPlane": "AnnotationPlane",
            "DimensionCallout": "DimensionCallout",
            "DraughtingCallout": "DraughtingCallout",
            "GeometricTolerance": "GeometricTolerance",
            "DimensionalSize": "DimensionalSize",
            "DimensionalLocation": "DimensionalLocation",
            "ToleranceValue": "ToleranceValue",
            # Views & Presentation
            "DraughtingModel": "DraughtingModel",
            "ViewDefinition": "ViewDefinition",
            "CameraModel": "CameraModel",
            "PresentationLayerAssignment": "LayerAssignment",
            "StyledItem": "StyledItem",
            # Surfaces
            "BoundedSurface": "BoundedSurface",
            "BsplineSurface": "BsplineSurface",
            "ConicalSurface": "ConicalSurface",
            "CylindricalSurface": "CylindricalSurface",
            "SphericalSurface": "SphericalSurface",
            "ToroidalSurface": "ToroidalSurface",
            "SurfaceOfRevolution": "SurfaceOfRevolution",
            # Curves
            "BsplineCurve": "BsplineCurve",
            "TrimmedCurve": "TrimmedCurve",
            "CompositeCurve": "CompositeCurve",
            "Circle": "Circle",
            "Ellipse": "Ellipse",
            "Line": "Line",
            # Material & Properties
            "Material": "Material",
            "MaterialDesignation": "MaterialDesignation",
            "MaterialProperty": "MaterialProperty",
            "PropertyDefinition": "PropertyDefinition",
            "PropertyValue": "PropertyValue",
            # Documents & Files
            "Document": "Document",
            "DocumentFile": "DocumentFile",
            "DocumentReference": "DocumentReference",
            "ExternallyDefinedItem": "ExternalItem",
            "AppliedExternalIdentificationAssignment": "ExternalId",
        }
    
    def get_ap_level(self) -> str:
        return "AP242"
    
    def get_standard(self) -> str:
        return "ISO 10303-242"
    
    def get_domain(self) -> str:
        return "Managed Model-Based 3D Engineering"


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ingest AP242 EXPRESS schemas into Neo4j Knowledge Graph"
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
    ingester = AP242Ingester(
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
