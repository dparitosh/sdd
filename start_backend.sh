#!/bin/bash
# Start Flask backend with correct Python path

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
python src/web/app.py
