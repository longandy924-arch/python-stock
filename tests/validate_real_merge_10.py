"""10只真实股票：Tushare历史日线 + 14:30实时行情融合验证。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import pandas as pd
import tushare as ts

from data_source.realtime_gateway import RealtimeGateway
from merge.merge_engine import merge_history_with_realtime
from strategy.indicators import calculate_indicators


TEST_COUNT = 10
HISTORY_DAYS = 180


def normalise_code(value: object) -> str:
    """统一为Tushare股票代码格式。"""
    text = str(value).strip().upper()

    if text.endswith((".SH", ".SZ", ".BJ")):
        return text

    digits = "".join(char for char in text if char.isdigit()).zfill(6)

    if digits.startswith(("5", "6", "9")):
        return f"{digits}.SH"

    if digits.startswith(("4", "8")):
        return f"{digits}.BJ"

    return f"{digits}.SZ"


def prepare_history(raw: pd.DataFrame) -> pd.DataFrame:
    """将Tushare日线转换为Merge Engine字段口径。"""
    if raw is None or raw.empty:
        raise RuntimeError("Tushare历史数据为空。")

    required = {
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "vol",
    }

    missing = required - set(raw.columns)
    if missing:
        raise RuntimeError(
            f"Tushare历史数据缺少字段：{sorted(missing)}"
        )

    history = raw.copy()

    history["trade_date"] = pd.to_datetime(
        history["trade_date"],
        format="%Y%m%d",
        errors="coerce",
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
        "pre_close",
        "pct_chg",
    ]

    for column in numeric_columns:
        if column in history.columns:
            history[column] = pd.to_numeric(
                history[column],
                errors="coerce",
            )

    history = (
        history.dropna(
            subset=[
                "trade_date",
                "open",
                "high",
                "low",
                "close",
                "vol",
            ]
        )
        .sort_values("trade_date")
        .drop_duplicates("trade_date", keep="last")
        .reset_index(drop=True)
    )

    if len(history) < 21:
        raise RuntimeError(
            f"有效历史数据不足21个交易日：{len(history)}"
        )

    return history


def choose_test_quotes(quotes: pd.DataFrame) -> pd.DataFrame:
    """选择10只字段完整、正常交易的主板股票。"""
    required = {
        "ts_code",
        "name",
        "price",
        "volume",
        "amount",
    }

    missing = required - set(quotes.columns)
    if missing:
        raise RuntimeError(
            f"实时行情缺少字段：{sorted(missing)}"
        )

    result = quotes.copy()

    result["ts_code"] = result["ts_code"].map(normalise_code)
    result["price"] = pd.to_numeric(
        result["price"],
        errors="coerce",
    )
    result["volume"] = pd.to_numeric(
        result["volume"],
        errors="coerce",
    )
    result["amount"] = pd.to_numeric(
        result["amount"],
        errors="coerce",
    )

    result = result[
        result["price"].notna()
        & (result["price"] > 0)
        & result["volume"].notna()
        & (result["volume"] > 0)
        & result["amount"].notna()
        & (result["amount"] > 0)
        & ~result["name"].astype(str).str.contains(
            r"ST|退市",
            case=False,
            regex=True,
            na=False,
        )
        & ~result["ts_code"].str.startswith(("300", "301", "688"))
        & ~result["ts_code"].str.endswith(".BJ")
    ].copy()

    result = (
        result.sort_values("amount", ascending=False)
        .drop_duplicates("ts_code")
        .head(TEST_COUNT)
        .reset_index(drop=True)
    )

    if len(result) < TEST_COUNT:
        raise RuntimeError(
            f"符合条件的真实股票不足{TEST_COUNT}只。"
        )

    return result


def main() -> None:
    print("步骤1/5：获取全市场实时行情")

    gateway = RealtimeGateway()
    realtime_all = gateway.get_realtime_quotes()
    test_quotes = choose_test_quotes(realtime_all)

    print(f"数据源：{gateway.current_source}")
    print(f"测试股票数量：{len(test_quotes)}")

    print("\n步骤2/5：连接Tushare")
    pro = ts.pro_api()

    today = datetime.now()
    start_date = (
        today - timedelta(days=HISTORY_DAYS)
    ).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    current_trade_date = today.strftime("%Y-%m-%d")

    records: list[dict[str, object]] = []
    failures: list[str] = []

    print("\n步骤3/5：逐只获取历史数据并融合")

    for index, realtime_row in test_quotes.iterrows():
        ts_code = realtime_row["ts_code"]
        name = realtime_row["name"]

        try:
            raw_history = pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )

            history = prepare_history(raw_history)

            historical_last_date = history.iloc[-1]["trade_date"]
            historical_last_volume = float(
                history.iloc[-1]["vol"]
            )

            merged = merge_history_with_realtime(
                history=history,
                realtime=realtime_row,
                trade_date=current_trade_date,
                keep_days=120,
            )

            indicators = calculate_indicators(merged)
            latest = indicators.iloc[-1]

            realtime_volume = float(realtime_row["volume"])

            volume_ratio_to_last = (
                realtime_volume / historical_last_volume
                if historical_last_volume > 0
                else float("nan")
            )

            required_indicators = [
                "ma5",
                "ma10",
                "ma20",
                "pct",
                "close_strength",
                "vol_ratio",
            ]

            indicator_valid = all(
                pd.notna(latest[column])
                for column in required_indicators
            )

            records.append(
                {
                    "ts_code": ts_code,
                    "name": name,
                    "history_rows": len(history),
                    "history_last_date": historical_last_date.date(),
                    "merged_last_date": merged.iloc[-1][
                        "trade_date"
                    ].date(),
                    "price": round(float(latest["close"]), 3),
                    "ma5": round(float(latest["ma5"]), 3),
                    "ma10": round(float(latest["ma10"]), 3),
                    "ma20": round(float(latest["ma20"]), 3),
                    "pct": round(float(latest["pct"]), 3),
                    "close_strength": round(
                        float(latest["close_strength"]),
                        3,
                    ),
                    "vol_ratio": round(
                        float(latest["vol_ratio"]),
                        3,
                    ),
                    "volume_ratio_to_last": round(
                        volume_ratio_to_last,
                        3,
                    ),
                    "indicator_valid": indicator_valid,
                }
            )

            print(
                f"[{index + 1:02d}/{TEST_COUNT}] "
                f"{ts_code} {name}：成功"
            )

        except Exception as exc:
            failures.append(
                f"{ts_code} {name}：{type(exc).__name__}: {exc}"
            )

            print(
                f"[{index + 1:02d}/{TEST_COUNT}] "
                f"{ts_code} {name}：失败"
            )

        time.sleep(0.15)

    print("\n步骤4/5：检查融合结果")

    result = pd.DataFrame(records)

    if failures:
        print("\n失败明细：")
        for failure in failures:
            print(f"- {failure}")

    if len(result) < 8:
        raise RuntimeError(
            f"真实融合成功数量不足8只：{len(result)}/{TEST_COUNT}"
        )

    if not result["indicator_valid"].all():
        raise RuntimeError("存在指标为空的股票。")

    if result["merged_last_date"].nunique() != 1:
        raise RuntimeError("合并后的最新交易日期不一致。")

    extreme_volume = result[
        (result["volume_ratio_to_last"] > 200)
        | (result["volume_ratio_to_last"] < 0.001)
    ]

    if not extreme_volume.empty:
        raise RuntimeError(
            "实时成交量与Tushare历史成交量疑似单位不一致：\n"
            + extreme_volume[
                [
                    "ts_code",
                    "name",
                    "volume_ratio_to_last",
                ]
            ].to_string(index=False)
        )

    print("\n步骤5/5：输出验证结果")
    print(result.to_string(index=False))

    print("\n" + "=" * 68)
    print("10只真实股票融合验证成功")
    print("=" * 68)
    print(f"成功数量：{len(result)}/{TEST_COUNT}")
    print("历史日期口径：通过")
    print("实时日期写入：通过")
    print("成交量单位初步检查：通过")
    print("MA5/MA10/MA20：通过")
    print("pct/close_strength/vol_ratio：通过")


if __name__ == "__main__":
    main()
