import os
from pathlib import Path
import pandas as pd
import tushare as ts


def get_pro():
    token = os.getenv("TUSHARE_TOKEN")

    if not token:
        env = Path("config/tushare.env")
        if env.exists():
            token = env.read_text().strip().split("=")[1]

    if not token:
        raise RuntimeError("未找到Tushare token")

    ts.set_token(token)
    return ts.pro_api()


def main():
    pro = get_pro()

    df = None

    # daily_basic自动寻找最近可用交易日
    for d in pd.bdate_range(
        end=pd.Timestamp.today(),
        periods=10
    )[::-1]:

        trade_date = d.strftime("%Y%m%d")

        print(f"尝试daily_basic日期: {trade_date}")

        tmp = pro.daily_basic(
            trade_date=trade_date,
            fields="ts_code,total_mv,circ_mv"
        )

        if tmp is not None and len(tmp) > 0:
            df = tmp
            print(f"daily_basic使用日期: {trade_date}")
            break

    if df is None:
        raise RuntimeError("最近10个交易日没有daily_basic数据")

    output = Path("pipeline/data/stock_basic_mv.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"流通市值更新完成: {len(df)} 条")
    print(output)


if __name__ == "__main__":
    main()
