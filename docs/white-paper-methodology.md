# Privé Technologies - Private Asset Methodology

**Risk & Analytics Representation of Illiquid Private Holdings**
Comparable-based proxy construction for private & illiquid assets.

**Version 1.1 - 2026-08-21** (supersedes v1.0, 2025-07-10)
Config version at time of writing: `2026-08-21.1` (`engine/config/mappings.yaml`).

> This document is the white paper of record. It takes the v1.0 white paper as
> its base and revises it to reflect changes made in response to model-validation
> review. Where a section changed materially, the change is called out inline and
> summarised in the changelog below.

---

## What changed since v1.0 (response to review)

| # | Reviewer point | Change in v1.1 | Section |
|---|---|---|---|
| 1 | The baseline traded universe is never defined | Baseline universe is defined as the **client's own investible universe** (their market-data entitlement); prototype data is explicitly illustrative | §4.1 |
| 2 | No leverage input; equity beta of a levered deal differs from an unlevered comp | **Leverage (net debt / EBITDA) is now a matching metric**, and the basket's equity beta is **Hamada-relevered** to the holding's capital structure | §4.2, §4.3, §5.3 |
| 3 | Fundamental similarity is asserted to equal return co-movement | Stated explicitly as an **empirical** claim, established by the backtest (§6), not by the proxy-point geometry; Appendix A corrected | §2.2, §6, Appendix A |
| 4 | No validation / backtest | **Out-of-sample leave-one-out backtest** added (tracking error, correlation, R², beta), with a Backtest screen | §6 |
| 5 | k=3 with inverse-distance weighting is unstable | `k` defaults to **8**; added a **distance floor** and a **single-name weight cap** | §5.1, §5.4 |
| 6 | Euclidean on correlated metrics double-counts size | **Mahalanobis distance** (ridge-regularised) is now the default; **per-metric weights** so margins ≠ size | §5.2 |
| 7 | Dropping absent metrics ≈ assuming the universe mean; distances not comparable across coverage | Distances are **RMS-normalised** by dimension count; the implicit prior is documented | §5.2, §7 |
| 8 | Hedge funds cannot be placed in a revenue/EBITDA space | **Hedge Fund removed** from supported classes; routed to manual mapping (return-based style analysis is the correct tool) | §3 |
| 9 | Vintage year as a categorical filter does not capture the J-curve | Vintage used **numerically**: fund age + % called → a **deployment (J-curve) stage** | §5.6 |

---

## 1. Introduction

Privé provides a tool for representing illiquid private holdings inside the same
risk and portfolio analytics stack used for listed positions. A private or
illiquid holding has no continuous, market-observable price series, so a risk
engine cannot treat it like a listed line item. Privé resolves this with a
**proxy-asset**: an explicit, auditable representation of the holding built
entirely from liquid, traded assets, so the private holding can flow through the
same analytics as a listed position - Value-at-Risk and Conditional VaR,
tracking error, stress tests, factor attribution, contribution-to-risk and
coverage.

**Scope of this build.** This build produces a **risk / analytics
representation, not a valuation or a fair-value mark.** The proxy is a
*behavioural* stand-in for how a holding **moves** with markets, not a statement
of what it is **worth**. NAV is consumed as an input for anchoring and validation
only; it is never re-derived as an output (see §2.2).

---

## 2. What a proxy-asset is - and how Privé builds it

A proxy-asset maps an illiquid private holding onto a basket of liquid traded
assets whose combined market behaviour approximates that of the holding. Because
the traded basket has a continuous price history, every analytic the platform
runs on a listed position can then be run on the private holding through its
proxy.

### 2.1 Approximation from input metrics (no factor library)

Privé does not rely on a fixed, curated library of named risk factors. The proxy
is constructed entirely by approximation from the holding's own input metrics -
the fundamentals the user supplies (revenue, EBITDA, net income, margins, size,
leverage, yield). Concretely:

1. Each traded asset in a baseline universe is described by the **same metrics**.
2. Every asset (traded or private) is therefore a **point in a shared metric space**.
3. The private holding is placed in that space from its supplied metrics.
4. Its proxy is a **weighted basket of the traded assets nearest to it** in that
   space - its closest comparables.

