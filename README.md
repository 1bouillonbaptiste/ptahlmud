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

from ptahlmud.backtesting.backtest import RiskConfig, process_signals
from ptahlmud.entities.fluctuations import Fluctuations
from ptahlmud.types.signal import Signal, Side, Action

# Define trading signals
signals = [
    Signal(date=datetime(2023, 1, 1), side=Side.LONG, action=Action.ENTER),
    Signal(date=datetime(2023, 1, 15), side=Side.LONG, action=Action.EXIT),
    Signal(date=datetime(2023, 2, 1), side=Side.SHORT, action=Action.ENTER),
    Signal(date=datetime(2023, 2, 15), side=Side.SHORT, action=Action.EXIT),
]

# Configure risk management
risk_config = RiskConfig(
    size=0.1,          # Use 10% of available capital per trade
    take_profit=0.05,  # Take profit at 5% price increase
    stop_loss=0.03,    # Cut losses at 3% price decrease
)

# Load market data (you'll need to implement this for your data source)
fluctuations: Fluctuations = load_your_market_data(...)

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
from ptahlmud.types.signal import Signal, Side, Action

def moving_average_strategy(fluctuations, fast_period: int, slow_period: int) -> list[Signal]:
    """Simple moving average crossover strategy."""
    signals: list[Signal] = []

    # Calculate moving averages (simplified example)
    fast_ma = calculate_moving_average(fluctuations, fast_period)
    slow_ma = calculate_moving_average(fluctuations, slow_period)

    # Generate signals on crossovers
    for index, candle in enumerate(fluctuations.candles):
        # fast ma crossed above slow ma
        if fast_ma[index-1] < slow_ma[index-1] and fast_ma[index] > slow_ma[index]:
            signals.append(Signal(
                date=candle.close_time,
                side=Side.LONG,
                action=Action.ENTER
            ))

        # slow ma crossed bellow slow ma
        if fast_ma[index-1] > slow_ma[index-1] and fast_ma[index] < slow_ma[index]:
            signals.append(Signal(
                date=candle.close_time,
                side=Side.LONG,
                action=Action.EXIT
            ))

    return signals

signals = moving_average_strategy(market_date, fast_period=10, slow_period=30)
trades = process_signals(
    signals=signals,
    fluctuations=market_date,
    risk_config=risk_config,
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
