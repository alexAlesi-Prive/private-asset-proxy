# Privé Proxy-Asset Methodology

**Status:** Owned by Privé Technologies. Revised to reflect Privé's **metric-based comparable** construction (no fixed factor library).
**Scope of this build (`PROXY_GOAL`):** **Risk / analytics representation.** A proxy-asset maps an illiquid private holding onto **liquid traded assets** so the private holding can flow through the same risk and portfolio analytics as a listed position (VaR/CVaR, tracking error, stress tests, attribution, contribution-to-risk, coverage).

> **This build does not produce a valuation or a fair-value mark.** The proxy is a *behavioural* stand-in for how a holding **moves** with markets, not what it is **worth**. NAV is consumed as an input for anchoring/validation only, never re-derived as an output. See §1.1.

---

## 1. What a proxy-asset is — and how Privé builds it

A private/illiquid holding has **no continuous, market-observable price series**, so risk analytics cannot treat it like a listed line item. A **proxy-asset** is an explicit, auditable representation of that holding built from **liquid, traded assets**.

### 1.1 Privé's approach: approximation from input metrics (no factor library)

**Privé does not rely on a fixed, curated library of named risk factors.** Instead, the proxy is constructed **100% by approximation from the holding's own input metrics** — the fundamentals the user supplies (revenue, EBITDA, net income, margins, size, yield, etc.). Concretely:

1. Each **traded asset** in a baseline universe is described by the **same metrics**.
2. Every asset — traded or private — is therefore a **point in a shared metric space**.
3. The private holding is placed in that space from its supplied metrics.
4. Its **proxy is a weighted basket of the traded assets nearest to it** in that space (its closest *comparables*).

This is a **comparable-company / nearest-neighbour** construction in standardised metric space. It is deliberately simple, transparent, and defensible: there is no black-box factor model and no proprietary factor table — the "factors" are the client-visible input metrics themselves. It also visualises naturally (§5): assets are dots in metric space and the private holding + its proxy sit in the same picture.

### 1.2 Which goal it serves — and which it does not

| | In scope | Out of scope |
|---|---|---|
| **Purpose** | Risk & portfolio **analytics representation** | **Valuation** / fair-value marking |
| **Question** | "How does this holding *behave* vs. traded markets?" | "What is it *worth* today?" |
| **Output** | A basket of traded comparables (weights) the analytics stack can consume | (none) |
| **NAV role** | *Input* — anchoring & validation only | *Not* re-derived |

---

## 2. Supported private asset classes

`DirectPrivateEquity`, `DirectPrivateDebt`, `DirectRealEstate`, `PrivateEquityFund`, `PrivateDebtFund`, `RealEstateFund`, `HedgeFund`. Holdings whose class is unrecognised are routed to **manual mapping** rather than guessed.

---

## 3. Inputs the method needs (per holding)

**All financial metrics are optional** — a user may not have them all. The engine uses whatever is present and degrades gracefully, flagging confidence. A small set is required only to make a **minimum computation** possible.

### 3.1 Required for a minimum computation (highlighted in the UI)
- **Name** (identity)
- **Asset class** (§2) — selects/filters eligible comparables
- **Currency** (ISO-4217) — representation & anchoring
- **At least one numeric metric** (see §3.2) — a holding with no metric cannot be placed in metric space

### 3.2 Metric inputs (optional; each one sharpens the match)
Numeric fundamentals used as **coordinates** in the comparison space (used when present):
- **Size / scale:** revenue, EBITDA, net income, (market value / NAV as a size anchor)
- **Profitability:** EBITDA margin, net margin *(derived from the above when both parts exist)*
- **Debt-specific:** expected yield, maturity/tenor, seniority, credit rating
- **Real-estate-specific:** occupancy rate, property type
- **Fund-specific:** strategy type, vintage year

### 3.3 Categorical inputs (optional filters that improve relevance)
- **Region / geography**, **sector / industry** — used to restrict comparables to the like-for-like part of the universe when populated.