This is a comparable-company / nearest-neighbour construction in standardised
metric space. It is deliberately simple, transparent and defensible: there is no
black-box factor model and no proprietary factor table. The "factors" are the
client-visible input metrics themselves, and the construction visualises
naturally - assets are dots in metric space and the holding and its proxy sit in
the same picture (§5.5).

### 2.2 What the proxy claims - and the fundamental-similarity caveat *(updated)*

The proxy answers a **behavioural** question, not a valuation question:

| | In scope | Out of scope |
|---|---|---|
| **Purpose** | Risk & portfolio analytics representation | Valuation / fair-value marking |
| **Question** | "How does this holding *behave* vs. traded markets?" | "What is it *worth* today?" |
| **Output** | A basket of traded comparables (weights) the analytics stack can consume | (none) |
| **NAV role** | Input - anchoring & validation only | Not re-derived |

**Fundamental similarity is not, by itself, return co-movement.** The distance
metric optimises for *fundamental* resemblance; what a VaR/covariance engine
ultimately needs is *return* co-movement. These are related - assets with similar
size, profitability and leverage in the same sector tend to share systematic risk
- but the link is an **empirical** claim, not a geometric identity. v1.1 does not
assert it; it **measures** it, out of sample, in the validation harness (§6). The
honest division of labour is: a proxy is designed to capture the **systematic /
market** component of a holding's behaviour; it does **not** capture single-name
idiosyncratic risk (a specific write-down, a manager's alpha, deal timing). §6
quantifies both sides of that line.

---

## 3. Supported private asset classes *(updated - Hedge Fund removed)*

- Direct Private Equity · Direct Private Debt · Direct Real Estate
- Private Equity Fund · Private Debt Fund · Real Estate Fund

Holdings whose class is unrecognised are routed to **manual mapping** rather than
guessed.

**Hedge funds are deliberately not supported here.** Strategy type plus vintage
year cannot place a market-neutral or macro fund in a revenue/EBITDA metric
space - a hedge fund's return behaviour is defined by its *strategy exposures*,
not by company fundamentals. The accepted method is **return-based style analysis**
(à la Sharpe), which is a different tool and out of scope for this
comparable-construction build. A hedge-fund holding therefore classifies as
unrecognised and is routed to manual mapping with a recorded reason.

---

## 4. Inputs the method needs

All financial metrics are **optional**; a user may not have them all. The engine
uses whatever is present and degrades gracefully, flagging confidence
accordingly. A small set of inputs is required only to make a **minimum
computation** possible.

### 4.1 Required for a minimum computation - and what the baseline universe is *(updated)*

- **Name** - identity.
- **Asset class** (§3) - selects and filters the eligible comparables.
- **Currency** (ISO-4217) - representation and anchoring.
- **At least one numeric metric** - a holding with no metric cannot be placed in
  metric space.

**Definition of the baseline traded universe.** The comparables are drawn from
the **client's own investible universe** - the set of liquid, traded instruments
the client is entitled to via their market-data subscription. There is no single
global universe: the pool of eligible proxies matches each client's entitlement,
so a client with broad EM coverage draws EM comparables, and a client with only
US large-cap data draws from that. In production this universe is delivered by the
EPC endpoint. **In this prototype the universe is an illustrative ("dummy") sample
of ~50 large listed companies**, assembled only to demonstrate the mechanics; it
is not licensed market data, not a recommended universe, and is replaced per
client at deployment. (This is surfaced as a heads-up banner on the Baseline
Universe screen.)

### 4.2 Metric inputs *(updated - leverage added)*

Numeric fundamentals used as coordinates in the comparison space. Each one
supplied sharpens the match; absent ones are dropped and noted (see §7 for the
implication).

- **Size / scale:** revenue, EBITDA, net income (market value / NAV can serve as a
  size anchor).
- **Profitability:** EBITDA margin, net margin (derived when both parts exist).
- **Capital structure *(new)*:** **net debt** and **leverage (net debt / EBITDA)**.
  Supplied directly as a multiple, or derived from net debt and EBITDA. Leverage
  is a first-class matching axis (§4.3).
- **Debt-specific:** expected yield, maturity / tenor, seniority, credit rating.
- **Real-estate-specific:** occupancy rate, property type.
- **Fund-specific:** strategy type, vintage year (used numerically - §5.6).

### 4.3 Capital structure & leverage (Hamada relevering) *(new)*

Standard comparable-company practice does not compare a levered private holding
to a listed comp at face value. A sponsor-backed deal running at **4-6× net
debt/EBITDA** has a materially different **equity beta** from a listed comparable
at 1-2×, purely because of capital structure. v1.1 addresses this in two ways:

1. **Leverage is a matching metric.** Because net-debt/EBITDA is one of the
   coordinates, comparables are selected with a *similar capital structure* in the
   first place, not just similar size and margins.

2. **The basket's equity beta is Hamada-relevered** to the holding's leverage and
   reported alongside the proxy. Using the Hamada relation
   `βL = βU · [1 + (1 − t)·(D/E)]`, we unlever the basket's (weighted-average)
   equity beta to an asset beta at the basket's D/E and relever it to the
   holding's D/E. The reported scalar is

   ```
   relever_factor = [1 + (1 − t)·(D/E)_holding] / [1 + (1 − t)·(D/E)_basket]
   ```

   where `D/E` uses net debt over equity (NAV for the holding; market cap for each
   comparable) and `t` is a configurable marginal tax rate (default 25%). A factor
   > 1 means the holding is more levered than its comparables, so its equity beta
   is scaled **up**; < 1 means the opposite. This is a **reported adjustment** the
   analytics stack applies to the proxy's beta - it does **not** re-select
   comparables. When the inputs needed (net debt / leverage and equity) are
   absent, leverage still serves as a matching metric and the relever factor is
   simply omitted.

### 4.4 Categorical inputs

Optional filters that improve relevance: region / geography and sector /
industry. When populated, they restrict comparables to the like-for-like part of
the universe.

### 4.5 Fund capital-call inputs

Private funds are commitment-based: an LP commits a total amount but only a
fraction is paid in (called) at any time; the remainder is uncalled capital
subject to future drawdowns. These optional inputs are surfaced in a user-toggled
section:

- **Commitment** - total committed capital.
- **Paid-in (called to date)** - cumulative capital contributed; defaults to the
  sum of the calls if a schedule is supplied.
- **Capital-call line of credit** - a facility LPs use to bridge calls.
- **Capital-call schedule** - individual drawdowns, each with a date, amount and
  purpose.

---

## 5. Proxy construction - the mapping logic

Construction is a deterministic, config-driven pipeline
(`engine/config/mappings.yaml`, versioned). The mapping core is built from pure
functions with data injected and makes no network calls. The two central
formulae are the standardised distance (§5.2) and the guarded inverse-distance
weighting (§5.4).

The pipeline:

1. **Select metrics** - the configured comparison metrics present on the holding.
   Absent optional metrics are dropped from the distance calculation and noted.
2. **Transform & standardise** - size-like metrics (revenue, EBITDA, net income,
   market value, net debt) are log-scaled; every metric is z-scored against the
   baseline universe's mean and σ. Transform parameters are recorded for audit.
3. **Filter comparables (optional)** - restrict by sector and/or region per
   config; if too few remain, relax and record that the relaxation fired.
4. **Distance** - the standardised distance from the holding to each eligible
   traded asset over the selected metrics (§5.2).
5. **Select the k nearest** comparables (config `k`, with a configured minimum).
6. **Weight** - convert distances to weights, normalised to sum to 100%, subject
   to a distance floor and a single-name cap (§5.4).
7. **Proxy point** - the weighted average of the comparables' coordinates gives
   the proxy's implied position in metric space (for the scatter view).
8. **Capital-structure relevering** - the Hamada relever factor (§4.3).
9. **Confidence / coverage** - driven by how many metrics were available, how
   close the nearest comparables are (on the RMS scale), and whether filters were
   relaxed → high / medium / low.

### 5.1 Number of comparables and stability *(updated)*

`k` defaults to **8** (not 3). Three single names carry enormous idiosyncratic
risk relative to any diversified private holding, so the basket is deliberately
wider. A minimum of 3 comparables is required for a valid proxy; below that the
holding is flagged rather than forced.

### 5.2 Distance: Mahalanobis, weighted, and RMS-normalised *(updated)*

Plain Euclidean distance on z-scored metrics assumes the axes are orthogonal and
equally important. Neither holds: revenue, EBITDA and net income are strongly
correlated, so Euclidean distance **double-counts size**; and nothing justifies
EBITDA margin carrying the same weight as size in determining return behaviour.
v1.1 makes three corrections:

- **Mahalanobis distance (default).** Distance is measured against the
  **covariance** of the metrics, estimated from the baseline universe in
  standardised space, so correlated size metrics are not counted multiple times.
  The covariance is **ridge-regularised** (shrunk toward the identity) for
  numerical stability and robustness; a large ridge degenerates gracefully back
  toward Euclidean. Euclidean remains available via config.

- **Per-metric weights.** Each axis is scaled by `√w` before distance, so the
  config can state that margins carry less weight than size (defaults: size 1.0,
  net income 0.7, leverage 0.8, margins 0.5). Weighting is applied consistently to
  both the Euclidean and Mahalanobis paths (and to the covariance estimate).

- **RMS normalisation.** The distance is divided by the number of contributing
  dimensions (root-mean-square), so a "distance of 1" means the same thing whether
  a holding was matched on two metrics or six. This makes distances - and hence
  the confidence thresholds - comparable across holdings with different coverage.

  ```
  d(h, aᵢ)_euclidean   = √( (1/n) · Σⱼ wⱼ (z_hj − z_ij)² )
  d(h, aᵢ)_mahalanobis = √( (1/n) · Δᵀ Σ⁻¹ Δ ),   Δⱼ = √wⱼ (z_hj − z_ij)
  ```

### 5.3 Weights, currency & determinism

- Basket weights are non-negative and sum to 100%.
- Each comparable carries its traded identifier and currency; a currency mismatch
  versus the holding is preserved as genuine FX exposure, never silently dropped.
- Identical inputs plus identical config version produce an identical proxy. The
  config version is stamped on every explanation object.

### 5.4 Weighting guards - distance floor and single-name cap *(new)*

Inverse-distance weighting degenerates: a comparable at near-zero distance would
take a near-100% weight, collapsing the basket to a single name. Two config
guards prevent this:

- **Distance floor** (default 0.35, standardised RMS units) - the distance used
  in the weighting is floored, so an extremely close comparable cannot dominate.
- **Single-name cap** (default 35%) - any weight above the cap is water-filled
  onto the remaining comparables, so `k ≥ 3` names genuinely share the basket.

Softmax weighting remains available as an alternative to inverse-distance.

### 5.5 Explanation & scatter visualisation

Every proxy ships with a full explanation object: metrics used and their
transforms; the **distance metric** used; filters applied and any relaxation;
comparables chosen with their distances and weights; the proxy composition and
implied proxy point; the capital-structure relever; the confidence flag; and the
config version and timestamp. Because every asset is a point in metric space, the
construction is directly viewable - the user picks any two metrics as x/y axes and
sees the baseline, the holding, the proxy point and the weighted comparables in
one picture.

### 5.6 Fund capital calls, vintage & the J-curve *(updated)*

The proxy basket describes a fund's **market behaviour** (its factor/beta
profile), and comparable selection is unaffected by capital-call inputs. What
capital calls change is the **notional** the proxy behaviour is applied to,
because in a commitment-based fund only the invested capital is exposed to
markets. The engine derives, deterministically:

