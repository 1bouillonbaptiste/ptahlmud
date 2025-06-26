"""Implement fluctuations service.

It is responsible to collect requested fluctuations.
If the data is not in the db, it will fetch it from the remote data provider.
"""

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from multiprocessing import Pool
from typing import Callable

import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm

from ptahlmud.datastack.clients.remote_client import RemoteClient
from ptahlmud.datastack.fluctuations import Fluctuations
from ptahlmud.datastack.fluctuations_repository import FluctuationsRepository
from ptahlmud.types import Period


@dataclass
class DateRange:
    """Store a range of dates."""

    start_date: datetime
    end_date: datetime

    def split(self, delta: timedelta) -> list["DateRange"]:
        """Split the date range into smaller chunks.

        This is an optimization, assuming the database stores daily fluctuations data.
        The date range can be split in daily chunks so that each chunk can be exactly divided by the period.
        """
        minutes_in_day = 60 * 24
        period_total_minutes = int(delta.total_seconds()) // 60
        days_per_chunk: int = math.lcm(minutes_in_day, period_total_minutes) // minutes_in_day

        chunk_size: timedelta = timedelta(days=days_per_chunk)
        chunks: list[DateRange] = []
        current_start = self.start_date
        while current_start < self.end_date:
            current_end = min(current_start + chunk_size, self.end_date)
            chunks.append(DateRange(start_date=current_start, end_date=current_end))
            current_start = current_end
        return chunks


class FluctuationsConfig(BaseModel):
    """Configure fluctuations.

    Attributes:
        coin: the base coin of the fluctuations (e.g. 'BTC' or 'ETH')
        currency: the currency of the fluctuations (e.g. 'USD') could be another coin
        from_date: earliest open date to retrieve data
        to_date: latest close date to retrieve data
        timeframe: the time duration of each data item (e.g. '15m' or `1h`)
    """

    coin: str
    currency: str
    from_date: datetime
    to_date: datetime
    timeframe: str


class FluctuationsService:
    """Define the fluctuations service."""

    def __init__(self, repository: FluctuationsRepository, client: RemoteClient | None = None):
        self._repository = repository
        self._client = client

    def request(self, config: FluctuationsConfig) -> Fluctuations:
        """Load fluctuations from the database."""
        date_ranges = DateRange(start_date=config.from_date, end_date=config.to_date).split(
            delta=Period(timeframe=config.timeframe).to_timedelta()
        )
        configurations = [
            config.model_copy(update={"from_date": chunk.start_date, "to_date": chunk.end_date})
            for chunk in date_ranges
        ]

        nb_processes = max((os.cpu_count() or 1) * 3 // 4, 1)
        with Pool(processes=nb_processes) as pool:
            results = list(
                tqdm(
                    pool.imap(self._query_fluctuations, configurations),
                    total=len(configurations),
                    desc="Loading fluctuations data",
                )
            )
        all_fluctuations: list[Fluctuations] = [result for result in results if result is not None]
        return _merge_fluctuations(all_fluctuations)

    def _query_fluctuations(self, config: FluctuationsConfig) -> Fluctuations:
        """Query the repository for a single chunk of data."""
        chunk_fluctuations = self._repository.query(
            coin=config.coin,
            currency=config.currency,
            from_date=config.from_date,
            to_date=config.to_date,
        )
        chunk_fluctuations = _convert_fluctuations_to_period(chunk_fluctuations, period=Period(config.timeframe))
        return chunk_fluctuations

    def fetch(self, config: FluctuationsConfig) -> None:
        """Fetch missing fluctuations data from the remote data provider."""
        if self._client is None:
            raise RuntimeError("Client is required to fetch fluctuations data.")
        incomplete_dates = self._repository.find_incomplete_dates(
            coin=config.coin,
            currency=config.currency,
            from_date=config.from_date,
            to_date=config.to_date,
        )
        for date in tqdm(incomplete_dates, desc="Downloading fluctuations data"):
            fluctuations = self._client.fetch_historical_data(
                symbol=config.coin + config.currency,
                start_date=date,
                end_date=date + timedelta(days=1),
                timeframe="1m",
            )
            self._repository.save(fluctuations, coin=config.coin, currency=config.currency)


class CustomOperation(BaseModel):
    """Define a custom operation on a `pandas.series`."""

    column: str
    function: Callable[[pd.Series], int | float]


def _build_aggregation_function(custom_ops: list[CustomOperation]) -> Callable[[pd.DataFrame], pd.Series]:
    def custom_agg(group: pd.DataFrame) -> pd.Series:
        if len(group) == 0:
            return pd.Series()

        high_max_idx = group["high"].idxmax()
        low_min_idx = group["low"].idxmin()

        return pd.Series(
            {
                "open_time": group["open_time"].iloc[0],
                "high_time": group["close_time"][high_max_idx],
                "low_time": group["close_time"][low_min_idx],
                "close_time": group["close_time"].iloc[-1],
                "open": group["open"].iloc[0],
                "high": group["high"].max(),
                "low": group["low"].min(),
                "close": group["close"].iloc[-1],
            }
            | {operation.column: operation.function(group[operation.column]) for operation in custom_ops}
        )

    return custom_agg


def _convert_fluctuations_to_period(fluctuations: Fluctuations, period: Period) -> Fluctuations:
    """Convert fluctuations dataframe rows as a single one."""
    if fluctuations.size == 0:
        return fluctuations
    custom_aggregation = _build_aggregation_function(custom_ops=[])

    df = fluctuations.dataframe.copy()
    df_indexed = df.set_index(df["open_time"])
    df_converted = (
        df_indexed.resample(
            period.to_timedelta(),
            origin=fluctuations.earliest_open_time,
        )
        .agg(custom_aggregation)
        .dropna()
        .reset_index(drop=True)
    )

    # the first or last candle may be incomplete when the period is not a multiple of date range
    if (df_converted.iloc[-1]["open_time"] + period.to_timedelta()) != fluctuations.dataframe.iloc[-1]["close_time"]:
        df_converted = df_converted.iloc[:-1]
    return Fluctuations(dataframe=df_converted)


def _merge_fluctuations(fluctuations_chunks: list[Fluctuations]) -> Fluctuations:
    """Concatenate fluctuations dataframes."""
    if not fluctuations_chunks:
        return Fluctuations.empty()
    merged_fluctuations = (
        pd.concat([fluctuations.dataframe for fluctuations in fluctuations_chunks])
        .sort_values(by="open_time")
        .reset_index(drop=True)
    )
    return Fluctuations(dataframe=merged_fluctuations)
