#!/bin/zsh
set -e

cd /Users/andylong/Desktop/python-stock

PYTHON_BIN="/Users/andylong/Desktop/python-stock/.venv/bin/python3"

LOG_DIR="/Users/andylong/Desktop/python-stock/logs"
mkdir -p "$LOG_DIR"

NOW=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/v52_1440_$NOW.log"

echo "===== V52 14:40 自动运行开始：$(date) =====" | tee "$LOG_FILE"
echo "使用Python: $PYTHON_BIN" | tee -a "$LOG_FILE"

"$PYTHON_BIN" pipeline/run_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE"

if grep -q "今日唯一候选" "$LOG_FILE"; then
    PICK=$(grep -E "股票代码|股票名称|当前价格|当日涨幅|近4日涨幅|近5日涨幅|流通市值|实时换手率估算|V52评分" "$LOG_FILE")

    SHORT_PICK=$(echo "$PICK" | grep -E "股票代码|股票名称|当前价格|当日涨幅|V52评分" | tr '\n' ' ')

    osascript -e "display notification \"$SHORT_PICK\" with title \"V52 今日唯一候选\"" || true

    echo "$PICK" | python3 scripts/send_qq_mail.py "V52今日唯一候选"
else
    EMPTY_MSG="V52今日无符合条件候选，建议空仓。运行时间：$(date)"
    echo "$EMPTY_MSG" | tee -a "$LOG_FILE"

    echo "$EMPTY_MSG" | python3 scripts/send_qq_mail.py "V52今日空仓提醒"
fi

echo "===== V52 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
