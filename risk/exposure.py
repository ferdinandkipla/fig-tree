# risk/exposure.py
from core.config import RESEARCH_MODE

class ExposureGuard:

    def __init__(self, max_consecutive_loss: int, max_open_trades: int,
                 max_dd_halt: float):
        self.max_consecutive_loss   = max_consecutive_loss
        self.max_open_trades        = max_open_trades
        self.max_dd_halt            = max_dd_halt
        self._consecutive_losses    = 0
        self._open_trades           = 0
        self._bars_since_last_trade = 0

    def can_trade(self, current_dd: float) -> bool:
        # Research mode: only block if already in a trade
        # No halts — we want full cycle statistics
        if RESEARCH_MODE:
            return self._open_trades < self.max_open_trades

        # Production mode: all guards active
        if self._consecutive_losses >= self.max_consecutive_loss:
            if self._bars_since_last_trade >= 50:
                self._consecutive_losses    = 0
                self._bars_since_last_trade = 0
            else:
                return False
        if self._open_trades >= self.max_open_trades:
            return False
        if current_dd <= self.max_dd_halt:
            return False
        return True

    def on_bar(self):
        if self._open_trades == 0:
            self._bars_since_last_trade += 1

    def on_win(self):
        self._consecutive_losses    = 0
        self._bars_since_last_trade = 0
        self._open_trades           = max(0, self._open_trades - 1)

    def on_loss(self):
        self._consecutive_losses   += 1
        self._bars_since_last_trade = 0
        self._open_trades           = max(0, self._open_trades - 1)

    def on_open(self):
        self._open_trades          += 1
        self._bars_since_last_trade = 0