| Quantity | Definition |
|---|---|
| **Paid-in** | explicit paid-in, else the sum of the capital-call schedule |
| **Uncalled commitment** | commitment − paid-in |
| **% called** | paid-in ÷ commitment |
| **Effective market exposure** | NAV if marked, else paid-in - the notional the proxy basket represents |
| **Net uncovered commitment** | max(uncalled − capital-call line, 0) - contingent liquidity not covered by a facility |
| **Each call's share** | call amount ÷ commitment |

**Key risk treatment.** Effective market exposure is sized to invested capital
(NAV / paid-in), and uncalled commitment is treated as a **contingent liquidity
obligation, not market exposure**. Applying the proxy's market beta to the full
commitment would overstate market risk; ignoring the uncalled portion would
understate liquidity risk. The engine reports both figures side by side. This
capital-call section is unchanged from v1.0 - it was already correct.

**Vintage & the J-curve (new).** Vintage year is used **numerically**, not as a
categorical label. A 2024-vintage fund at 20% called behaves nothing like a 2016
vintage at full deployment. The engine derives **fund age** (as-of year −
vintage) and, combined with **% called**, a **deployment (J-curve) stage** -
`investing → deploying → maturing → harvesting`. Deployment dominates when known;
age is the fallback. This tells the risk team how much of the commitment is
actually market-exposed today and where the fund sits on its J-curve, rather than
bucketing by vintage label.

