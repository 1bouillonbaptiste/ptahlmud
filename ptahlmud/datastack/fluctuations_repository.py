"""Repository to read and write fluctuations data from/to the database..

The repository is responsible for retrieving data from the database.
It can also fetch missing data from a remote data provider.
"""

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from ptahlmud.datastack.fluctuations import Fluctuations

logger = logging.getLogger(__name__)


class FilesMapper:
    """Interface to localize fluctuation files in the database.

    Args:
        root: directory where to find the fluctuation files
    """

    def __init__(self, root: Path):
        self._root = root

    def data_directory(self, coin: str, currency: str) -> Path:
        """Directory to find a specific pair."""
        return self._root / f"{coin}_{currency}"

    def find_file(self, coin: str, currency: str, date: datetime | date) -> Path:
        """Find the file containing market data for a specific date."""
        date_str = date.strftime("%Y-%m-%d")
        return self.data_directory(coin=coin, currency=currency) / f"fluctuations_{date_str}.csv"


class FluctuationsRepository:
    """Interface to access fluctuations stored in the database."""

    def __init__(self, database: FilesMapper):
        self._database = database

    def query(self, coin: str, currency: str, from_date: datetime, to_date: datetime) -> Fluctuations:
        """Request fluctuations from the database.

        Missing fluctuations are fetched from the remote data provider.

        Args:
            coin: coin symbol to fetch (e.g. 'BTC' or 'ETH')
            currency: currency symbol (e.g. 'USD')
            from_date: earliest open date to retrieve data
            to_date: latest close date to retrieve data
        """
        requested_fluctuations: list[Fluctuations] = []
        for day_nb in range((to_date - from_date).days + 1):
            fluctuations = self._request_daily_fluctuations(
                coin=coin, currency=currency, date=from_date.date() + timedelta(days=day_nb)
            )
            if fluctuations is not None:
                requested_fluctuations.append(fluctuations)

        if not requested_fluctuations:
            raise ValueError(f"No fluctuations found for '{coin}/{currency}' from '{from_date}' to '{to_date}'")

        merged_fluctuations = merge_fluctuations(requested_fluctuations)
        return merged_fluctuations.subset(from_date=from_date, to_date=to_date)

    def _request_daily_fluctuations(self, coin: str, currency: str, date: date) -> Fluctuations | None:
        """Request fluctuations for a specific day."""
        file = self._database.find_file(coin=coin, currency=currency, date=date)
        fluctuations = read_fluctuations(file) if file.is_file() else None
        return fluctuations

    def find_incomplete_dates(self, coin: str, currency: str, from_date: datetime, to_date: datetime) -> list[datetime]:
        """Find dates where fluctuations are missing or does not cover the full day."""
        MINUTES_IN_DAY = 60 * 24
        incomplete_dates: list[datetime] = []
        for day_nb in range((to_date - from_date).days + 1):
            day_date = from_date.date() + timedelta(days=day_nb)
            fluctuations = self._request_daily_fluctuations(coin=coin, currency=currency, date=day_date)
            if fluctuations is None or fluctuations.size < MINUTES_IN_DAY:
                incomplete_dates.append(datetime(day_date.year, day_date.month, day_date.day))
        return incomplete_dates

    def save(self, fluctuations: Fluctuations, coin: str, currency: str) -> None:
        """Write fluctuations to the database."""
        if fluctuations.timeframe != "1m":
            raise ValueError(
                f"Fluctuations repository can only save '1m' timeframes fluctuations, found '{fluctuations.timeframe}'."
            )

        MINUTES_IN_DAY = 60 * 24
        if fluctuations.size > MINUTES_IN_DAY:
            raise ValueError("Fluctuations repository can only save fluctuations for a single day.")

        date = fluctuations.earliest_open_time.date()
        filepath = self._database.find_file(coin=coin, currency=currency, date=date)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        write_fluctuations(fluctuations, filepath)


def read_fluctuations(filepath: Path) -> Fluctuations:
    """Read fluctuations from a CSV file."""
    dataframe = pd.read_csv(filepath, sep=";")
    return Fluctuations(dataframe)


def write_fluctuations(fluctuations: Fluctuations, filepath: Path) -> None:
    """Write fluctuations to a CSV file."""
    fluctuations.dataframe.to_csv(filepath, sep=";", index=False)


def merge_fluctuations(all_fluctuations: list[Fluctuations]) -> Fluctuations:
    """Merge multiple fluctuations into a single one."""
    merged_dataframes = pd.concat([fluctuations.dataframe for fluctuations in all_fluctuations]).reset_index(drop=True)
    return Fluctuations(merged_dataframes)
