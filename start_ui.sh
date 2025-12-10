#!/bin/bash

# Kill any existing Flask processes
pkill -f "python.*web/app.py" 2>/dev/null

# Set up environment
cd /workspaces/mbse-neo4j-graph-rep
export PYTHONPATH=/workspaces/mbse-neo4j-graph-rep

echo "================================="=
echo "🚀 Starting MBSE Knowledge Graph UI"
echo "=================================="
echo ""
echo "Starting Flask server..."

# Start Flask server
python src/web/app.py

