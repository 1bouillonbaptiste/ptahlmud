"""Implement fluctuations service.

It is responsible to collect requested fluctuations.
If the data is not in the db, it will fetch it from the remote data provider.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from multiprocessing import Pool

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


class FluctuationsConfig(BaseModel):
    """Configure fluctuations parameters.

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
    """Define fluctuations service."""

    def __init__(self, repository: FluctuationsRepository, client: RemoteClient | None = None):
        self._repository = repository
        self._client = client

    def request(self, config: FluctuationsConfig) -> Fluctuations:
        """Load fluctuations from the database."""
        # optimization, with '1m' timeframe we don't need to convert the data
        if config.timeframe == "1m":
            return self._repository.query(
                coin=config.coin,
                currency=config.currency,
                from_date=config.from_date,
                to_date=config.to_date,
            )

        date_ranges = _chunkify(
            start_date=config.from_date,
            end_date=config.to_date,
            chunk_size=Period(timeframe=config.timeframe).to_timedelta(),
        )
        process_func = partial(
            _process_chunk,
            repository=self._repository,
            coin=config.coin,
            currency=config.currency,
            timeframe=config.timeframe,
        )

        nb_processes = max((os.cpu_count() or 1) * 3 // 4, 1)
        with Pool(processes=nb_processes) as pool:
            # Use imap for progress tracking
            results = list(
                tqdm(pool.imap(process_func, date_ranges), total=len(date_ranges), desc="Loading fluctuations data")
            )
        all_fluctuations: list[Fluctuations] = [result for result in results if result is not None]
        return _merge_fluctuations(all_fluctuations)

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


def _chunkify(start_date: datetime, end_date: datetime, chunk_size: timedelta) -> list[DateRange]:
    """Split a time range into chunks of a given size."""
    chunks: list[DateRange] = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + chunk_size, end_date)
        chunks.append(DateRange(start_date=current_start, end_date=current_end))
        current_start = current_end
    return chunks


def _resume_fluctuations(fluctuations: Fluctuations) -> Fluctuations:
    """Resume fluctuations dataframe rows as a single one."""
    index_max = fluctuations.dataframe["high"].argmax()
    index_min = fluctuations.dataframe["low"].argmin()
    resumed_dataframe = pd.DataFrame(
        {
            "open_time": fluctuations.dataframe["open_time"].iloc[0],
            "high_time": fluctuations.dataframe["close_time"].iloc[index_max],
            "low_time": fluctuations.dataframe["close_time"].iloc[index_min],
            "close_time": fluctuations.dataframe["close_time"].iloc[-1],
            "open": fluctuations.dataframe["open"].iloc[0],
            "high": fluctuations.dataframe["high"].max(),
            "low": fluctuations.dataframe["low"].min(),
            "close": fluctuations.dataframe["close"].iloc[-1],
        },
        index=[0],
    )
    return Fluctuations(dataframe=resumed_dataframe)


def _merge_fluctuations(fluctuations_chunks: list[Fluctuations]) -> Fluctuations:
    """Concatenate fluctuations dataframes."""
    merged_fluctuations = (
        pd.concat([fluctuations.dataframe for fluctuations in fluctuations_chunks])
        .sort_values(by="open_time")
        .reset_index(drop=True)
    )
    return Fluctuations(dataframe=merged_fluctuations)


def _process_chunk(
    chunk: DateRange, repository: FluctuationsRepository, coin: str, currency: str, timeframe: str
) -> Fluctuations | None:
    """Process a single chunk of data."""
    chunk_fluctuations = repository.query(
        coin=coin,
        currency=currency,
        from_date=chunk.start_date,
        to_date=chunk.end_date,
    )
    if chunk_fluctuations.size == 0:
        return None

    chunk_fluctuations = _resume_fluctuations(chunk_fluctuations)
    if chunk_fluctuations.period == Period(timeframe):
        return chunk_fluctuations
    return None
