# research/walkforward.py
# ZenithFlow Walk-Forward Validation Harness
# ----------------------------------------------------------------------
# PURPOSE: Derive filter rules from TRAIN (2019-2021), freeze them,
#          then test ONCE on TEST (2022-2025). Out-of-sample verdict.
#
# DISCIPLINE: Rules are frozen to disk with a SHA-256 hash AFTER train.
#             Test phase refuses to run unless a frozen rules file exists.
#             Editing rules after seeing test breaks the hash → halts.
#
# Does NOT touch strategy/signals/simulator.
# Operates on per-trade CSV output (research/trades_*.csv).
# ----------------------------------------------------------------------

import pandas as pd
import numpy as np
import json
import hashlib
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
TRAIN_START = pd.Timestamp("2019-01-01")
TRAIN_END   = pd.Timestamp("2022-01-01")   # exclusive
TEST_START  = pd.Timestamp("2022-01-01")
TEST_END    = pd.Timestamp("2025-01-01")   # exclusive

INSTRUMENTS = {
    "USDJPY": "PRIMARY",
    "XAUUSD": "CONFIRMATORY",
    "GBPJPY": "CONFIRMATORY",
}

TRADES_DIR  = Path("research")
FROZEN_FILE = Path("research/frozen_rules.json")

MIN_TRADES_PER_BUCKET = 15


# ----------------------------------------------------------------------
# METRICS
# ----------------------------------------------------------------------
def profit_factor(pnl: pd.Series) -> float:
    gains  = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    if losses == 0:
        return 999.0 if gains > 0 else 0.0
    return round(gains / losses, 3)

def summarize(df: pd.DataFrame, label: str) -> dict:
    if len(df) == 0:
        return {"label": label, "trades": 0, "pf": 0.0,
                "wr": 0.0, "expectancy": 0.0, "total_pnl": 0.0}
    pnl = df["pnl"]
    return {
        "label":      label,
        "trades":     int(len(df)),
        "pf":         profit_factor(pnl),
        "wr":         round((pnl > 0).mean() * 100, 1),
        "expectancy": round(pnl.mean(), 2),
        "total_pnl":  round(pnl.sum(), 2),
    }


# ----------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------
def load_trades(symbol: str) -> pd.DataFrame:
    path = TRADES_DIR / f"trades_{symbol}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run full backtest first."
        )
    df = pd.read_csv(path)

    # Auto-detect entry time column
    time_col = next(
        (c for c in ["entry_dt", "entry_time", "entry_date", "time", "datetime"]
         if c in df.columns), None
    )
    if time_col is None:
        raise KeyError(
            f"{path} has no entry-time column. "
            f"Columns found: {list(df.columns)}"
        )
    df["_entry_dt"] = pd.to_datetime(df[time_col])

    for col in ["pnl", "adx_entry", "atr_entry"]:
        if col not in df.columns:
            raise KeyError(f"{path} missing required column '{col}'.")

    return df

def split_train_test(df: pd.DataFrame):
    train = df[
        (df["_entry_dt"] >= TRAIN_START) &
        (df["_entry_dt"] <  TRAIN_END)
    ].copy()
    test = df[
        (df["_entry_dt"] >= TEST_START) &
        (df["_entry_dt"] <  TEST_END)
    ].copy()
    return train, test