---

## 6. Validation - out-of-sample backtest *(new)*

The first question any model-validation function asks is: *what is the tracking
error of the proxy against realised returns?* v1.1 answers it with a
**leave-one-out backtest**:

1. Take a hold-out sample of traded assets and **treat each as if it were
   private** (its fundamentals only).
2. Build a proxy for it from the **rest** of the universe - the held-out asset is
   excluded, so the test is genuinely out of sample.
3. Compare the proxy basket's realised return series to the asset's own:
   **annualised tracking error**, **correlation**, **R²** and **beta**.
4. Aggregate across the sample (median / mean tracking error, correlation, R²,
   beta).

**What the numbers show, honestly.** Tracking error is dominated by the held-out
name's **single-name idiosyncratic** risk, which no proxy can capture - the proxy
is built to represent **systematic / market** behaviour, which the correlation,
R² and beta columns measure. A proxy that explains ~half the variance and matches
beta, with residual tracking error at the level of single-name idiosyncratic
vol, is behaving exactly as the methodology claims (§2.2) - no more, no less.

**On the returns used.** In this prototype the return series are **illustrative /
simulated** - a transparent factor model (market + sector + single-name
idiosyncratic) - so the harness and its statistics can be demonstrated end to
end. The systematic component is capturable by comparables while the idiosyncratic
component is not, by construction. **In production the identical backtest runs on
the client's real return history**; only the data source changes, not the method.
This is surfaced prominently on the Backtest screen.

