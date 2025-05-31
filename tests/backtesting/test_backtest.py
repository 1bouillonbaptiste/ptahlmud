from datetime import datetime

from pytest_cases import parametrize_with_cases

from ptahlmud.backtesting.backtest import MatchedSignal, _match_signals
from ptahlmud.types.signal import Action, Side, Signal


class MatchedSignalsCases:
    """Generate cases for `_match_signals()`.

    Each case returns:
    - signals to be matched
    - expected matches
    """

    def case_empty(self):
        return [], []

    def case_enter_long(self):
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        return [
            long_entry,
        ], [MatchedSignal(entry=long_entry, exit=None)]

    def case_exit_long(self):
        """No entry, so no action is performed."""
        long_exit = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.EXIT)
        return [
            long_exit,
        ], []

    def case_full_long(self):
        """Entry is associated to exit."""
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        long_exit = Signal(date=datetime(2020, 1, 2), side=Side.LONG, action=Action.EXIT)
        return [long_entry, long_exit], [MatchedSignal(entry=long_entry, exit=long_exit)]

    def case_long_exit_before_entry(self):
        long_entry = Signal(date=datetime(2020, 1, 3), side=Side.LONG, action=Action.ENTER)
        long_exit = Signal(date=datetime(2020, 1, 2), side=Side.LONG, action=Action.EXIT)
        return [long_entry, long_exit], [MatchedSignal(entry=long_entry, exit=None)]

    def case_different_side(self):
        """Don't match entry to exit if sides differ."""
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        short_exit = Signal(date=datetime(2020, 1, 2), side=Side.SHORT, action=Action.EXIT)
        return [long_entry, short_exit], [MatchedSignal(entry=long_entry, exit=None)]

    def case_mixed_side(self):
        long_entry = Signal(date=datetime(2020, 1, 1), side=Side.LONG, action=Action.ENTER)
        short_entry = Signal(date=datetime(2020, 1, 2), side=Side.SHORT, action=Action.ENTER)
        long_exit = Signal(date=datetime(2020, 1, 5), side=Side.LONG, action=Action.EXIT)
        short_exit = Signal(date=datetime(2020, 1, 4), side=Side.SHORT, action=Action.EXIT)
        return [long_entry, short_exit, short_entry, long_exit], [
            MatchedSignal(entry=long_entry, exit=long_exit),
            MatchedSignal(entry=short_entry, exit=short_exit),
        ]


@parametrize_with_cases("signals, expected_matches", cases=MatchedSignalsCases)
def test__match_signals(signals: list[Signal], expected_matches: list[MatchedSignal]):
    matches = _match_signals(signals)
    assert matches == expected_matches
