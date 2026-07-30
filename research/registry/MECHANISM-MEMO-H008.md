# Mechanism Memo: Thin-Session / High-Volatility Interaction

**Written:** 2026-07-25, BEFORE any exploratory look at the conditioning
variable, per `research/CONDITIONAL_SEARCH_CHARTER.md` Section 3's
sequencing rule. This memo commits the mechanism, counterparty, prior,
and per-instrument sign prediction. No data has been examined for this
candidate as of this commit.

---

## 1. The economic story

Both marginals are individually dead: H-002/H-004 killed session
structure, H-005 killed volatility regime as standalone conditioning
variables. This memo does not re-test either marginal. It tests whether
their INTERACTION carries structure that averaging over each margin
separately destroys.

**The claim:** when a volatility shock (a high-ATR bar) occurs during a
session where an instrument has genuinely thin, non-home liquidity, the
price move is more likely to be a temporary overshoot that partially
reverts once deeper-session liquidity arrives -- rather than a
directionally "clean" move of the kind that occurs when the same
volatility shock happens during the instrument's home/deep session.
Averaged across all sessions (H-005) or across all volatility levels
within a session (H-002/H-004), this effect washes out -- it should only
be visible at the specific intersection of "high volatility" AND "thin
session for this instrument."

## 2. The counterparty -- who is systematically wrong, and why they can't arbitrage it away

During an instrument's thin/non-home session, the marginal liquidity
providers are structurally thinner: fewer professional market-makers
actively quoting, wider natural spreads, lower depth-of-book. When a
volatility shock hits in this window (a news release, a large order, a
correlated move from a more liquid instrument), the thin liquidity
cannot absorb it efficiently -- price moves further than the shock's
"true" informational content justifies, because there isn't enough
competing liquidity to keep the move tight. Once the instrument's home
session opens and deeper, better-informed liquidity arrives, some of
that overshoot corrects.

**Why this isn't already arbitraged away:** the counterparties capable
of correcting this (deep-session market-makers) are, by construction,
not YET active during the thin window when the dislocation happens --
they can only trade on it once their own session opens, which is
exactly the reversion this memo predicts, not a contradiction of the
mechanism. This is a structural, session-boundary timing constraint,
not a pure information asymmetry that a fast enough algorithm could
close instantly -- professional liquidity provision itself is
session-scheduled human/institutional capital, not a 24-hour uniform
resource, especially for currency pairs and metals whose natural demand
centers are geographically concentrated.

## 3. Prior: MEDIUM

Justification: thin-liquidity overshoot-and-reversion is a documented
microstructure phenomenon in FX generally (not specific to this
project's instrument set), which supports a real mechanism existing.
However, this project's own dataset has already shown (H-002, H-004,
H-005) that several plausible-sounding, literature-adjacent mechanisms
failed to produce detectable structure at 1H/H4 once the seed-dispersion
check was applied honestly. MEDIUM, not HIGH, reflects that base rate
directly -- this candidate has real theoretical grounding but sits in
the same overall search program that has been 0/7 tradable so far.

## 4. The per-instrument, per-condition sign prediction (committed, falsifiable)

**This project's own `core/instruments.py` metadata already encodes
which sessions are "home" per instrument** -- not a new judgment call
invented for this memo, but the SAME session lists used throughout
H-002/H-004:

| Instrument | Sessions (home/deep) | Tokyo is home? |
|---|---|---|
| USDJPY | tokyo, london, new_york | YES |
| GBPJPY | tokyo, london, new_york | YES |
| AUDUSD | tokyo, london, new_york | YES |
| EURUSD | london, new_york | NO -- tokyo is thin |
| XAUUSD | london, new_york | NO -- tokyo is thin |

**Predicted pattern, stated now, specific enough to be visibly wrong:**

- **EURUSD and XAUUSD** (tokyo = thin session): high-ATR-tercile bars
  occurring during the `tokyo` session window should show LOWER
  (more negative, or more strongly mean-reverting on subsequent bars)
  expectancy for a naive directional entry than high-ATR-tercile bars
  occurring during `london`/`new_york` on the SAME instruments. This is
  the interaction effect the memo predicts exists.
- **USDJPY, GBPJPY, AUDUSD** (tokyo = home session): the tokyo-session
  high-volatility effect should be WEAKER or ABSENT compared to
  EURUSD/XAUUSD's -- because tokyo is not a thin-liquidity window for
  these instruments. If these three show the SAME magnitude
  tokyo-high-vol effect as EURUSD/XAUUSD, that is evidence AGAINST this
  specific mechanism (it would suggest a generic high-vol effect
  unrelated to session-liquidity depth, which is a different,
  unregistered claim requiring its own memo).

**This is the falsification condition, stated in advance:** if
EURUSD/XAUUSD do NOT show a distinguishably stronger tokyo-high-vol
effect than USDJPY/GBPJPY/AUDUSD do, the mechanism as stated here is
refuted -- not "re-interpreted" as evidence for a different, broader
claim. A memo whose story could absorb either outcome would fail the
charter's sign-specificity requirement; this one cannot absorb "no
difference between the two groups" as a pass.

## 5. What this memo does NOT claim

- Does not claim the effect exists in every session, only the
  thin-session/high-vol intersection specifically.
- Does not claim a uniform direction across all five instruments -- the
  2-vs-3 split above IS the claim.
- Does not pre-commit to which specific ATR tercile threshold or which
  exact reversion window (bars-to-revert) -- those are test-design
  parameters to be frozen in the H-008 registration itself, following
  this memo, using the SAME freeze-before-verdict discipline as
  `research/run_h001.py`.

## Provenance

- This memo is committed BEFORE registration. The subsequent H-008
  registration file must reference this memo's commit hash as its
  economic justification, per `research/CONDITIONAL_SEARCH_CHARTER.md`
  Section 3.
- Session metadata source: `core/instruments.py` (unchanged, same
  metadata H-002/H-004 already used -- no new data required for this
  candidate, consistent with the charter's mechanism-cost/data-cost
  prioritization, item #2).
