"""Command-line interface for MBSE Neo4j Knowledge Graph"""

from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger

from graph.connection import Neo4jConnection
from parsers.apoc_loader import APOCXMILoader
from utils.config import Config
from utils.logger import setup_logger


@click.group()
def cli():
    """MBSE Neo4j Knowledge Graph CLI"""
    load_dotenv()
    setup_logger()


@cli.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input XMI file path")
def load(input):
    """Load XMI file directly into Neo4j using APOC"""
    if not input:
        click.echo("Please provide an input file with --input")
        return

    config = Config()

    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        if not conn.verify_connection():
            click.echo("Failed to connect to Neo4j")
            return

        loader = APOCXMILoader(conn)
        stats = loader.load_xmi_file(Path(input))
        click.echo(f"Loaded successfully: {stats}")


@cli.command()
def test_connection():
    """Test Neo4j connection"""
    config = Config()

    click.echo(f"Testing connection to {config.neo4j_uri}...")

    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        if conn.verify_connection():
            click.echo("✓ Connection successful!")
        else:
            click.echo("✗ Connection failed!")


@cli.command()
def clear_graph():
    """Clear all data from the graph"""
    if not click.confirm("This will delete all nodes and relationships. Continue?"):
        return

    config = Config()
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        builder = GraphBuilder(conn)
        builder.clear_graph()
        click.echo("Graph cleared!")


if __name__ == "__main__":
    cli()


@cli.command()
def clear_graph():
    """Clear all data from the graph"""
    if not click.confirm("This will delete all nodes and relationships. Continue?"):
        return

    config = Config()
    with Neo4jConnection(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as conn:
        loader = APOCXMILoader(conn)
        loader.clear_graph()
        click.echo("Graph cleared!")
