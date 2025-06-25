from datetime import datetime, timedelta

import pytest

from ptahlmud.datastack.clients.remote_client import RemoteClient
from ptahlmud.datastack.fluctuations import Fluctuations
from ptahlmud.datastack.fluctuations_repository import FilesMapper, FluctuationsRepository
from ptahlmud.datastack.fluctuations_service import FluctuationsConfig, FluctuationsService
from ptahlmud.datastack.testing.fluctuations import generate_fluctuations
from ptahlmud.types import Period


class MockedClient(RemoteClient):
    """Mock remote client."""

    def fetch_historical_data(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> Fluctuations:
        """Mock fetching."""
        return generate_fluctuations(
            from_date=start_date,
            to_date=end_date,
            period=Period(timeframe=timeframe),
        )


@pytest.fixture
def mocked_service(tmp_path):
    return FluctuationsService(
        client=MockedClient(), repository=FluctuationsRepository(database=FilesMapper(root=tmp_path))
    )


def test_service_request_is_empty(mocked_service):
    config = FluctuationsConfig.model_validate(
        {
            "coin": "FAKE",
            "currency": "NEWS",
            "from_date": datetime(2020, 1, 1),
            "to_date": datetime(2020, 1, 2),
            "timeframe": "1m",
        }
    )
    with pytest.raises(ValueError, match="No fluctuations found for 'FAKE/NEWS' from "):
        mocked_service.request(config)


def test_service_request_incomplete_data(mocked_service):
    config = FluctuationsConfig.model_validate(
        {
            "coin": "FAKE",
            "currency": "NEWS",
            "from_date": datetime(2020, 1, 1),
            "to_date": datetime(2020, 1, 2),
            "timeframe": "1m",
        }
    )
    dataframe = mocked_service._client.fetch_historical_data(
        symbol=config.coin + config.currency,
        start_date=config.from_date,
        end_date=config.from_date + timedelta(hours=12),
        timeframe=config.timeframe,
    )
    mocked_service._repository.save(dataframe, coin=config.coin, currency=config.currency)

    fluctuations = mocked_service.request(config)

    MINUTES_IN_HOUR = 60
    assert fluctuations.size == MINUTES_IN_HOUR * 12
    assert fluctuations.earliest_open_time == datetime(2020, 1, 1)
    assert fluctuations.latest_close_time == datetime(2020, 1, 1, hour=12)


def test_service_fetch_data(mocked_service):
    config = FluctuationsConfig.model_validate(
        {
            "coin": "FAKE",
            "currency": "NEWS",
            "from_date": datetime(2020, 1, 1),
            "to_date": datetime(2020, 1, 2),
            "timeframe": "1m",
        }
    )
    mocked_service.fetch(config)

    fluctuations = mocked_service.request(config)

    MINUTES_IN_DAY = 60 * 24
    assert fluctuations.size == MINUTES_IN_DAY
    assert fluctuations.earliest_open_time == datetime(2020, 1, 1)
    assert fluctuations.latest_close_time == datetime(2020, 1, 2)


def test_service_request_subset(mocked_service):
    config = FluctuationsConfig.model_validate(
        {
            "coin": "FAKE",
            "currency": "NEWS",
            "from_date": datetime(2020, 1, 1, hour=5),
            "to_date": datetime(2020, 1, 1, hour=7),
            "timeframe": "1m",
        }
    )
    mocked_service.fetch(config)

    fluctuations = mocked_service.request(config)

    MINUTES_IN_HOUR = 60
    assert fluctuations.size == MINUTES_IN_HOUR * 2
    assert fluctuations.earliest_open_time == datetime(2020, 1, 1, hour=5)
    assert fluctuations.latest_close_time == datetime(2020, 1, 1, hour=7)


def test_service_request_and_convert_fluctuations(mocked_service):
    config = FluctuationsConfig.model_validate(
        {
            "coin": "FAKE",
            "currency": "NEWS",
            "from_date": datetime(2020, 1, 1, hour=5),
            "to_date": datetime(2020, 1, 1, hour=7),
            "timeframe": "7m",
        }
    )
    mocked_service.fetch(config)

    fluctuations = mocked_service.request(config)

    MINUTES_IN_HOUR = 60
    MINUTES_IN_TIMEFRAME = 7
    assert fluctuations.size == MINUTES_IN_HOUR * 2 // MINUTES_IN_TIMEFRAME
    assert fluctuations.earliest_open_time == datetime(2020, 1, 1, hour=5)
    assert fluctuations.latest_close_time == datetime(
        2020, 1, 1, hour=6, minute=59
    )  # 7-minute candles are complete until 6:59

    for _, candle in fluctuations.dataframe.iterrows():
        assert (candle["close_time"] - candle["open_time"]) == timedelta(minutes=MINUTES_IN_TIMEFRAME)
