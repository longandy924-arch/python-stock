#!/bin/zsh
set -e

cd /Users/andylong/python-stock

PYTHON_BIN="/Users/andylong/python-stock/.venv/bin/python3"
LOG_DIR="/Users/andylong/python-stock/logs"
LIVE_DIR="/Users/andylong/python-stock/output/live"

mkdir -p "$LOG_DIR"
mkdir -p "$LIVE_DIR"
mkdir -p "$LIVE_DIR/rejected"

NOW=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/v52_1440_$NOW.log"

echo "===== V55/V56 14:40 自动运行开始：$(date) =====" | tee "$LOG_FILE"
echo "使用Python: $PYTHON_BIN" | tee -a "$LOG_FILE"

echo "===== 清理旧候选文件，防止重复邮件 =====" | tee -a "$LOG_FILE"
find "$LIVE_DIR" -maxdepth 1 -name "v52_live_pick_*.csv" -type f -delete
find "$LIVE_DIR/rejected" -maxdepth 1 -name "v52_live_pick_*.csv" -type f -delete

echo "===== A股交易日判断 =====" | tee -a "$LOG_FILE"
set +e
"$PYTHON_BIN" scripts/is_a_share_trade_day.py 2>&1 | tee -a "$LOG_FILE"
TRADE_DAY_STATUS=${PIPESTATUS[1]}
set -e

if [ "$TRADE_DAY_STATUS" -ne 0 ]; then
    MSG="今日无符合条件的股票。

系统已正常运行14:40自动选股任务，但今天不是A股交易日，或交易日历检查失败。

运行时间：$(date)"
    echo "$MSG" | tee -a "$LOG_FILE"
    echo "$MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "今日无符合条件的股票"
    echo "===== V55/V56 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "===== 运行V52候选生成器 =====" | tee -a "$LOG_FILE"
"$PYTHON_BIN" pipeline/run_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE"

NEW_FILE=$(ls -t "$LIVE_DIR"/v52_live_pick_*.csv 2>/dev/null | head -1 || true)

if [ -z "$NEW_FILE" ]; then
    MSG="今日无符合条件的股票。

系统已正常运行14:40自动选股任务，但V52候选生成器未生成候选文件。

建议：今日空仓，不强行买入。

运行时间：$(date)"
    echo "$MSG" | tee -a "$LOG_FILE"
    echo "$MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "今日无符合条件的股票"
    echo "===== V55/V56 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "本次候选文件：$NEW_FILE" | tee -a "$LOG_FILE"

echo "===== V55 A类高胜率校验 =====" | tee -a "$LOG_FILE"
set +e
V55_OUTPUT=$("$PYTHON_BIN" scripts/validate_v55_buyable_live_pick.py 2>&1)
V55_STATUS=$?
set -e
echo "$V55_OUTPUT" | tee -a "$LOG_FILE"

if [ "$V55_STATUS" -eq 0 ]; then
    echo "===== V55通过，发送A级候选邮件 =====" | tee -a "$LOG_FILE"
    ("$PYTHON_BIN" scripts/record_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE") || true
    "$PYTHON_BIN" scripts/build_v52_mail_content.py | "$PYTHON_BIN" scripts/send_qq_mail.py "V55今日A类可买候选"
    echo "===== V55/V56 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "===== V55未通过，继续检测V56 B类候选 =====" | tee -a "$LOG_FILE"
set +e
V56_OUTPUT=$("$PYTHON_BIN" scripts/validate_v56_live_pick.py 2>&1)
V56_STATUS=$?
set -e
echo "$V56_OUTPUT" | tee -a "$LOG_FILE"

if [ "$V56_STATUS" -eq 0 ]; then
    echo "===== V56通过，发送B类次级候选邮件 =====" | tee -a "$LOG_FILE"
    "$PYTHON_BIN" scripts/build_v56_mail_content.py | "$PYTHON_BIN" scripts/send_qq_mail.py "V56今日B类次级候选"
    echo "===== V55/V56 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

MSG="今日无符合条件的股票。

系统已正常运行14:40自动选股任务，但候选股票未通过V55A级和V56B级规则。

建议：今日空仓，不强行买入。

运行时间：$(date)"
echo "$MSG" | tee -a "$LOG_FILE"
echo "$MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "今日无符合条件的股票"

echo "===== V55/V56 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
