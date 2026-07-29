#!/bin/zsh

cd /Users/andylong/python-stock

PYTHON="./.venv/bin/python3"

echo "===== V52 20:00复盘开始 ====="

$PYTHON scripts/update_v52_market_result.py

$PYTHON scripts/generate_v52_report.py

if [ -f reports/v52_daily_report.txt ]; then
    cat reports/v52_daily_report.txt | $PYTHON scripts/send_qq_mail.py "V52每日复盘报告"
fi

echo "===== V52 20:00复盘结束 ====="

echo "===== V52.5 因子分析 ====="
./.venv/bin/python3 scripts/analyze_v52_factors.py || true

echo "===== V52.6 失败原因分析 ====="
./.venv/bin/python3 scripts/analyze_v52_failures.py || true

