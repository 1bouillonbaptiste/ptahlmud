# ptahlmud

A Python library for crafting and backtesting trading strategies. ptahlmud helps you design, test, and evaluate algorithmic trading strategies using historical market data.

## Features

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
from ptahlmud.types.signal import Signal, Side, Action
from ptahlmud.backtesting.backtest import RiskConfig, process_signals
from ptahlmud.backtesting.portfolio import Portfolio
from ptahlmud.entities.fluctuations import Fluctuations

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

# Initialize portfolio
initial_portfolio = Portfolio(
    starting_date=datetime(2023, 1, 1),
    starting_asset=0,
    starting_currency=10_000,
)

# Load market data (you'll need to implement this for your data source)
fluctuations: Fluctuations = load_your_market_data(...)

# Run the backtest
trades, final_portfolio = process_signals(
    signals=signals,
    risk_config=risk_config,
    fluctuations=fluctuations,
    initial_portfolio=initial_portfolio,
)

# Analyze results
print(f"Number of trades : {len(trades)}")
print(f"Final capital : {final_portfolio.get_available_capital_at(datetime(2023, 3, 1))}")
print(f"Win rate : {sum([1 for trade in trades if trade.total_profit > 0]) / len(trades)}")
```


## Advanced Usage

### Creating a Custom Strategy

You can define custom trading strategies by creating signals based on technical indicators or other market conditions:

```python
from ptahlmud.types.signal import Signal, Side, Action

def moving_average_strategy(market_data, fast_period=10, slow_period=30) -> list[Signal]:
    """Simple moving average crossover strategy."""
    signals: list[Signal] = []

    # Calculate moving averages (simplified example)
    fast_ma = calculate_moving_average(market_data, fast_period)
    slow_ma = calculate_moving_average(market_data, slow_period)

    # Generate signals on crossovers
    for i in range(1, len(market_data)):
        # fast ma crossed slow ma
        if fast_ma[i-1] < slow_ma[i-1] and fast_ma[i] > slow_ma[i]:
            signals.append(Signal(
                date=market_data[i].date,
                side=Side.LONG,
                action=Action.ENTER
            ))

        # slow ma crossed fast ma
        if fast_ma[i-1] > slow_ma[i-1] and fast_ma[i] < slow_ma[i]:
            signals.append(Signal(
                date=market_data[i].date,
                side=Side.LONG,
                action=Action.EXIT
            ))

    return signals
```

## Development Setup

Beforehand, you must install [pyenv](https://github.com/pyenv/pyenv) with python >= 3.11.

```bash
# Clone the repository
git clone https://github.com/yourusername/ptahlmud.git
cd ptahlmud
```

Install development dependencies
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
Contributions are welcome! Please feel free to open an issue or send me a dm.
You can also submit a Pull Request.
