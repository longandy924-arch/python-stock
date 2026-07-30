#!/bin/zsh
set -e

cd /Users/andylong/python-stock

PYTHON_BIN="/Users/andylong/python-stock/.venv/bin/python3"
LOG_DIR="/Users/andylong/python-stock/logs"
LIVE_DIR="/Users/andylong/python-stock/output/live"

mkdir -p "$LOG_DIR"
mkdir -p "$LIVE_DIR"

NOW=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/v52_1440_$NOW.log"

echo "===== V55 14:40 自动运行开始：$(date) =====" | tee "$LOG_FILE"
echo "使用Python: $PYTHON_BIN" | tee -a "$LOG_FILE"

echo "===== 清理旧候选文件，防止重复邮件 =====" | tee -a "$LOG_FILE"
find "$LIVE_DIR" -maxdepth 1 -name "v52_live_pick_*.csv" -type f -delete

echo "===== A股交易日判断 =====" | tee -a "$LOG_FILE"
set +e
"$PYTHON_BIN" scripts/is_a_share_trade_day.py 2>&1 | tee -a "$LOG_FILE"
TRADE_DAY_STATUS=${PIPESTATUS[1]}
set -e

if [ "$TRADE_DAY_STATUS" -ne 0 ]; then
    MSG="V55今日不执行选股：非A股交易日，或交易日历检查失败。运行时间：$(date)"
    echo "$MSG" | tee -a "$LOG_FILE"
    echo "$MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "今日无符合条件的股票"
    echo "===== V55 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "===== 运行V52实时选股 =====" | tee -a "$LOG_FILE"
"$PYTHON_BIN" pipeline/run_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE"

NEW_FILE=$(ls -t "$LIVE_DIR"/v52_live_pick_*.csv 2>/dev/null | head -1 || true)

if [ -z "$NEW_FILE" ]; then
    EMPTY_MSG="今日无符合条件的股票。

系统已正常运行14:40自动选股任务，但未筛选出符合V55可买版规则的股票。

建议：今日空仓，不强行买入。

运行时间：$(date)"
    echo "$EMPTY_MSG" | tee -a "$LOG_FILE"
    echo "$EMPTY_MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "今日无符合条件的股票"
    echo "===== V55 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "本次候选文件：$NEW_FILE" | tee -a "$LOG_FILE"

echo "===== V55可买版实时候选校验 =====" | tee -a "$LOG_FILE"
if ! "$PYTHON_BIN" scripts/validate_v55_buyable_live_pick.py 2>&1 | tee -a "$LOG_FILE"; then
    EMPTY_MSG="今日无符合条件的股票。

系统已正常运行14:40自动选股任务，但V52候选未通过V55可买版过滤。

V55可买版规则：
允许主板、创业板；
排除科创板、北交所；
V52评分>=0.74；
近4日涨幅>=16%；
近5日涨幅>=15%；
实时换手率<=1.0。

建议：今日空仓，不强行买入。

运行时间：$(date)"
    echo "$EMPTY_MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "今日无符合条件的股票"
    echo "V55过滤未通过，今日不推荐。" | tee -a "$LOG_FILE"
    echo "===== V55 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "===== 记录V55实盘候选 =====" | tee -a "$LOG_FILE"
("$PYTHON_BIN" scripts/record_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE") || true

echo "===== 发送V55选股邮件 =====" | tee -a "$LOG_FILE"
"$PYTHON_BIN" scripts/build_v52_mail_content.py | "$PYTHON_BIN" scripts/send_qq_mail.py "V55今日可买候选"

echo "===== V55 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
