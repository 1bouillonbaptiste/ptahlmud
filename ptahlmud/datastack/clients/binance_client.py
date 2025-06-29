"""Binance API adapter."""

from datetime import datetime, timedelta

import pandas as pd
from binance.client import Client

from ptahlmud.core.fluctuations import Fluctuations
from ptahlmud.datastack.clients.remote_client import RemoteClient
from ptahlmud.types import Period


class BinanceClient(RemoteClient):
    """Main interface between binance and athena."""

    def __init__(self, binance_secret: str, binance_key: str):
        self._client = Client(binance_key, binance_secret)

    def fetch_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Fluctuations:
        """Fetch historical data from binance.

        Args:
            symbol: pair symbol (e.g. 'BTCUSDT')
            timeframe: periodicity of the data to fetch (e.g. '1h' or '30m')
            start_date: date from which to start fetching data
            end_date: date until which to fetch data

        """
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)
        historical_data: list[tuple[float | int, ...]] = self._client.get_historical_klines(
            symbol=symbol, interval=timeframe, start_str=start_timestamp, end_str=end_timestamp
        )

        dataframe = _format_bars(historical_data, period=Period(timeframe=timeframe), end_date=end_date)
        return Fluctuations(dataframe=dataframe)


def _format_bars(bars: list[tuple[float | int, ...]], period: Period, end_date: datetime) -> pd.DataFrame:
    """Format binance bars to a pandas DataFrame.

    Binance provides bars containing the following (ordered) information:
        Open time: bar starting time in milliseconds
        Open: bar price at the opening
        High: bar highest price
        Low: bar lowest price
        Close: bar price at the closing
        Volume: coin total traded volume
        Close time: bar closing time in milliseconds
        Quote asset volume: currency total traded amount (can also be another coin e.g. with BTCETH symbol)
        Number of trades: total number of trades for this bar
        Taker buy base asset volume,
        Taker buy quote asset volume,
        Ignore this field: binance specific field
    see https://python-binance.readthedocs.io/en/latest/_modules/binance/client.html#Client.get_historical_klines
    """
    candles: list[pd.DataFrame] = []
    for bar in bars:
        open_time = datetime.fromtimestamp(bar[0] / 1000.0)
        close_time = datetime.fromtimestamp(bar[6] / 1000.0)

        candle_still_open = close_time - open_time < (period.to_timedelta() - timedelta(seconds=1))
        if candle_still_open:
            continue

        # When the clock time is changed in a country (e.g. France switch from winter to summer)
        # see https://docs.python.org/3/library/datetime.html#datetime.datetime.fold
        if open_time.fold == 1:
            continue

        new_candle = pd.DataFrame(
            {
                "open_time": open_time,
                "close_time": open_time + period.to_timedelta(),
                "open": float(bar[1]),
                "high": float(bar[2]),
                "low": float(bar[3]),
                "close": float(bar[4]),
                "volume": float(bar[5]),
                "quote_volume": float(bar[7]),
                "nb_trades": int(bar[8]),
                "taker_volume": float(bar[9]),
                "taker_quote_volume": float(bar[10]),
            },
            index=[0],
        )
        if new_candle["close_time"].iloc[0] <= end_date:
            candles.append(new_candle)

    return (
        pd.concat(candles)
        .reset_index(drop=True)
        .astype(
            {
                "open_time": "datetime64[ns]",
                "close_time": "datetime64[ns]",
            }
        )
    )
