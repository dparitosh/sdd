#!/bin/bash
# Start FastAPI backend with correct Python path

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):$PYTHONPATH"
python -m uvicorn src.web.app_fastapi:app --host 0.0.0.0 --port 5000 --reload
