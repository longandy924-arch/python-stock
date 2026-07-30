from pathlib import Path
import pandas as pd
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
LIVE_DIR = BASE_DIR / "output" / "live"

REJECT_DIR = LIVE_DIR / "rejected"

files = list(LIVE_DIR.glob("v52_live_pick_*.csv"))
files += list(REJECT_DIR.glob("v52_live_pick_*.csv"))

files = sorted(
    files,
    key=lambda x: x.stat().st_mtime,
    reverse=True
)

if not files:
    print("暂无实时候选文件")
    sys.exit(1)

latest = files[0]
df = pd.read_csv(latest)

if df.empty:
    print("候选文件为空")
    sys.exit(1)

row = df.iloc[0]

def pick_col(*names):
    for n in names:
        if n in df.columns:
            return n
    return None

def get_float(*names):
    col = pick_col(*names)
    if not col:
        return None
    try:
        return float(row[col])
    except Exception:
        return None

def get_str(*names):
    col = pick_col(*names)
    if not col:
        return ""
    return str(row[col]).strip()

code = get_str("ts_code", "股票代码", "code")
name = get_str("name", "股票名称")
pure_code = code.split(".")[0]

score = get_float("single_pick_score", "V52评分", "score")
gain4 = get_float("gain_4d", "近4日涨幅")
gain5 = get_float("gain_5d", "近5日涨幅")
turnover = get_float("turnover_pct", "实时换手率估算", "实时换手率")

# 兼容小数涨幅
if gain4 is not None and gain4 <= 2:
    gain4 *= 100
if gain5 is not None and gain5 <= 2:
    gain5 *= 100

reasons = []

# 可买性：允许主板、创业板；排除科创板、北交所
if pure_code.startswith(("688", "689", "8", "4")):
    reasons.append(f"不可买板块：{code}")

# V56次级规则
if score is None or score < 0.70:
    reasons.append(f"V52评分不足：{score}")

if gain4 is None or gain4 < 12:
    reasons.append(f"近4日涨幅不足：{gain4}")

if gain5 is None or gain5 < 10:
    reasons.append(f"近5日涨幅不足：{gain5}")

if turnover is None or turnover > 1.2:
    reasons.append(f"实时换手率估算过高：{turnover}")

print("===== V56实时校验 =====")
print("股票代码:", code)
print("股票名称:", name)
print("V52评分:", score)
print("近4日涨幅:", gain4)
print("近5日涨幅:", gain5)
print("实时换手率估算:", turnover)

if reasons:
    print("V56校验未通过")
    print("拒绝原因:")
    for r in reasons:
        print("-", r)
    sys.exit(1)

print("V56校验通过：B类次级候选")
sys.exit(0)
