# research/run_h007_verdict.py
#
# H-007: cross-instrument correlation. Direct, deterministic measurement
# on real H1 price data -- no null model, no permutation test, no seed
# dispersion check (see H-007.md's explicit note on evidentiary form).

import sys
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SYMBOLS   = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]
TRAIN_END = "2022-01-01"
THRESHOLD = 0.5

JPY_CROSSES = {"USDJPY", "GBPJPY"}
USD_CROSSES = {"EURUSD", "AUDUSD"}


def load_train_returns(symbol: str) -> pd.Series:
    path = Path(f"data/storage/{symbol}_16385.csv")
    df = pd.read_csv(path, parse_dates=[0])
    df.columns = [c.lower() for c in df.columns]
    dt_col = df.columns[0]
    df = df.set_index(dt_col)
    df = df[df.index < TRAIN_END]
    returns = np.log(df["close"] / df["close"].shift(1)).dropna()
    returns.name = symbol
    return returns


def main():
    returns = {s: load_train_returns(s) for s in SYMBOLS}
    combined = pd.concat(returns.values(), axis=1, join="inner")
    print(f"Common TRAIN timestamps across all 5 instruments: {len(combined)}")

    corr_matrix = combined.corr()
    print("\nPairwise correlation matrix:")
    print(corr_matrix.round(3).to_string())

    pairs = list(combinations(SYMBOLS, 2))
    pair_corrs = []
    print("\nPairwise |correlation|:")
    for a, b in pairs:
        c = corr_matrix.loc[a, b]
        pair_corrs.append({"pair": f"{a}-{b}", "correlation": c, "abs_correlation": abs(c)})
        print(f"  {a}-{b}: {c:.3f}")

    mean_abs_corr = np.mean([p["abs_correlation"] for p in pair_corrs])
    print(f"\nMean pairwise |correlation| across all 10 pairs: {mean_abs_corr:.4f}")
    print(f"Threshold (committed in H-007.md): {THRESHOLD}")
    print(f"Below threshold: {mean_abs_corr < THRESHOLD}")

    jpy_corr = corr_matrix.loc["USDJPY", "GBPJPY"]
    usd_corr = corr_matrix.loc["EURUSD", "AUDUSD"]
    other_corrs = [p["correlation"] for p in pair_corrs
                  if p["pair"] not in ("USDJPY-GBPJPY", "EURUSD-AUDUSD")]
    mean_other = np.mean([abs(c) for c in other_corrs])
    print(f"\nJPY-cross pair (USDJPY-GBPJPY) correlation: {jpy_corr:.3f}")
    print(f"USD-cross pair (EURUSD-AUDUSD) correlation: {usd_corr:.3f}")
    print(f"Mean |correlation| of all OTHER (cross-group) pairs: {mean_other:.3f}")
    print(f"Within-group > cross-group (expected pattern): "
          f"{abs(jpy_corr) > mean_other and abs(usd_corr) > mean_other}")

    result_df = pd.DataFrame(pair_corrs)
    result_df.to_csv("research/H-007-verdict.csv", index=False)
    corr_matrix.to_csv("research/H-007-correlation-matrix.csv")
    print(f"\nSaved -> research/H-007-verdict.csv, research/H-007-correlation-matrix.csv")

    survives = mean_abs_corr < THRESHOLD
    print(f"\nPRIMARY PREDICTION {'SURVIVES' if survives else 'REFUTED'} "
          f"(mean |corr| {'<' if survives else '>='} {THRESHOLD})")
    return result_df, mean_abs_corr


if __name__ == "__main__":
    main()
