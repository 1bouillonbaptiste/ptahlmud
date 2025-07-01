from ptahlmud.core import Fluctuations

# ptahlmud

Python library for crafting and backtesting trading strategies.
Ptahlmud helps you design, test, and evaluate algorithmic trading strategies using historical market data.

## Features

This project is still under construction and features may be added or reworked.

- **Signal-based trading**: Define entry and exit points with customizable signals
- **Portfolio simulation**: Track your strategy's performance over time
- **Risk management**: Configure position sizing, take-profit, and stop-loss parameters
- **Backtesting engine**: Test strategies against historical market data

## Installation

```bash
pip install ptahlmud
```

## Quick Start

Here's a simple example of defining trading signals and running a backtest:

```python
from datetime import datetime
from pathlib import Path

from ptahlmud.backtesting.models import Signal, Side, Action
from ptahlmud.backtesting.backtest import RiskConfig, process_signals
from ptahlmud.datastack import FluctuationsService, BinanceClient, FluctuationsSpecs

client = BinanceClient(binance_secret="", binance_key="")
service = FluctuationsService(client, savedir=Path("/data/fluctuations_data"))

specifications = FluctuationsSpecs(
    coin="BTC", currency="USDT",
    from_date=datetime(2023, 1, 1),
    to_date=datetime(2023, 2, 1),
)

# Fetch and load the historical market data
service.fetch(specifications)
fluctuations = service.request(specifications)

# Define trading signals
signals = [
    Signal(date=datetime(2023, 1, 1), side=Side.LONG, action=Action.ENTER),
    Signal(date=datetime(2023, 1, 15), side=Side.LONG, action=Action.EXIT),
    Signal(date=datetime(2023, 2, 1), side=Side.SHORT, action=Action.ENTER),
    Signal(date=datetime(2023, 2, 15), side=Side.SHORT, action=Action.EXIT),
]

# Configure risk management
risk_config = RiskConfig(
    size=0.1,  # Use 10% of available capital per trade
    take_profit=0.05,  # Take profit at 5% price increase
    stop_loss=0.03,  # Cut losses at 3% price decrease
)

# Run the backtest
trades = process_signals(
    signals=signals,
    risk_config=risk_config,
    fluctuations=fluctuations,
)

# Analyze results
print(f"Number of trades : {len(trades)}")
print(f"Total profit : {sum([trade.total_profit for trade in trades])}")
print(f"Win rate : {sum([1 for trade in trades if trade.total_profit > 0]) / len(trades)}")
```


## Advanced Usage

### Creating a Custom Strategy

You can define custom trading strategies by creating signals based on technical indicators or other market conditions:

```python
from ptahlmud.backtesting.models.signal import Signal, Side, Action


def moving_average_strategy(fluctuations: Fluctuations, fast_period: int, slow_period: int) -> list[Signal]:
    """Moving average crossover strategy."""
    # Calculate moving averages (simplified example)
    fast_ma = fluctuations.dataframe["close"].rolling(fast_period).mean()
    slow_ma = fluctuations.dataframe["close"].rolling(slow_period).mean()

    ma_crossover = (fast_ma < slow_ma) & (fast_ma.shift(1) > slow_ma.shift(1))
    crossover_df = fluctuations.dataframe[ma_crossover]

    signals: list[Signal] = []
    for _, row in crossover_df.iterrows():
        signals.append(Signal(
            date=row["close_time"],
            action=Action.ENTER,
            side=Side.LONG
        ))

    return signals


signals = moving_average_strategy(fluctuations, fast_period=10, slow_period=30)
trades = process_signals(
    signals=signals,
    risk_config=risk_config,
    fluctuations=fluctuations,
)
```

## Development

It is recommended to work in a virtual environment, you can install [pyenv](https://github.com/pyenv/pyenv) with python >= 3.11.
```bash
pyenv install 3.12.5
pyenv virtualenv 3.12.5 ptahlmud
pyenv activate ptahlmud
```

```bash
# Clone the repository
git clone https://github.com/yourusername/ptahlmud.git
cd ptahlmud
```

Setup environment
```bash
make setup
```

Run tests
```bash
make test
```

Run code quality checks
```bash
make check
```

## Contributing

Contributions are welcome!
You can open an issue, submit a pull-request or simply chat with me.
I'm always pleased to discuss design, performance or technical stuff.
