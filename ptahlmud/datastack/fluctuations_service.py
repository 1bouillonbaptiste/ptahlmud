"""Implement fluctuations service.

It is responsible to collect requested fluctuations.
If the data is not in the db, it will fetch it from the remote data provider.
"""

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import Callable

import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm

from ptahlmud.datastack.clients.remote_client import RemoteClient
from ptahlmud.datastack.custom_operations import CustomOperation, get_operation, register_operation
from ptahlmud.datastack.fluctuations import Fluctuations
from ptahlmud.datastack.fluctuations_repository import FilesMapper, FluctuationsRepository
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


class FluctuationsSpecs(BaseModel):
    """Specifications that fully define `Fluctuations`.

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

    def __init__(self, savedir: Path, client: RemoteClient | None = None) -> None:
        self._repository = FluctuationsRepository(FilesMapper(root=savedir))
        self._client = client

    def request(
        self, config: FluctuationsSpecs, custom_operations: list[CustomOperation] | None = None
    ) -> Fluctuations:
        """Build fluctuations from specifications."""
        date_ranges = DateRange(start_date=config.from_date, end_date=config.to_date).split(
            delta=Period(timeframe=config.timeframe).to_timedelta()
        )
        configurations = [
            config.model_copy(update={"from_date": chunk.start_date, "to_date": chunk.end_date})
            for chunk in date_ranges
        ]

        # multiprocessing cannot handle functions as arguments, we register operations and access them later
        operations_names = _register_operations(custom_operations or [])

        _process_function = partial(
            _process_config_chunk, repository=self._repository, operations_names=operations_names
        )

        max_workers = max((os.cpu_count() or 1) * 3 // 4, 1)
        with Pool(processes=max_workers) as pool:
            all_fluctuations = list(
                tqdm(
                    pool.imap(_process_function, configurations),
                    total=len(configurations),
                    desc="Loading fluctuations data",
                )
            )

        return _merge_fluctuations(all_fluctuations)

    def fetch(self, config: FluctuationsSpecs) -> None:
        """Update missing fluctuations from the database using the remote data provider."""
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


def _register_operations(custom_operations: list[CustomOperation]) -> list[str]:
    """Register custom operations in the global scope."""
    operations_names = []
    for custom_operation in custom_operations:
        register_operation(custom_operation)
        operations_names.append(custom_operation.column)
    return operations_names


def _get_operations(operations_names: list[str]) -> list[CustomOperation]:
    """Access custom operations from the global scope."""
    return [get_operation(name) for name in operations_names]


def _process_config_chunk(
    specs: FluctuationsSpecs, repository: FluctuationsRepository, operations_names: list[str]
) -> Fluctuations:
    """Process a single configuration chunk - used for multiprocessing."""
    chunk_fluctuations = repository.query(
        coin=specs.coin,
        currency=specs.currency,
        from_date=specs.from_date,
        to_date=specs.to_date,
    )
    # access the operations now
    custom_operations = _get_operations(operations_names)

    chunk_fluctuations = _convert_fluctuations_to_period(
        chunk_fluctuations, period=Period(specs.timeframe), custom_operations=custom_operations
    )
    return chunk_fluctuations


def _build_aggregation_function(custom_operations: list[CustomOperation]) -> Callable[[pd.DataFrame], pd.Series]:
    """Create a pandas aggregation function with custom operations."""

    def custom_agg(group: pd.DataFrame) -> pd.Series:
        """Define how to aggregate a dataframe to a series."""
        if len(group) == 0:
            return pd.Series(
                {
                    "open_time": None,
                    "high_time": None,
                    "low_time": None,
                    "close_time": None,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                }
                | {operation.column: None for operation in custom_operations}
            )

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
            | {operation.column: operation.function(group[operation.requires]) for operation in custom_operations}
        )

    return custom_agg


def _convert_fluctuations_to_period(
    fluctuations: Fluctuations, period: Period, custom_operations: list[CustomOperation]
) -> Fluctuations:
    """Merge fluctuations so that each row has a period of `period`."""
    if fluctuations.size == 0:
        return fluctuations
    custom_aggregation = _build_aggregation_function(custom_operations)
    df = fluctuations.dataframe.copy()

    # Pandas raise a warning when the datetime is not enforced
    df["open_time"] = pd.to_datetime(df["open_time"])
    df_indexed = df.set_index("open_time", drop=False)
    df_converted = (
        df_indexed.resample(
            period.to_timedelta(),
            origin=fluctuations.earliest_open_time,
        )
        .apply(lambda group: custom_aggregation(group))
        .dropna()
        .reset_index(drop=True)
    )

    # the last candle may be incomplete when the period is not a multiple of date range
    if (df_converted.iloc[-1]["open_time"] + period.to_timedelta()) != fluctuations.dataframe.iloc[-1]["close_time"]:
        df_converted = df_converted.iloc[:-1]
    return Fluctuations(dataframe=df_converted)


def _merge_fluctuations(fluctuations_chunks: list[Fluctuations]) -> Fluctuations:
    """Concatenate fluctuations to a single dataframe."""
    if not fluctuations_chunks:
        return Fluctuations.empty()
    merged_fluctuations = (
        pd.concat([fluctuations.dataframe for fluctuations in fluctuations_chunks])
        .sort_values(by="open_time")
        .reset_index(drop=True)
    )
    return Fluctuations(dataframe=merged_fluctuations)