# ----------------------------------------------------------------------
# PHASE A — derive rules from TRAIN ONLY
# ----------------------------------------------------------------------
def derive_rules(train: pd.DataFrame, symbol: str) -> dict:
    rules = {
        "symbol":            symbol,
        "adx_ceiling":       None,
        "exclude_high_vol":  False,
        "_train_evidence":   {}
    }

    # ADX bucket analysis
    train = train.copy()
    train["adx_bucket"] = pd.cut(
        train["adx_entry"],
        bins=[0, 20, 25, 35, np.inf],
        labels=["<20", "20-25", "25-35", ">35"]
    )
    adx_perf = {}
    for b in ["<20", "20-25", "25-35", ">35"]:
        sub = train[train["adx_bucket"] == b]
        adx_perf[b] = summarize(sub, f"ADX {b}")
    rules["_train_evidence"]["adx"] = adx_perf

    b2025 = adx_perf["20-25"]
    b2535 = adx_perf["25-35"]
    b35   = adx_perf[">35"]
    if (b2025["trades"] >= MIN_TRADES_PER_BUCKET and
            b2025["pf"] > 1.10 and
            b2535["pf"] < 1.0 and
            b35["pf"]   < 1.0):
        rules["adx_ceiling"] = 25.0

    # ATR regime analysis
    train["atr_regime"] = pd.qcut(
        train["atr_entry"], q=3,
        labels=["low_vol", "med_vol", "high_vol"]
    )
    atr_perf = {}
    for r in ["low_vol", "med_vol", "high_vol"]:
        sub = train[train["atr_regime"] == r]
        atr_perf[r] = summarize(sub, f"ATR {r}")
    rules["_train_evidence"]["atr"] = atr_perf

    hv         = atr_perf["high_vol"]
    others_pf  = [atr_perf["low_vol"]["pf"], atr_perf["med_vol"]["pf"]]
    if (hv["trades"] >= MIN_TRADES_PER_BUCKET and
            hv["pf"] < 0.90 and
            hv["pf"] < min(others_pf)):
        rules["exclude_high_vol"] = True
        rules["high_vol_atr_threshold"] = float(
            train["atr_entry"].quantile(2/3)
        )

    return rules


