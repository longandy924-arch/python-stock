#!/bin/zsh

cd /Users/andylong/python-stock

PYTHON="./.venv/bin/python3"

echo "===== V52 次日结果自动更新 ====="

$PYTHON scripts/update_v52_nextday_result.py || true

$PYTHON scripts/analyze_v52_db_summary.py || true

echo "===== 更新完成 ====="
