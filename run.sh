#!/bin/bash
# Convenience script to run the application with proper PYTHONPATH

export PYTHONPATH="/workspaces/mbse-neo4j-graph-rep/src:$PYTHONPATH"
cd /workspaces/mbse-neo4j-graph-rep

case "$1" in
  "test")
    python src/cli/main.py test-connection
    ;;
  "parse")
    python src/cli/main.py parse --input "$2"
    ;;
  "build")
    python src/cli/main.py build-graph --input "$2"
    ;;
  "clear")
    python src/cli/main.py clear-graph
    ;;
  "main")
    python src/main.py
    ;;
  *)
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  test              - Test Neo4j connection"
    echo "  parse <file>      - Parse XMI file"
    echo "  build <file>      - Build graph from XMI file"
    echo "  clear             - Clear all graph data"
    echo "  main              - Run main application"
    ;;
esac