# ----------------------------------------------------------------------
# FREEZE / HASH
# ----------------------------------------------------------------------
def _rules_hash(all_rules: dict) -> str:
    decisions = {
        s: {
            "adx_ceiling":            r["adx_ceiling"],
            "exclude_high_vol":       r["exclude_high_vol"],
            "high_vol_atr_threshold": r.get("high_vol_atr_threshold"),
        }
        for s, r in all_rules.items()
    }
    blob = json.dumps(decisions, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()

def freeze_rules(all_rules: dict):
    payload = {
        "frozen_at":    datetime.now().isoformat(),
        "train_window": [str(TRAIN_START.date()), str(TRAIN_END.date())],
        "test_window":  [str(TEST_START.date()),  str(TEST_END.date())],
        "rules":        all_rules,
        "hash":         _rules_hash(all_rules),
    }
    FROZEN_FILE.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n[FREEZE] Rules locked → {FROZEN_FILE}")
    print(f"[FREEZE] Hash: {payload['hash'][:16]}...")

def load_frozen() -> dict:
    if not FROZEN_FILE.exists():
        raise FileNotFoundError(
            "No frozen rules. Run --train before --test."
        )
    payload = json.loads(FROZEN_FILE.read_text())
    if _rules_hash(payload["rules"]) != payload["hash"]:
        raise RuntimeError(
            "FROZEN RULES TAMPERED. Hash mismatch. "
            "Delete frozen_rules.json and re-run --train honestly."
        )
    return payload


# ----------------------------------------------------------------------
# APPLY rules to a trade set
# ----------------------------------------------------------------------
def apply_rules(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    out = df.copy()
    if rule["adx_ceiling"] is not None:
        out = out[out["adx_entry"] < rule["adx_ceiling"]]
    if rule["exclude_high_vol"] and rule.get("high_vol_atr_threshold"):
        out = out[out["atr_entry"] < rule["high_vol_atr_threshold"]]
    return out


# ----------------------------------------------------------------------
# REPORTING
# ----------------------------------------------------------------------
SEP  = "=" * 62
SEP2 = "-" * 62

def print_rule(symbol, tag, rule):
    ev = rule["_train_evidence"]
    print(f"\n  {symbol} [{tag}]")
    print(f"  {SEP2}")
    print(f"  ADX ceiling      : {rule['adx_ceiling']}")
    print(f"  Exclude high_vol : {rule['exclude_high_vol']}")
    if rule.get("high_vol_atr_threshold"):
        print(f"  High vol ATR threshold : {rule['high_vol_atr_threshold']:.5f}")

    print(f"\n  TRAIN ADX evidence:")
    for bucket, stats in ev["adx"].items():
        flag = " ◄" if stats["pf"] < 1.0 else ""
        print(f"    ADX {bucket:<8} : "
              f"{stats['trades']:>3} trades  "
              f"PF {stats['pf']:>5}  "
              f"WR {stats['wr']:>5.1f}%  "
              f"exp ${stats['expectancy']:>7.2f}{flag}")

    print(f"\n  TRAIN ATR evidence:")
    for regime, stats in ev["atr"].items():
        flag = " ◄" if stats["pf"] < 1.0 else ""
        print(f"    {regime:<10} : "
              f"{stats['trades']:>3} trades  "
              f"PF {stats['pf']:>5}  "
              f"WR {stats['wr']:>5.1f}%  "
              f"exp ${stats['expectancy']:>7.2f}{flag}")

def print_verdict(symbol, tag, before, after):
    print(f"\n  {SEP2}")
    print(f"  {symbol} [{tag}] — OUT-OF-SAMPLE VERDICT (2022–2025)")
    print(f"  {SEP2}")
    print(f"  Raw (no rules)  : "
          f"{before['trades']:>3} tr | "
          f"PF {before['pf']:>5} | "
          f"exp ${before['expectancy']:>7} | "
          f"PnL ${before['total_pnl']:>9,.2f}")
    print(f"  Rules applied   : "
          f"{after['trades']:>3} tr | "
          f"PF {after['pf']:>5} | "
          f"exp ${after['expectancy']:>7} | "
          f"PnL ${after['total_pnl']:>9,.2f}")

    verdict = (
        "PASS ✓" if after["pf"] > 1.10 and after["total_pnl"] > 0
        else "FAIL ✗"
    )
    print(f"  VERDICT         : {verdict}")
    return verdict


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def run_train():
    print(SEP)
    print("  WALK-FORWARD  |  PHASE A: TRAIN (2019–2021)")
    print("  Deriving rules from training data only")
    print(SEP)

    all_rules = {}
    for symbol, tag in INSTRUMENTS.items():
        df          = load_trades(symbol)
        train, _    = split_train_test(df)
        print(f"\n[{symbol}] train trades available: {len(train)}")
        if len(train) < 10:
            print(f"  WARNING: only {len(train)} trades in train window.")
            print(f"  Rules derived from this sample are not trustworthy.")
        rule = derive_rules(train, symbol)
        all_rules[symbol] = rule
        print_rule(symbol, tag, rule)

    freeze_rules(all_rules)
    print(f"\n{SEP}")
    print("  PHASE A COMPLETE")
    print("  Rules frozen. Test set NOT yet touched.")
    print("  Read the rules above. Sit with them.")
    print("  Only run --test when ready. Once.")
    print(SEP)

def run_test():
    print(SEP)
    print("  WALK-FORWARD  |  PHASE B: TEST (2022–2025)")
    print("  Sealed out-of-sample verdict")
    print(SEP)

    payload = load_frozen()
    print(f"[OK] Hash verified : {payload['hash'][:16]}...")
    print(f"[OK] Frozen at     : {payload['frozen_at']}")
    print(f"[OK] Train window  : {payload['train_window']}")
    print(f"[OK] Test window   : {payload['test_window']}")

    results = {}
    for symbol, tag in INSTRUMENTS.items():
        df          = load_trades(symbol)
        _, test     = split_train_test(df)
        rule        = payload["rules"][symbol]
        before      = summarize(test, "raw")
        after       = summarize(apply_rules(test, rule), "ruled")
        verdict     = print_verdict(symbol, tag, before, after)
        results[symbol] = (tag, verdict, after)

    # Binding decision
    print(f"\n{SEP}")
    print("  PHASE-1 BINDING VERDICT  (PRIMARY = USDJPY)")
    print(SEP)
    for symbol, (tag, verdict, after) in results.items():
        if tag == "PRIMARY":
            print(f"  {symbol}: {verdict}")
            if "PASS" in verdict:
                print("  → Edge SURVIVES out-of-sample.")
                print("  → Proceed to deeper validation.")
            else:
                print("  → Edge DIES out-of-sample.")
                print("  → Trend-pullback on this setup is not validated.")
                print("  → Per charter: redesign before Phase 2.")
    print(SEP)


if __name__ == "__main__":
    import sys
    if "--train" in sys.argv:
        run_train()
    elif "--test" in sys.argv:
        run_test()
    else:
        print("Usage:")
        print("  python research/walkforward.py --train")
        print("  python research/walkforward.py --test")
        print()
        print("DISCIPLINE:")
        print("  Run --train first. Read output. Do NOT peek at test.")
        print("  Run --test once. Accept the verdict.")