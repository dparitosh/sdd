#!/usr/bin/env python3
"""
SMRL Ingestion Script (Phase 2)
============================================================================
Purpose: Ingest ISO 10303-4443 (SMRL) Schemas into the Semantic Knowledge Graph.

Functionality:
1. Walks the `smrlv12/data/resources` directory.
2. Identifies EXPRESS schemas (.exp) or XSDs (placeholder for now, expecting mapping).
3. Converts core Entities (e.g., ThermalAnalysis, Requirement) into OWL Classes.
4. Generates a SKOS vocabulary for Reference Data found in the schemas.
5. Saves the resulting Ontology as `backend/data/ontologies/smrl.owl`.

Usage:
    python scripts/ingest_smrl.py
"""

import os
import sys
from pathlib import Path
from loguru import logger
from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef
from rdflib.namespace import SKOS, DCTERMS

# Add parent directory to path
sys.path.insert(0, ".")

# Namespaces
SMRL = Namespace("http://standards.iso.org/iso/10303/-4443/ed-1/tech/ontology#")
SMRL_VOCAB = Namespace("http://standards.iso.org/iso/10303/-4443/ed-1/tech/vocab#")

class SMRLIngester:
    def __init__(self, smrl_root: str):
        self.smrl_root = Path(smrl_root)
        self.ontology = Graph()
        self.ontology.bind("smrl", SMRL)
        self.ontology.bind("skos", SKOS)
        self.ontology.bind("owl", OWL)
        
        # Initialize Ontology Header
        self.ontology.add((SMRL.Ontology, RDF.type, OWL.Ontology))
        self.ontology.add((SMRL.Ontology, DCTERMS.title, Literal("ISO 10303-4443 SMRL Ontology")))
        self.ontology.add((SMRL.Ontology, DCTERMS.description, Literal("Auto-generated from SMRLv12 resources")))

    def ingest(self):
        """Main execution flow"""
        logger.info(f"Starting SMRL Ingestion from {self.smrl_root}...")
        
        if not self.smrl_root.exists():
            logger.error(f"SMRL root path does not exist: {self.smrl_root}")
            return

        resource_dirs = [x for x in self.smrl_root.iterdir() if x.is_dir()]
        logger.info(f"Found {len(resource_dirs)} schema modules.")

        for schema_dir in resource_dirs:
            self._process_schema_module(schema_dir)
            
        # Save output
        output_dir = Path("backend/data/ontologies")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "smrl.owl"
        
        self.ontology.serialize(destination=str(output_file), format="turtle")
        logger.success(f"Ontology saved to {output_file}")
        logger.info(f"Total Triples: {len(self.ontology)}")

    def _process_schema_module(self, schema_dir: Path):
        """
        Process a specific schema folder (e.g., 'analysis_schema').
        In a real implementation, this would parse the EXPRESS file.
        Here we infer structure from the directory name as a placeholder for the parser.
        """
        schema_name = schema_dir.name
        
        # Create a Class for the Schema Module itself
        schema_uri = SMRL[self._to_camel_case(schema_name)]
        self.ontology.add((schema_uri, RDF.type, OWL.Class))
        self.ontology.add((schema_uri, RDFS.label, Literal(schema_name.replace("_", " ").title())))
        
        # Simulate extraction of entities based on schema name context
        # e.g., if schema is 'analysis_schema', create 'Analysis' concept
        if "_schema" in schema_name:
            concept_name = schema_name.replace("_schema", "")
            concept_uri = SMRL[self._to_camel_case(concept_name)]
            
            # Subclass relationship
            self.ontology.add((concept_uri, RDF.type, OWL.Class))
            self.ontology.add((concept_uri, RDFS.subClassOf, schema_uri))
            self.ontology.add((concept_uri, RDFS.label, Literal(concept_name.title())))
            
            # Simulate SKOS concept creation for reference data
            vocab_uri = SMRL_VOCAB[concept_name]
            self.ontology.add((vocab_uri, RDF.type, SKOS.Concept))
            self.ontology.add((vocab_uri, SKOS.prefLabel, Literal(concept_name.replace("_", " ").title())))
            self.ontology.add((vocab_uri, SKOS.definition, Literal(f"Concept derived from {schema_name}")))

    def _to_camel_case(self, snake_str):
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)

def main():
    smrl_path = "smrlv12/data/resources"
    ingester = SMRLIngester(smrl_path)
    ingester.ingest()

if __name__ == "__main__":
    main()
