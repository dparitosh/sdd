from pyoslc.resources.mixins import OSLCResource
from rdflib import Graph
from loguru import logger
import pyshacl
import os

class SHACLValidator:
    """
    Validates semantic data against ISO 10303 (AP239/AP242) SHACL shapes.
    """
    
    SHAPES_DIR = os.path.join(os.path.dirname(__file__), "shapes")

    @staticmethod
    def validate_graph(data_graph: Graph, standard: str = "ap239") -> bool:
        """
        Validate an RDF graph against a specific standard's shapes.
        
        Args:
            data_graph (Graph): The RDF data to validate.
            standard (str): 'ap239' or 'ap242'.
            
        Returns:
            bool: True if compliant, False otherwise.
        """
        shape_file = "ap239_requirement.ttl" if standard == "ap239" else "ap242_part.ttl"
        shape_path = os.path.join(SHACLValidator.SHAPES_DIR, shape_file)
        
        if not os.path.exists(shape_path):
            logger.error(f"Shape file not found: {shape_path}")
            return False

        # Load Shapes Graph
        shacl_graph = Graph()
        shacl_graph.parse(shape_path, format="turtle")

        conforms, report_graph, report_text = pyshacl.validate(
            data_graph,
            shacl_graph=shacl_graph,
            inference='rdfs',
            abort_on_first=False,
            meta_shacl=False,
            advanced=True
        )

        if not conforms:
            logger.warning(f"SHACL Validation Failed for {standard}:")
            logger.warning(report_text)
            
        return conforms
