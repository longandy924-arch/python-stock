#!/bin/bash

export PROJECT_ROOT="/Users/andylong/python-stock"
export PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"

export DATA_DIR="$PROJECT_ROOT/data"
export DAILY_DIR="$PROJECT_ROOT/data/daily"
export OUTPUT_DIR="$PROJECT_ROOT/output"
export LOG_DIR="$PROJECT_ROOT/logs"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: Python环境不存在: $PYTHON_BIN"
    exit 1
fi
