#!/bin/bash

# Convenience wrapper to start the FastAPI backend from repo root.

cd "$(dirname "$0")/.."
exec ./backend/start_backend.sh
