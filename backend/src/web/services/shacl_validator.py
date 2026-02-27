from rdflib import Graph
from loguru import logger
import pyshacl
import os
from typing import Dict, Optional, Tuple

class SHACLValidator:
    """
    Validates semantic data against ISO 10303 (AP239/AP242) and SDD v4.0 SHACL shapes.
    """

    # Legacy shapes (web/services/shapes/)
    SHAPES_DIR = os.path.join(os.path.dirname(__file__), "shapes")

    # SDD v4.0 shapes (src/models/shapes/)
    SDD_SHAPES_DIR = os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, "models", "shapes"
    )

    # Map standard names to shape files
    _SHAPE_MAP: Dict[str, Tuple[str, str]] = {
        # (directory, filename)
        "ap239": ("legacy", "ap239_requirement.ttl"),
        "ap242": ("legacy", "ap242_part.ttl"),
        "sdd_dossier": ("sdd", "sdd_dossier.ttl"),
        "approval_record": ("sdd", "approval_record.ttl"),
    }

    @classmethod
    def _resolve_shape_path(cls, standard: str) -> Optional[str]:
        """Resolve the absolute path for a shape file by standard name."""
        entry = cls._SHAPE_MAP.get(standard)
        if entry is None:
            logger.error(f"Unknown standard/shape name: '{standard}'")
            return None

        directory, filename = entry
        if directory == "legacy":
            base = cls.SHAPES_DIR
        else:
            base = cls.SDD_SHAPES_DIR

        shape_path = os.path.normpath(os.path.join(base, filename))
        if not os.path.exists(shape_path):
            logger.error(f"Shape file not found: {shape_path}")
            return None
        return shape_path

    @classmethod
    def list_available_shapes(cls) -> list[str]:
        """Return the list of registered shape names."""
        return sorted(cls._SHAPE_MAP.keys())

    @staticmethod
    def validate_graph(data_graph: Graph, standard: str = "ap239") -> bool:
        """
        Validate an RDF graph against a specific standard's shapes.
        
        Args:
            data_graph (Graph): The RDF data to validate.
            standard (str): 'ap239', 'ap242', 'sdd_dossier', or 'approval_record'.
            
        Returns:
            bool: True if compliant, False otherwise.
        """
        shape_path = SHACLValidator._resolve_shape_path(standard)
        if shape_path is None:
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

    @staticmethod
    def validate_graph_detailed(
        data_graph: Graph, standard: str = "ap239"
    ) -> dict:
        """
        Validate and return detailed results (conforms, report text, graph).

        Args:
            data_graph (Graph): The RDF data to validate.
            standard (str): Shape name (see list_available_shapes()).

        Returns:
            dict with keys: conforms (bool), report_text (str), report_graph (Graph | None)
        """
        shape_path = SHACLValidator._resolve_shape_path(standard)
        if shape_path is None:
            return {
                "conforms": False,
                "report_text": f"Shape file for '{standard}' not found.",
                "report_graph": None,
            }

        shacl_graph = Graph()
        shacl_graph.parse(shape_path, format="turtle")

        conforms, report_graph, report_text = pyshacl.validate(
            data_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
            abort_on_first=False,
            meta_shacl=False,
            advanced=True,
        )

        if not conforms:
            logger.warning(f"SHACL Validation Failed for {standard}:")
            logger.warning(report_text)

        return {
            "conforms": conforms,
            "report_text": report_text,
            "report_graph": report_graph,
        }
