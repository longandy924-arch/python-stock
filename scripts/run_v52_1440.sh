#!/bin/zsh
set -e

cd /Users/andylong/python-stock

PYTHON_BIN="/Users/andylong/python-stock/.venv/bin/python3"

LOG_DIR="/Users/andylong/python-stock/logs"
mkdir -p "$LOG_DIR"

NOW=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/v52_1440_$NOW.log"

echo "===== V52 14:40 自动运行开始：$(date) =====" | tee "$LOG_FILE"
echo "使用Python: $PYTHON_BIN" | tee -a "$LOG_FILE"

echo "===== A股交易日判断 =====" | tee -a "$LOG_FILE"
set +e
"$PYTHON_BIN" scripts/is_a_share_trade_day.py 2>&1 | tee -a "$LOG_FILE"
TRADE_DAY_STATUS=${PIPESTATUS[0]}
set -e

if [ "$TRADE_DAY_STATUS" -ne 0 ]; then
    MSG="V52今日不执行选股：非A股交易日，或交易日历检查失败。运行时间：$(date)"
    echo "$MSG" | tee -a "$LOG_FILE"
    echo "$MSG" | python3 scripts/send_qq_mail.py "V52今日不选股提醒"
    echo "===== V52 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

"$PYTHON_BIN" pipeline/run_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE"

if grep -q "今日唯一候选" "$LOG_FILE"; then
    PICK=$(grep -E "股票代码|股票名称|当前价格|当日涨幅|近4日涨幅|近5日涨幅|流通市值|实时换手率估算|V52评分" "$LOG_FILE")

    SHORT_PICK=$(echo "$PICK" | grep -E "股票代码|股票名称|当前价格|当日涨幅|V52评分" | tr '\n' ' ')

    osascript -e "display notification \"$SHORT_PICK\" with title \"V52 今日唯一候选\"" || true

    
echo "===== V52因子匹配强制校验 =====" | tee -a "$LOG_FILE"
if ! ./.venv/bin/python3 scripts/validate_v52_factor_match.py 2>&1 | tee -a "$LOG_FILE"; then
    EMPTY_MSG="V52今日无符合条件候选。\n\n原因：最终候选触发过热过滤器，已自动剔除。\n\n当前规则：不排除创业板；但排除4日/5日涨幅过高、换手率过高、高涨幅叠加高换手的候选。\n\n建议：今日空仓，不强行买入。\n\n运行时间：$(date)"
    echo "$EMPTY_MSG" | ./.venv/bin/python3 scripts/send_qq_mail.py "V52今日空仓提醒"
    echo "过热候选已剔除，今日不推荐。" | tee -a "$LOG_FILE"
    echo "===== V52 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
    exit 0
fi

(./.venv/bin/python3 scripts/record_v52_live_pick.py 2>&1 | tee -a "$LOG_FILE") || true

./.venv/bin/python3 scripts/build_v52_mail_content.py | ./.venv/bin/python3 scripts/send_qq_mail.py "V52每日选股"
else
    EMPTY_MSG="V52今日无符合条件候选，建议空仓。运行时间：$(date)"
    echo "$EMPTY_MSG" | tee -a "$LOG_FILE"

    echo "$EMPTY_MSG" | ./.venv/bin/python3 scripts/send_qq_mail.py "V52今日空仓提醒"
fi

echo "===== V52 14:40 自动运行结束：$(date) =====" | tee -a "$LOG_FILE"
