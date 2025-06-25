"""Backtesting module.

The backtest is a simulation of the market. We calculate the trade that would have occurred given entry signals.
"""

from ptahlmud.backtesting.backtest import process_signals
from ptahlmud.backtesting.models.candle import Candle
from ptahlmud.backtesting.portfolio import Portfolio
from ptahlmud.backtesting.position import Trade

__all__ = ["Candle", "Portfolio", "Trade", "process_signals"]