### 3.4 Fund capital-call inputs (optional; commitment-based vehicles)
Private funds are **commitment-based**: an LP signs a Limited Partnership Agreement committing a total amount, but only a fraction is *paid in* (called) at any time — the remainder is *uncalled capital* subject to future capital calls (drawdowns) during the investment period. These inputs are optional and surfaced in a user-toggled section (relevant to fund/commitment vehicles):
- **Commitment** — total committed capital.
- **Paid-in (called to date)** — cumulative capital contributed. If a call schedule is supplied, paid-in defaults to the **sum of the calls**.
- **Capital-call line of credit** — a facility LPs use to bridge calls (a liquidity mitigant).
- **Capital-call schedule** — individual drawdowns, each with a **date, amount, and purpose** (each call's share of commitment is derived).

---

## 4. Proxy construction (the mapping logic)

A **deterministic, config-driven** pipeline (`engine/config/mappings.yaml`, versioned). Pure functions; data injected; no network calls inside the mapping core.

1. **Select metrics** — the configured comparison metrics that are *present* on the holding. (Absent optional metrics are simply dropped from the distance calculation and noted.)
2. **Transform & standardise** — size-like metrics (revenue/EBITDA/net income/market value) are **log-scaled** (they span orders of magnitude); every metric is then **z-scored** using the baseline universe's mean/σ so unlike units are comparable. Transform parameters are recorded for audit.
3. **Filter comparables (optional)** — restrict the baseline universe by sector and/or region per config. If too few remain, **relax** the filter (and record that the relaxation fired).
4. **Distance** — standardised **Euclidean distance** from the holding to each eligible traded asset over the selected metrics.
5. **Select the k nearest** comparables (config `k`, with a configured minimum).
6. **Weight** — convert distances to weights (default **inverse-distance**; softmax available), normalised to **sum to 100%**. This is the proxy basket.
7. **Proxy point** — the weighted average of the comparables' coordinates gives the proxy's implied position in metric space (used for the scatter view, §5).
8. **Confidence / coverage** — driven by (a) how many configured metrics were available, (b) how close the nearest comparables are, and (c) whether filters were relaxed → **high / medium / low**.

### 4.1 Weights, currency, determinism
- Basket weights are non-negative and sum to 100%.
- Each comparable carries its traded identifier and currency; currency mismatch versus the holding is preserved as genuine FX exposure (never silently dropped).
- Identical inputs + identical config version ⇒ identical proxy. The **config version** is stamped on every explanation object.

### 4.2 Fund capital calls — commitment-based exposure sizing

The proxy basket describes a fund's **market behaviour** (its factor/beta profile), and the comparable selection is **unaffected** by capital-call inputs — that stays driven by the fundamentals (§4). What capital calls change is the **notional the proxy behaviour is applied to**, because in a commitment-based fund only the *invested* capital is exposed to markets. The engine derives, deterministically:

| Quantity | Definition |
|---|---|
| **Paid-in** | explicit paid-in, else the sum of the capital-call schedule |
| **Uncalled commitment** | `commitment − paid-in` |
| **% called** | `paid-in ÷ commitment` |
| **Effective market exposure** | **NAV** if marked, else **paid-in** — the notional the proxy basket represents |
| **Net uncovered commitment** | `max(uncalled − capital-call line, 0)` — contingent liquidity not covered by a credit facility |
| **Each call's share** | `call amount ÷ commitment` |

**The key risk treatment:** *effective market exposure is sized to invested capital (NAV / paid-in), and uncalled commitment is treated as a **contingent liquidity obligation, not market exposure**.* Applying the proxy's market beta to the full commitment would overstate market risk; ignoring the uncalled portion would understate liquidity risk. The engine reports both figures explicitly so a risk team sees the market-exposed notional and the future funding obligation side by side. A capital-call line of credit reduces the *net uncovered* liquidity need but does not change market exposure.

These figures are attached to the proxy result (`capital_call`) and shown on the review screens whenever capital-call inputs are supplied; they are omitted entirely otherwise.

---

## 5. Explanation, visualisation, confidence, and override

The proxy is a **proposal, not a verdict.**

### 5.1 Explanation object (emitted per proxy)
- **Metrics used** and their transforms/standardisation.
- **Filters applied** (and any relaxation).
- **Comparables chosen** — each traded asset with its distance and weight.
- **Proxy composition** (weights) and the **implied proxy point**.
- **Confidence/coverage** flag and the **config version + timestamp**.

### 5.2 Scatter visualisation
Because every asset is a point in metric space, the construction is directly viewable: pick any two metrics as **x/y axes**; the **baseline traded assets** render as dots in one colour, and the **private holding and its constructed proxy** render in a highlighting colour. The comparables actually used (and their weights) are emphasised. Users can switch axes to inspect the fit from different metric pairs.

### 5.3 Human override
Accept · **edit weights** · **replace comparables** · reject. The proxy is a starting proposal; every override persists **who / when / why** with the before/after basket and the originating explanation object (audit trail).

---

## 6. Transforms relevant to the risk/analytics goal

- **Appraisal de-smoothing (recommended, standard public technique).** Private NAVs are appraisal-based and smoothed, understating volatility/beta. De-smoothing recovers a realistic return series before it is used to sanity-check a proxy. *Proposed Privé addition; see provenance note.*
- **NAV roll-forward (analytics continuity only).** Between NAV dates, the proxy's traded return series rolls the last reported NAV forward to give analytics a continuous path — explicitly an *estimated path, not a valuation*, always reconciled to the next reported NAV.

---

## 7. Limitations & failure modes

| Situation | Behaviour | Confidence |
|---|---|---|
| Unrecognised asset class | Manual mapping (reason recorded) | n/a |
| No numeric metric supplied | Cannot place in metric space → manual mapping | n/a |
| Only one metric supplied | Proxy built on a single axis | **Low** |
| Sparse baseline after filtering | Filter relaxed; recorded | Medium |
| Nearest comparables still far away | Proxy built but flagged | **Low** |
| Currency mismatch | Kept as FX exposure | as matched |
| Appraisal-smoothed history unadjusted | Volatility/beta understated; de-smoothing (§6) mitigates | risk noted |
| Uncalled fund commitment | Market exposure sized to invested capital (NAV/paid-in); uncalled reported as a **contingent liquidity obligation** (§4.2), not market risk | n/a |

**Caveats for a client risk team:** the proxy captures **systematic/market behaviour via comparables**, not deal-specific outcomes (a write-down, capital-call timing, manager alpha). Proxy quality is bounded by (a) the metrics the user can supply and (b) the breadth/quality of the baseline traded universe (in production, the EPC endpoint; in this prototype, a fetched sample of ~50 traded assets). Nothing here is a valuation.

---

## 8. End-to-end flow

```
Add private holding (name, class, currency, metrics — metrics optional)
        │  minimum: class + currency + >=1 metric
        ▼
Select comparison metrics present  ─►  transform + standardise (vs baseline universe)
        │
        ▼
Filter baseline by sector/region (optional; relax if sparse)
        │
        ▼
Distance -> k nearest traded comparables -> inverse-distance weights (sum 100%)
        │
        ▼
Proxy basket + implied proxy point + Explanation (metrics, comparables, weights, confidence, config version)
        │
        ▼
Review on scatter (switchable x/y metrics) -> Accept | Edit weights | Replace | Reject  -> persist override (who/when/why)
        │
        ▼
Proxy consumed by risk & portfolio analytics as a liquid basket
```
