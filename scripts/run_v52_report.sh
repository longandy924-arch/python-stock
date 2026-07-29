#!/bin/zsh

cd /Users/andylong/python-stock

PYTHON="./.venv/bin/python3"

echo "===== V52 20:00复盘开始 ====="

$PYTHON scripts/update_v52_market_result.py || true

echo "===== V52次日行情回填 ====="
$PYTHON scripts/update_v52_nextday_result.py || true


$PYTHON scripts/analyze_v52_factors.py || true

$PYTHON scripts/analyze_v52_failures.py || true

$PYTHON scripts/generate_v52_report.py || true

echo "===== V52.9 实盘监控面板 ====="
$PYTHON scripts/generate_v52_dashboard.py || true


if [ -f reports/v52_daily_report.txt ]; then
    cat reports/v52_daily_report.txt | $PYTHON scripts/send_qq_mail.py "V52每日复盘报告"
fi

echo "===== V52 20:00复盘结束 ====="

echo "===== V52.7 排名分析 ====="
./.venv/bin/python3 scripts/analyze_v52_rank.py || true





echo "===== V53交易评价 ====="
$PYTHON scripts/update_v53_daily_eval.py || true

echo "===== V53策略监控 ====="
$PYTHON scripts/v53_daily_monitor.py || true

echo "===== V52.8 权重分析 ====="
./.venv/bin/python3 scripts/analyze_v52_weights.py || true

