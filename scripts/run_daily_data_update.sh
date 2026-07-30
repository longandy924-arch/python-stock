#!/bin/zsh

cd /Users/andylong/python-stock

PYTHON="./.venv/bin/python3"

echo "===== 每日日线更新开始 ====="

$PYTHON scripts/update_daily_csv.py

$PYTHON scripts/update_stock_basic_mv.py

$PYTHON scripts/check_daily_data_health.py


echo "===== 数据更新完成 ====="
