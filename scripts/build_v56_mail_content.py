from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
LIVE_DIR = BASE_DIR / "output" / "live"
REJECT_DIR = LIVE_DIR / "rejected"

files = list(LIVE_DIR.glob("v52_live_pick_*.csv"))
files += list(REJECT_DIR.glob("v52_live_pick_*.csv"))

files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)

if not files:
    print("今日无符合条件的股票。")
    print()
    print("系统已正常运行14:40自动选股任务，但未筛选出符合V55/V56规则的股票。")
    print()
    print("建议：今日空仓，不强行买入。")
    print()
    print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    raise SystemExit

df = pd.read_csv(files[0])

if df.empty:
    print("今日无符合条件的股票。")
    print()
    print("系统已正常运行14:40自动选股任务，但候选文件为空。")
    print()
    print("建议：今日空仓，不强行买入。")
    print()
    print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    raise SystemExit

row = df.iloc[0]

def val(*names, default=""):
    for n in names:
        if n in row.index:
            v = row.get(n)
            if pd.notna(v):
                return v
    return default

def fmt_float(x, digits=2):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)

def fmt_amount_yi(x):
    try:
        return f"{float(x) / 100000000:.2f} 亿"
    except Exception:
        return ""

def fmt_circ_mv_yi(x):
    try:
        return f"{float(x) / 10000:.2f} 亿"
    except Exception:
        return str(x)

code = val("ts_code", "股票代码", "code")
name = val("name", "股票名称")
price = val("price", "当前价格")
pct_chg = val("pct_chg", "当日涨幅")
gain4 = val("gain_4d", "近4日涨幅")
gain5 = val("gain_5d", "近5日涨幅")
amount = val("amount", "成交额")
circ_mv = val("circ_mv", "流通市值")
turnover = val("turnover_pct", "实时换手率估算", "实时换手率")
score = val("single_pick_score", "V52评分")

print("【V56今日B类次级候选】")
print()
print("说明：该股票未达到V55A级标准，但符合V56次级机会规则。")
print("执行建议：轻仓/观察，不按V55正常仓位处理。")
print()
print(f"股票：{name}")
print(f"代码：{code}")
print()
print(f"当前价：{fmt_float(price, 2)}")
print(f"当日涨幅：{fmt_float(pct_chg, 2)}%")
print(f"近4日涨幅：{fmt_float(gain4, 2)}%")
print(f"近5日涨幅：{fmt_float(gain5, 2)}%")
print()
print(f"流通市值：{fmt_circ_mv_yi(circ_mv)}")
print(f"实时成交额：{fmt_amount_yi(amount)}")
print(f"实时换手率估算：{fmt_float(turnover, 2)}%")
print(f"V52评分：{fmt_float(score, 4)}")
print()
print("V56规则：")
print("1. 允许主板、创业板")
print("2. 排除科创板、北交所")
print("3. V52评分 >= 0.70")
print("4. 近4日涨幅 >= 12%")
print("5. 近5日涨幅 >= 10%")
print("6. 实时换手率估算 <= 1.2%")
print()
print("回测参考：177笔，169胜8负，胜率95.48%，最大连续失败2。")
print()
print("执行：14:40附近观察，轻仓或仅记录")
print("纪律：次日无论涨跌坚决卖出")
print()
print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
