#!/bin/bash
source config/env.sh


cd "$PROJECT_ROOT"

if [ -f "/Users/andylong/python-stock/config/tushare.env" ]; then
    source "/Users/andylong/python-stock/config/tushare.env"
fi


PYTHON="$PYTHON_BIN"

echo "===== 每日日线更新开始 ====="

$PYTHON scripts/update_daily_csv.py

$PYTHON scripts/update_stock_basic_mv.py

$PYTHON scripts/check_daily_data_health.py


echo "===== 数据更新完成 ====="
