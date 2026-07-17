# strategies/trend_pullback/params.py
from core.config import TREND_PULLBACK as P

EMA_FAST           = P["ema_fast"]
EMA_SLOW           = P["ema_slow"]
ADX_PERIOD         = P["adx_period"]
ADX_THRESHOLD      = P["adx_threshold"]
#ADX_CEILING        = P["adx_ceiling"]
ATR_PERIOD         = P["atr_period"]
STOP_ATR_MULT      = P["stop_atr_multiplier"]
RISK_REWARD        = P["risk_reward"]
PULLBACK_TOLERANCE = P["pullback_tolerance"]