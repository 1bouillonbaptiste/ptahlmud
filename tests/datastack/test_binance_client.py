from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest

from ptahlmud.datastack.clients.binance_client import BinanceClient


@dataclass
class BinanceCreds:
    """Store binance credentials."""

    secret: str | None
    key: str | None

    def exists(self):
        """Check if credentials are available."""
        return self.secret is not None and self.key is not None


def _build_credentials(filepath: Path) -> BinanceCreds:
    """Build credentials from a file containing secrets."""
    if not filepath.exists():
        return BinanceCreds(None, None)

    creds: dict[str, str] = {}
    for line in filepath.open("r"):
        name, value = line.replace("\n", "").split("=")
        if name in ["BINANCE_SECRET", "BINANCE_KEY"]:
            creds[name] = value
    return BinanceCreds(secret=creds.get("BINANCE_SECRET"), key=creds.get("BINANCE_KEY"))


@pytest.fixture
def binance_credentials(repository_root) -> BinanceCreds:
    """Return binance secrets if available."""
    return _build_credentials(repository_root / ".credentials")


def test_fetch_historical_data(binance_credentials: BinanceCreds):
    if not binance_credentials.exists():
        pytest.skip("Could not connect to Binance")
    else:
        client = BinanceClient(
            binance_secret=binance_credentials.secret,  # type: ignore
            binance_key=binance_credentials.key,  # type: ignore
        )
        fluctuations = client.fetch_historical_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date=datetime(2021, 1, 1),
            end_date=datetime(2021, 1, 2),
        )

        HOURS_IN_DAY = 24
        assert fluctuations.size == HOURS_IN_DAY
