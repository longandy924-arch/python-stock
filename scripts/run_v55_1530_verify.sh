#!/bin/zsh
set -e

cd /Users/andylong/python-stock

PYTHON_BIN="/Users/andylong/python-stock/.venv/bin/python3"
LOG_DIR="/Users/andylong/python-stock/logs"
mkdir -p "$LOG_DIR"

NOW=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/v55_1530_verify_$NOW.log"

echo "===== V55/V56 15:30 次日验证开始：$(date) =====" | tee "$LOG_FILE"

echo "===== A股交易日判断 =====" | tee -a "$LOG_FILE"
set +e
"$PYTHON_BIN" scripts/is_a_share_trade_day.py 2>&1 | tee -a "$LOG_FILE"
TRADE_DAY_STATUS=${PIPESTATUS[1]}
set -e

if [ "$TRADE_DAY_STATUS" -ne 0 ]; then
    MSG="V55/V56次日验证未执行：今天不是A股交易日，或交易日历检查失败。运行时间：$(date)"
    echo "$MSG" | tee -a "$LOG_FILE"
    echo "$MSG" | "$PYTHON_BIN" scripts/send_qq_mail.py "V55/V56次日验证日报"
    echo "===== V55/V56 15:30 次日验证结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

echo "===== 更新次日验证结果 =====" | tee -a "$LOG_FILE"
"$PYTHON_BIN" scripts/update_v55_verify_result.py 2>&1 | tee -a "$LOG_FILE"

echo "===== 发送验证日报 =====" | tee -a "$LOG_FILE"
"$PYTHON_BIN" scripts/build_v55_verify_mail.py | "$PYTHON_BIN" scripts/send_qq_mail.py "V55/V56次日验证日报"

echo "===== V55/V56 15:30 次日验证结束：$(date) =====" | tee -a "$LOG_FILE"
