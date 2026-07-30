from pathlib import Path
from datetime import datetime
import os
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RECORD_FILE = BASE_DIR / "records" / "v55_selected_records.csv"

if not RECORD_FILE.exists():
    print("暂无V55/V56选股记录")
    raise SystemExit(0)

df = pd.read_csv(RECORD_FILE, dtype=str)

if df.empty:
    print("记录表为空")
    raise SystemExit(0)

today = datetime.now().strftime("%Y%m%d")

def get_tushare_pro():
    import tushare as ts

    token = os.environ.get("TUSHARE_TOKEN", "").strip()

    token_paths = [
        BASE_DIR / "config" / "tushare_token.txt",
        BASE_DIR / "config" / "token.txt",
        BASE_DIR / ".tushare_token",
    ]

    for p in token_paths:
        if not token and p.exists():
            token = p.read_text().strip()

    if not token:
        raise RuntimeError("未找到Tushare token，请检查环境变量或config/tushare_token.txt")

    ts.set_token(token)
    return ts.pro_api()

pro = get_tushare_pro()

updated = 0

for idx, row in df.iterrows():
    status = str(row.get("verify_status", ""))

    if status == "已验证":
        continue

    selection_date = str(row.get("selection_date", "")).strip()
    ts_code = str(row.get("ts_code", "")).strip()

    if not selection_date or not ts_code:
        continue

    if selection_date >= today:
        continue

    try:
        buy_price = float(row.get("price"))
    except Exception:
        print("买入价异常，跳过:", ts_code, row.get("price"))
        continue

    try:
        daily = pro.daily(
            ts_code=ts_code,
            start_date=selection_date,
            end_date=today
        )
    except Exception as e:
        print("Tushare获取失败:", ts_code, e)
        continue

    if daily is None or daily.empty:
        print("暂无行情:", ts_code)
        continue

    daily = daily.sort_values("trade_date")
    daily = daily[daily["trade_date"].astype(str) > selection_date]

    if daily.empty:
        print("尚无次日行情:", ts_code)
        continue

    next_row = daily.iloc[0]
    next_trade_date = str(next_row["trade_date"])
    next_high = float(next_row["high"])
    next_close = float(next_row["close"])

    next_high_return = (next_high / buy_price - 1) * 100
    next_close_return = (next_close / buy_price - 1) * 100
    success = "成功" if next_high_return >= 2.5 else "失败"

    df.loc[idx, "verify_status"] = "已验证"
    df.loc[idx, "verify_date"] = today
    df.loc[idx, "next_trade_date"] = next_trade_date
    df.loc[idx, "next_high"] = round(next_high, 3)
    df.loc[idx, "next_close"] = round(next_close, 3)
    df.loc[idx, "next_high_return"] = round(next_high_return, 4)
    df.loc[idx, "next_close_return"] = round(next_close_return, 4)
    df.loc[idx, "success"] = success

    updated += 1

df.to_csv(RECORD_FILE, index=False, encoding="utf-8-sig")

print("V55/V56次日验证完成")
print("本次更新数量:", updated)
print("记录文件:", RECORD_FILE)

if updated > 0:
    print()
    print("===== 本次验证结果 =====")
    show_cols = [
        "selection_date", "signal_level", "ts_code", "name", "price",
        "next_trade_date", "next_high", "next_high_return",
        "next_close", "next_close_return", "success"
    ]
    show_cols = [c for c in show_cols if c in df.columns]
    today_verified = df[df["verify_date"].astype(str) == today]
    print(today_verified[show_cols].to_string(index=False))
