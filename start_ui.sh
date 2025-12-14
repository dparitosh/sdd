#!/bin/bash

# Kill any existing frontend processes
pkill -f "vite" 2>/dev/null

# Set up environment
cd /workspaces/mbse-neo4j-graph-rep

echo "=================================="
echo "🚀 Starting MBSE Knowledge Graph UI"
echo "=================================="
echo ""
echo "Starting React frontend with Vite..."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install --legacy-peer-deps
fi

# Start Vite dev server
npm run dev

