"""
Unified Neo4j connection pool.

Replaces three independent connection paths:
  1. ``Neo4jService``  (web layer) — 50-connection pool with retry
  2. ``Neo4jGraphStore`` (engine layer) — bare driver, no pool tuning
  3. ``Neo4jConnection`` (graph/ module) — bare driver

Now every consumer calls ``get_driver()`` which returns the **single**
shared driver instance, or ``Neo4jPool`` for a slightly richer API.

Usage::

    from src.core.database import get_driver, get_pool

    # Quick one-off query
    driver = get_driver()
    records, _, _ = driver.execute_query("MATCH (n) RETURN count(n) AS c")

    # Pool wrapper (recommended for services)
    pool = get_pool()
    result = pool.execute_read("MATCH (n) RETURN n LIMIT 10")
    pool.close()  # only when the entire app shuts down
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional

from loguru import logger
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable


_lock = threading.Lock()
_shared_driver: Optional[Driver] = None


# ---------------------------------------------------------------------------
# Low-level driver singleton
# ---------------------------------------------------------------------------

def get_driver() -> Driver:
    """Return the process-wide Neo4j driver (created lazily on first call).

    The driver is configured from ``core.config.Settings`` and uses the
    tuned pool parameters previously hardcoded in ``Neo4jService``.
    """
    global _shared_driver
    if _shared_driver is not None:
        return _shared_driver

    with _lock:
        if _shared_driver is not None:          # double-checked locking
            return _shared_driver

        from src.core.config import get_settings

        s = get_settings()

        last_exc: Optional[Exception] = None
        for attempt in range(1, s.neo4j_max_retry_attempts + 1):
            temp: Optional[Driver] = None
            try:
                logger.debug(
                    f"Creating Neo4j driver for {s.neo4j_uri} "
                    f"(attempt {attempt}/{s.neo4j_max_retry_attempts})"
                )
                temp = GraphDatabase.driver(
                    s.neo4j_uri,
                    auth=(s.neo4j_user, s.neo4j_password),
                    max_connection_pool_size=s.neo4j_max_pool_size,
                    connection_acquisition_timeout=s.neo4j_connection_acquisition_timeout,
                    max_transaction_retry_time=s.neo4j_max_transaction_retry_time,
                    connection_timeout=s.neo4j_connection_timeout,
                    max_connection_lifetime=s.neo4j_max_connection_lifetime,
                    keep_alive=s.neo4j_keep_alive,
                )
                temp.verify_connectivity()
                _shared_driver = temp
                logger.info("Neo4j driver created successfully")
                return _shared_driver
            except Exception as exc:
                last_exc = exc
                logger.warning(f"Neo4j attempt {attempt} failed: {exc}")
                if temp is not None:
                    try:
                        temp.close()
                    except Exception:
                        pass
                if attempt < s.neo4j_max_retry_attempts:
                    time.sleep(s.neo4j_retry_base_delay * attempt)

        msg = f"Cannot connect to Neo4j after {s.neo4j_max_retry_attempts} attempts"
        if last_exc:
            raise ServiceUnavailable(msg) from last_exc
        raise ServiceUnavailable(msg)


def close_driver() -> None:
    """Close the shared driver (call at application shutdown)."""
    global _shared_driver
    with _lock:
        if _shared_driver is not None:
            _shared_driver.close()
            _shared_driver = None
            logger.info("Neo4j shared driver closed")


def reset_driver() -> None:
    """Tear down and recreate on next ``get_driver()`` call — useful in tests."""
    close_driver()


# ---------------------------------------------------------------------------
# Higher-level pool wrapper
# ---------------------------------------------------------------------------

class Neo4jPool:
    """Thin convenience wrapper around the shared ``Driver``.

    Provides ``execute_read`` / ``execute_write`` helpers that open a
    session, run the query, and return ``List[Dict]``.  Designed to be a
    drop-in replacement for the query methods scattered across
    ``Neo4jService``, ``Neo4jConnection``, and ``Neo4jGraphStore``.
    """

    def __init__(self, driver: Optional[Driver] = None, database: Optional[str] = None):
        self._driver = driver or get_driver()
        if database is None:
            from src.core.config import get_settings
            database = get_settings().neo4j_database
        self.database = database

    # -- properties --------------------------------------------------------

    @property
    def driver(self) -> Driver:
        return self._driver

    # -- read / write helpers -----------------------------------------------

    def execute_read(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a read query and return a list of record dicts."""
        with self._driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    # alias used by the legacy graph/connection.py API
    execute_query = execute_read

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Execute a write transaction."""

        def _tx(tx, q, p):
            tx.run(q, p)

        with self._driver.session(database=self.database) as session:
            session.execute_write(_tx, query, parameters or {})

    def verify_connectivity(self) -> bool:
        """Quick ``RETURN 1`` check."""
        try:
            with self._driver.session(database=self.database) as session:
                rec = session.run("RETURN 1 AS num").single()
                return rec is not None and rec["num"] == 1
        except Exception as exc:
            logger.error(f"Neo4j connectivity check failed: {exc}")
            return False

    def close(self) -> None:
        """Close the underlying *shared* driver.

        Only call this when the entire process is shutting down — other
        consumers sharing the same driver will lose their connection.
        """
        close_driver()

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> "Neo4jPool":
        return self

    def __exit__(self, *_exc: Any) -> None:
        pass  # don't close the shared driver automatically


def get_pool(database: Optional[str] = None) -> Neo4jPool:
    """Return a ``Neo4jPool`` backed by the shared driver."""
    return Neo4jPool(database=database)
