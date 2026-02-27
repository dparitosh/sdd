"""
Ingester registry – self-service plugin discovery.

Every ingester subclass registers itself here via ``registry.register()``.
The pipeline and CLI use the registry to discover available ingesters at
runtime without hard-coding imports.
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from loguru import logger

from src.engine.protocol import BaseIngester


class IngesterRegistry:
    """Thread-safe registry mapping ingester names → classes."""

    def __init__(self) -> None:
        self._ingesters: Dict[str, Type[BaseIngester]] = {}

    # -- mutators ----------------------------------------------------------

    def register(self, ingester_cls: Type[BaseIngester]) -> Type[BaseIngester]:
        """
        Register an ingester class. Can be used as a decorator::

            @registry.register
            class MyIngester(BaseIngester):
                ...
        """
        # Instantiate briefly to read the name property
        instance = ingester_cls.__new__(ingester_cls)
        # For name property, we initialize minimally
        try:
            name = ingester_cls.name.fget(instance)  # type: ignore[attr-defined]
        except Exception:
            name = getattr(ingester_cls, '_name', ingester_cls.__name__)

        if name in self._ingesters:
            logger.warning(f"Overwriting existing ingester registration: {name}")
        self._ingesters[name] = ingester_cls
        logger.debug(f"Registered ingester: {name} -> {ingester_cls.__name__}")
        return ingester_cls

    def unregister(self, name: str) -> None:
        self._ingesters.pop(name, None)

    # -- accessors ---------------------------------------------------------

    def get(self, name: str) -> Optional[Type[BaseIngester]]:
        return self._ingesters.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._ingesters.keys())

    def all(self) -> Dict[str, Type[BaseIngester]]:
        return dict(self._ingesters)

    def __contains__(self, name: str) -> bool:
        return name in self._ingesters

    def __len__(self) -> int:
        return len(self._ingesters)

    def __repr__(self) -> str:
        return f"IngesterRegistry({self.list_names()})"


# Global singleton – importable from ``src.engine``
registry = IngesterRegistry()
