"""
MBSEsmrl Dataloader — CLI entrypoint.

Usage:
    # Start as standalone server
    python -m src.dataloader.cli serve --port 5001

    # Quick pipeline run (no server needed)
    python -m src.dataloader.cli reload [--engine] [--clear]

    # Run migrations
    python -m src.dataloader.cli migrate

    # Graph inspection
    python -m src.dataloader.cli inspect
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Ensure backend is on path
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv()


def cmd_serve(args):
    """Start the dataloader FastAPI server."""
    import uvicorn
    logger.info(f"Starting MBSEsmrl Dataloader on port {args.port}...")
    uvicorn.run(
        "src.dataloader.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_reload(args):
    """Quick pipeline reload (no server needed)."""
    from src.dataloader.dependencies import (
        get_graph_store, get_pipeline, get_neo4j_connection,
        DEFAULT_XMI_PATHS, SEED_DIR,
    )

    # Find XMI file
    xmi_path = None
    for base in DEFAULT_XMI_PATHS:
        if base.exists():
            files = list(base.glob("*.xmi"))
            if files:
                xmi_path = str(files[0])
                break

    if not xmi_path:
        logger.error("No XMI file found. Place .xmi files in data/raw/ or smrlv12/data/domain_models/mossec/")
        sys.exit(1)

    if args.engine:
        logger.info("Using engine pipeline...")
        store = get_graph_store()
        pipeline = get_pipeline(store)
        sources = {"xmi": xmi_path}
        if SEED_DIR.exists():
            sources["oslc"] = str(SEED_DIR)
        results = pipeline.run(sources=sources, clear_first=args.clear)
        for r in results:
            status = "OK" if r.ok else f"ERRORS: {r.errors}"
            logger.info(f"  [{r.ingester_name}] nodes={r.nodes_created} rels={r.relationships_created} {status}")
        store.close()
    else:
        logger.info("Using legacy SemanticXMILoader...")
        from src.parsers.semantic_loader import SemanticXMILoader
        conn = get_neo4j_connection()
        try:
            if args.clear:
                logger.info("Clearing database...")
                conn.execute_query("MATCH (n) DETACH DELETE n")
            loader = SemanticXMILoader(conn, enable_versioning=True)
            loader.create_constraints_and_indexes()
            stats = loader.load_xmi_file(Path(xmi_path))
            logger.info(f"Loaded: {stats}")
        finally:
            conn.close()

    logger.info("Reload complete!")


def cmd_migrate(args):
    """Run pending schema migrations."""
    from src.dataloader.dependencies import get_neo4j_connection, MIGRATIONS_DIR
    from src.dataloader.routes.migrations import _discover_migrations, _get_applied_migrations, _run_migration_file

    conn = get_neo4j_connection()
    try:
        migrations = _discover_migrations()
        applied = _get_applied_migrations(conn)
        pending = [m for m in migrations if m["name"] not in applied]

        if not pending:
            logger.info("No pending migrations.")
            return

        logger.info(f"Found {len(pending)} pending migration(s):")
        for m in pending:
            logger.info(f"  - {m['name']}")
            if not args.dry_run:
                _run_migration_file(conn, m["file"], m["name"])
                logger.info(f"    ✓ Applied")

        if args.dry_run:
            logger.info("(Dry run — no changes made)")
    finally:
        conn.close()


def cmd_inspect(args):
    """Quick graph summary."""
    from src.dataloader.dependencies import get_neo4j_connection

    conn = get_neo4j_connection()
    try:
        nodes = conn.execute_query("MATCH (n) RETURN count(n) AS count")
        rels = conn.execute_query("MATCH ()-[r]->() RETURN count(r) AS count")

        logger.info(f"Nodes: {nodes[0]['count'] if nodes else 0}")
        logger.info(f"Relationships: {rels[0]['count'] if rels else 0}")

        labels = conn.execute_query("""
            MATCH (n) UNWIND labels(n) AS label
            RETURN label, count(*) AS count ORDER BY count DESC LIMIT 15
        """)
        logger.info("Top labels:")
        for r in labels:
            logger.info(f"  {r['label']}: {r['count']}")

        ap = conn.execute_query("""
            MATCH (n) WHERE n.ap_level IS NOT NULL
            RETURN n.ap_level AS level, count(n) AS count ORDER BY level
        """)
        if ap:
            logger.info("AP distribution:")
            for r in ap:
                logger.info(f"  {r['level']}: {r['count']}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        prog="dataloader",
        description="MBSEsmrl Dataloader — Batch Processing Utility",
    )
    sub = parser.add_subparsers(dest="command")

    # serve
    p_serve = sub.add_parser("serve", help="Start dataloader FastAPI server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=5001)
    p_serve.add_argument("--reload", action="store_true", help="Enable hot reload")

    # reload
    p_reload = sub.add_parser("reload", help="Quick pipeline reload")
    p_reload.add_argument("--engine", action="store_true", help="Use engine pipeline")
    p_reload.add_argument("--clear", action="store_true", help="Clear DB first")

    # migrate
    p_migrate = sub.add_parser("migrate", help="Run schema migrations")
    p_migrate.add_argument("--dry-run", action="store_true")

    # inspect
    sub.add_parser("inspect", help="Show graph summary")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "reload":
        cmd_reload(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "inspect":
        cmd_inspect(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
