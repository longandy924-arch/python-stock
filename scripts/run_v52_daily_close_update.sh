#!/bin/bash
source config/env.sh


cd "$PROJECT_ROOT"

PYTHON="$PYTHON_BIN"

echo "===== V52 次日结果自动更新 ====="

$PYTHON scripts/update_v52_nextday_result.py || true

$PYTHON scripts/analyze_v52_db_summary.py || true

echo "===== 更新完成 ====="
