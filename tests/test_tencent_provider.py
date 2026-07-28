"""腾讯实时行情 Provider 真实连接测试。"""

import time

from data_source.providers.tencent_provider import (
    REQUIRED_COLUMNS,
    TencentRealtimeProvider,
)


if __name__ == "__main__":
    provider = TencentRealtimeProvider(
        ts_codes=[
            "000001.SZ",
            "600000.SH",
            "300750.SZ",
        ],
    )

    started = time.perf_counter()
    quotes = provider.get_quotes()
    elapsed_ms = round(
        (time.perf_counter() - started) * 1000,
        2,
    )

    assert provider.is_available()
    assert not quotes.empty
    assert set(REQUIRED_COLUMNS).issubset(quotes.columns)
    assert quotes["ts_code"].is_unique
    assert "000001.SZ" in quotes["ts_code"].tolist()

    print("腾讯Provider真实连接成功")
    print(f"腾讯响应时间(ms)：{elapsed_ms}")
    print(f"返回股票数量：{len(quotes)}")
    print(quotes.to_string(index=False))