---

## 7. The absent-metric prior - an honest note *(new)*

Dropping a metric a holding does not supply is not neutral. Two consequences are
stated plainly rather than hidden behind "graceful degradation":

- **It is an indifference prior on that axis.** A holding is only compared on the
  metrics it actually has; comparables are required to share those metrics. Not
  constraining an axis is closer to "match anywhere on this axis" than to "assume
  the universe mean" - either way it is a prior, and it is disclosed via the
  confidence flag and the list of metrics used.
- **Distances are made comparable across coverage.** Because distance is
  RMS-normalised (§5.2), a holding matched on two metrics and one matched on six
  sit on the same distance scale, so the near/far confidence thresholds mean the
  same thing for both. This does not manufacture the missing information - it
  simply stops coverage differences from silently distorting the geometry, and
  low coverage is still flagged as lower confidence.

---

## 8. Transforms relevant to the risk/analytics goal

- **Appraisal de-smoothing (standard public technique).** Private NAVs are
  appraisal-based and smoothed, understating volatility and beta. De-smoothing
  recovers a more realistic return series before it is used to sanity-check a
  proxy.
- **NAV roll-forward (analytics continuity only).** Between NAV dates, the proxy's
  traded return series rolls the last reported NAV forward to give analytics a
  continuous path - explicitly an estimated path, not a valuation, always
  reconciled to the next reported NAV.

---

## 9. Limitations & failure modes *(updated)*

| Situation | Behaviour | Confidence |
|---|---|---|
| Unrecognised asset class (incl. hedge funds) | Routed to manual mapping (reason recorded); hedge funds → return-based style analysis | n/a |
| No numeric metric supplied | Cannot place in metric space → manual mapping | n/a |
| Only one metric supplied | Proxy built on a single axis | Low |
| Sparse baseline after filtering | Filter relaxed and recorded | Medium |
| Nearest comparables still far away (high RMS distance) | Proxy built but flagged | Low |
| Near-zero-distance comparable | Distance floored + weight capped so the basket stays diversified | as matched |
| Currency mismatch | Kept as FX exposure | as matched |
| Leverage inputs absent | Leverage dropped as a matching axis; relever factor omitted | noted |
| Appraisal-smoothed history unadjusted | Volatility/beta understated; de-smoothing (§8) mitigates | risk noted |
| Uncalled fund commitment | Market exposure sized to invested capital; uncalled reported as contingent liquidity (§5.6) | n/a |

