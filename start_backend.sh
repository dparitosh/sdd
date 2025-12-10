#!/bin/bash
# Start Flask backend with correct Python path

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):$PYTHONPATH"
python src/web/app.py
