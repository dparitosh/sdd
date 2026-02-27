#!/usr/bin/env python3
"""
Schema Migration Framework
============================================================================
Purpose: Versioned, idempotent schema migrations for the Neo4j Knowledge Graph.

Architecture:
    - Migrations are numbered Python files in backend/scripts/migrations/
    - Each migration defines an `up()` function (and optionally `down()`)
    - Applied migrations are tracked via :SchemaMigration nodes in Neo4j
    - Running the migrator applies only NEW (unapplied) migrations in order

Usage:
    python backend/scripts/schema_migrator.py                  # Apply all pending
    python backend/scripts/schema_migrator.py --status         # Show migration status
    python backend/scripts/schema_migrator.py --rollback       # Rollback last migration
    python backend/scripts/schema_migrator.py --create "desc"  # Create new migration file

Must be run from the project root (d:\\MBSEsmrl).
"""

import argparse
import importlib.util
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

# ---------------------------------------------------------------------------
# Path setup — must run from repo root or backend/
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent
MIGRATIONS_DIR = SCRIPT_DIR / "migrations"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_migration_module(filepath: Path):
    """Dynamically import a migration file as a Python module."""
    spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get_migration_files() -> list[Path]:
    """Return sorted list of migration files (NNN_description.py)."""
    if not MIGRATIONS_DIR.exists():
        return []
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.py"))
    return files


def _migration_version(filepath: Path) -> str:
    """Extract version string from filename, e.g. '001'."""
    return filepath.stem.split("_", 1)[0]


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def get_applied_versions(neo4j) -> set[str]:
    """Query Neo4j for versions already applied."""
    result = neo4j.execute_query(
        "MATCH (m:SchemaMigration) RETURN m.version AS version"
    )
    return {r["version"] for r in result} if result else set()


def apply_pending(neo4j, *, dry_run: bool = False):
    """Apply all pending migrations in order."""
    applied = get_applied_versions(neo4j)
    files = _get_migration_files()

    pending = [f for f in files if _migration_version(f) not in applied]

    if not pending:
        logger.info("All migrations are up to date — nothing to apply.")
        return 0

    logger.info(f"Found {len(pending)} pending migration(s)")

    for filepath in pending:
        version = _migration_version(filepath)
        description = filepath.stem.split("_", 1)[1].replace("_", " ")
        logger.info(f"  Applying {version}: {description}")

        if dry_run:
            logger.info(f"    [DRY RUN] Would execute {filepath.name}")
            continue

        mod = _load_migration_module(filepath)
        if not hasattr(mod, "up"):
            logger.error(f"    Migration {filepath.name} has no up() function — skipping")
            continue

        try:
            mod.up(neo4j)

            # Record successful application
            neo4j.execute_query(
                """
                MERGE (m:SchemaMigration {version: $version})
                SET m.description = $description,
                    m.applied_at = datetime($ts),
                    m.filename = $filename
                """,
                {
                    "version": version,
                    "description": description,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "filename": filepath.name,
                },
            )
            logger.success(f"    ✓ {version} applied")
        except Exception as exc:
            logger.error(f"    ✗ Migration {version} failed: {exc}")
            return 1

    return 0


def rollback_last(neo4j, *, dry_run: bool = False):
    """Rollback the most recently applied migration."""
    result = neo4j.execute_query(
        """
        MATCH (m:SchemaMigration)
        RETURN m.version AS version, m.filename AS filename, m.description AS description
        ORDER BY m.version DESC LIMIT 1
        """
    )

    if not result:
        logger.info("No migrations to rollback.")
        return 0

    last = result[0]
    version = last["version"]
    filename = last["filename"]
    description = last["description"]

    filepath = MIGRATIONS_DIR / filename
    if not filepath.exists():
        logger.error(f"Migration file not found: {filename}")
        return 1

    mod = _load_migration_module(filepath)
    if not hasattr(mod, "down"):
        logger.error(f"Migration {filename} has no down() function — cannot rollback")
        return 1

    logger.info(f"Rolling back {version}: {description}")

    if dry_run:
        logger.info(f"  [DRY RUN] Would rollback {filename}")
        return 0

    try:
        mod.down(neo4j)
        neo4j.execute_query(
            "MATCH (m:SchemaMigration {version: $version}) DELETE m",
            {"version": version},
        )
        logger.success(f"  ✓ {version} rolled back")
    except Exception as exc:
        logger.error(f"  ✗ Rollback failed: {exc}")
        return 1

    return 0


def show_status(neo4j):
    """Show applied and pending migrations."""
    applied = get_applied_versions(neo4j)
    files = _get_migration_files()

    logger.info("Schema Migration Status")
    logger.info("=" * 60)

    if not files:
        logger.info("No migration files found in backend/scripts/migrations/")
        return

    for filepath in files:
        version = _migration_version(filepath)
        description = filepath.stem.split("_", 1)[1].replace("_", " ")
        status = "✓ applied" if version in applied else "  pending"
        logger.info(f"  [{status}] {version}: {description}")

    pending_count = sum(1 for f in files if _migration_version(f) not in applied)
    logger.info(f"\n  {len(applied)} applied, {pending_count} pending")


def create_migration(description: str):
    """Create a new numbered migration file from template."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

    existing = _get_migration_files()
    if existing:
        last_num = int(_migration_version(existing[-1]))
        next_num = last_num + 1
    else:
        next_num = 1

    slug = description.lower().replace(" ", "_").replace("-", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    filename = f"{next_num:03d}_{slug}.py"
    filepath = MIGRATIONS_DIR / filename

    template = textwrap.dedent(f'''\
        """
        Migration {next_num:03d}: {description}
        Auto-generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}
        """


        def up(neo4j):
            """Apply this migration."""
            # Example:
            # neo4j.execute_query("CREATE INDEX ... IF NOT EXISTS ...")
            pass


        def down(neo4j):
            """Rollback this migration (optional but recommended)."""
            pass
    ''')

    filepath.write_text(template, encoding="utf-8")
    logger.success(f"Created migration: {filepath.relative_to(PROJECT_ROOT)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Schema migration manager")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--rollback", action="store_true", help="Rollback last migration")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--create", metavar="DESC", help="Create a new migration file")
    args = parser.parse_args()

    # --create doesn't need Neo4j
    if args.create:
        create_migration(args.create)
        return 0

    # All other commands need Neo4j
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")

    from src.web.services import get_neo4j_service

    neo4j = get_neo4j_service()

    if args.status:
        show_status(neo4j)
        return 0

    if args.rollback:
        return rollback_last(neo4j, dry_run=args.dry_run)

    return apply_pending(neo4j, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
