from pathlib import Path
import pandas as pd
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
LIVE_DIR = BASE_DIR / "output" / "live"
REJECT_DIR = LIVE_DIR / "rejected"
REJECT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(LIVE_DIR.glob("v52_live_pick_*.csv"))

if not files:
    print("暂无V52实时候选文件")
    sys.exit(1)

latest = files[-1]
df = pd.read_csv(latest)

if len(df) == 0:
    print("候选文件为空")
    sys.exit(1)

row = df.iloc[0]

def pick_col(*names):
    for n in names:
        if n in df.columns:
            return n
    return None

code_col = pick_col("股票代码", "code", "ts_code")
name_col = pick_col("股票名称", "name")
score_col = pick_col("V52评分", "single_pick_score", "score")
gain4_col = pick_col("近4日涨幅", "gain_4d")
gain5_col = pick_col("近5日涨幅", "gain_5d")
turn_col = pick_col("实时换手率估算", "实时换手率", "turnover_pct")

def get_float(col):
    if not col:
        return None
    try:
        return float(row[col])
    except Exception:
        return None

code = str(row[code_col]).strip() if code_col else "UNKNOWN"
name = str(row[name_col]).strip() if name_col else "UNKNOWN"
pure_code = code.split(".")[0].strip()

score = get_float(score_col)
gain4 = get_float(gain4_col)
gain5 = get_float(gain5_col)
turnover = get_float(turn_col)

# 兼容涨幅单位：0.3049 转为 30.49；30.49 保持不变
if gain4 is not None and gain4 <= 2:
    gain4 = gain4 * 100

if gain5 is not None and gain5 <= 2:
    gain5 = gain5 * 100

reasons = []

# 允许创业板；排除科创板、北交所
if pure_code.startswith(("688", "689", "8", "4")):
    reasons.append(f"不可买板块：{code} 属于科创板或北交所")

if score is None or score < 0.74:
    reasons.append(f"V52评分不足：{score}")

if gain4 is None or gain4 < 16:
    reasons.append(f"近4日涨幅不足：{gain4}")

if gain5 is None or gain5 < 15:
    reasons.append(f"近5日涨幅不足：{gain5}")

if turnover is None or turnover > 1.0:
    reasons.append(f"实时换手率不符合V55口径：{turnover}")

if reasons:
    target = REJECT_DIR / latest.name
    latest.rename(target)

    print("V55可买版实时候选校验未通过")
    print("股票代码:", code)
    print("股票名称:", name)
    print("V52评分:", score)
    print("近4日涨幅:", gain4)
    print("近5日涨幅:", gain5)
    print("实时换手率:", turnover)
    print("拒绝原因:")
    for r in reasons:
        print("-", r)
    print("已移入:", target)
    sys.exit(1)

print("V55可买版实时候选校验通过")
print("股票代码:", code)
print("股票名称:", name)
print("V52评分:", score)
print("近4日涨幅:", gain4)
print("近5日涨幅:", gain5)
print("实时换手率:", turnover)
sys.exit(0)
