"""Realtime Gateway V1 tests."""

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_source.providers import RealtimeDataProvider
from data_source.realtime_gateway import (
    REQUIRED_COLUMNS,
    LocalCacheRealtimeProvider,
    RealtimeGateway,
)


def sample_quotes() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "name": "平安银行",
                "price": 11.17,
                "pct_chg": 0.54,
                "volume": 10000,
                "amount": 111700,
                "bid1": 11.16,
                "ask1": 11.17,
                "bid1_volume": 200,
                "ask1_volume": 300,
                "update_time": "2026-07-28 13:45:00",
            }
        ]
    )


class FakeProvider(RealtimeDataProvider):
    def __init__(
        self,
        provider_name,
        available=True,
        quotes=None,
        error=None,
    ):
        self.provider_name = provider_name
        self.available = available
        self.quotes = quotes
        self.error = error

    def is_available(self) -> bool:
        if isinstance(self.available, Exception):
            raise self.available
        return self.available

    def get_quotes(self) -> pd.DataFrame:
        if self.error is not None:
            raise self.error
        return self.quotes if self.quotes is not None else pd.DataFrame()


class RealtimeGatewayTest(unittest.TestCase):
    def test_provider_switches_to_next_successful_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = RealtimeGateway(
                providers=[
                    FakeProvider("eastmoney", available=False),
                    FakeProvider("tencent", error=RuntimeError("boom")),
                    FakeProvider("akshare", quotes=sample_quotes()),
                ],
                cache_path=Path(temp_dir) / "realtime_quotes.csv",
                log_path=Path(temp_dir) / "realtime.log",
            )

            quotes = gateway.get_realtime_quotes()

            self.assertEqual(gateway.current_source, "akshare")
            self.assertTrue(gateway.switched)
            self.assertFalse(quotes.empty)
            self.assertEqual(list(quotes.columns), REQUIRED_COLUMNS)
            self.assertIn("tencent get_quotes failed", (Path(temp_dir) / "realtime.log").read_text())

    def test_returns_consistent_nonempty_dataframe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = RealtimeGateway(
                providers=[FakeProvider("eastmoney", quotes=sample_quotes())],
                cache_path=Path(temp_dir) / "realtime_quotes.csv",
                log_path=Path(temp_dir) / "realtime.log",
            )

            quotes = gateway.get_realtime_quotes()

            self.assertFalse(quotes.empty)
            self.assertEqual(list(quotes.columns), REQUIRED_COLUMNS)
            self.assertEqual(gateway.current_source, "eastmoney")
            self.assertGreaterEqual(gateway.response_time_ms, 0)
            self.assertEqual(gateway.stock_count, 1)

    def test_local_cache_is_last_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "realtime_quotes.csv"
            sample_quotes().to_csv(cache_path, index=False, encoding="utf-8-sig")
            cache_provider = LocalCacheRealtimeProvider(cache_path)
            gateway = RealtimeGateway(
                providers=[
                    FakeProvider("eastmoney", error=RuntimeError("down")),
                    FakeProvider("tencent", available=False),
                    FakeProvider("akshare", available=False),
                    cache_provider,
                ],
                cache_path=cache_path,
                log_path=Path(temp_dir) / "realtime.log",
            )

            quotes = gateway.get_realtime_quotes()

            self.assertEqual(gateway.current_source, "local_cache")
            self.assertTrue(gateway.switched)
            self.assertFalse(quotes.empty)
            self.assertEqual(list(quotes.columns), REQUIRED_COLUMNS)


if __name__ == "__main__":
    unittest.main()