**Caveats for a client risk team.** The proxy captures **systematic / market**
behaviour via comparables - quantified out of sample in §6 - not deal-specific
outcomes (a write-down, capital-call timing, manager alpha). Proxy quality is
bounded by the metrics the user can supply and by the breadth and quality of the
client's baseline traded universe (§4.1). **Nothing here is a valuation.**

---

## 10. End-to-end flow

```
Add private holding - name, class, currency, metrics (metrics optional;
        minimum = class + currency + ≥1 metric)
        │
        ▼
Select comparison metrics present → transform + standardise vs. baseline universe
        │
        ▼
Filter baseline by sector / region (optional; relax if sparse)
        │
        ▼
Distance (Mahalanobis, weighted, RMS-normalised) → k nearest traded comparables
        → inverse-distance weights, distance-floored & capped (sum 100%)
        │
        ▼
Proxy basket + implied proxy point + Hamada beta relever + capital-call/J-curve
        + Explanation (metrics, distance metric, comparables, weights, confidence, config version)
        │
        ▼
Review on scatter → Accept | Edit weights | Replace | Reject → persist override (who / when / why)
        │
        ▼
Proxy consumed by risk & portfolio analytics as a liquid basket
        │
        ▼
Validation: out-of-sample leave-one-out backtest (tracking error, correlation, R², beta)
```

---

## Appendix A: Worked example - nearest-neighbour construction *(corrected)*

A compact two-metric example makes the construction concrete. Two metrics are
used so it maps directly onto the scatter view. In production the same logic runs
over every configured metric that is present, using the Mahalanobis distance of
§5.2.

**Holding H** - Direct Private Equity, Europe, Industrials. Supplied metrics:
revenue = $120m, EBITDA margin = 22%.

Baseline standardisation parameters: `ln(revenue $m)`: mean 4.50, σ 1.20; EBITDA
margin: mean 0.18, σ 0.08. Placing H in standardised space:
`z_H = ((ln120 − 4.50)/1.20, (0.22 − 0.18)/0.08) = (0.24, 0.50)`.

Four eligible comparables, standardised, with their distance to H (illustrative):

| Comparable | z (size) | z (margin) | Distance to H | k-nearest? | Weight |
|---|---|---|---|---|---|
| A | 0.43 | 0.25 | 0.31 | Yes (1st) | 42.9% |
| B | 0.00 | 0.88 | 0.45 | Yes (2nd) | 30.1% |
| C | 0.67 | 0.75 | 0.49 | Yes (3rd) | 27.1% |
| D | 0.17 | −0.38 | 0.88 | No | - |

With `k = 3`, comparables A, B and C are selected; inverse-distance weights
(floored and capped per §5.4) give the basket. The implied proxy point is the
weighted average of the comparables' coordinates, `z_proxy ≈ (0.36, 0.57)`, near
H's `(0.24, 0.50)`.

**What the proxy point does - and does not - tell you.** *(corrected)* The proxy
point sitting near H confirms only that the basket's average fundamentals are
close to H's - it is a **consistency check on the construction**, nothing more.
It is **not** evidence of proxy quality, because "the average of three points
lands between them" is arithmetic, not tracking. The proxy point being near H
says nothing about whether the basket's **returns** will co-move with H's. That
question - the one a VaR/covariance engine cares about - is answered only by the
**out-of-sample backtest (§6)**, which measures realised tracking error,
correlation and beta. Read the proxy point as a sanity check; read §6 for
quality.

Because two metrics were used, the nearest comparable sits at a moderate
distance, and no filter relaxation was needed, this example flags **Medium**
confidence. The engine emits the whole computation - metrics, standardisation
parameters, distance metric, distances, the k-selection, the weights, the proxy
point, the relever factor and the confidence flag - as the explanation object,
versioned by config, ready for the analytics stack to consume the basket as a
liquid line item.
