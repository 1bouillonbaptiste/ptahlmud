"""Define the interface that every adapter must implement."""

from datetime import datetime
from typing import Protocol

from ptahlmud.datastack.fluctuations import Fluctuations


class RemoteClient(Protocol):
    """Interface for data providers."""

    def fetch_historical_data(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> Fluctuations:
        """Interface to download data from remote sources."""
        ...
