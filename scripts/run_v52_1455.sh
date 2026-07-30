#!/bin/zsh
set -e

cd /Users/andylong/Desktop/python-stock

LOG_DIR="/Users/andylong/Desktop/python-stock/logs"
mkdir -p "$LOG_DIR"

NOW=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/v52_1455_$NOW.log"

echo "===== V52 14:55 自动运行开始：$(date) =====" | tee "$LOG_FILE"

python3 pipeline/run_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE"

if grep -q "今日唯一候选" "$LOG_FILE"; then
    PICK=$(grep -E "股票代码|股票名称|当前价格|当日涨幅|V52评分" "$LOG_FILE" | tr '\n' ' ')
    osascript -e "display notification \"$PICK\" with title \"V52 今日唯一候选\""
else
    echo "今日无符合条件的股票，不发送通知。" | tee -a "$LOG_FILE"
fi

echo "===== V52 14:55 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
