# EPC Data Contract & Gap Analysis

**Phase 1 deliverable.** Defines the input the Proxy-Asset engine consumes from Privé's **EPC** holdings source, the field types, and a gap analysis against what the methodology (Phase 0) needs.

---

## 0. Discovery status — read first

> **A live EPC endpoint could not be reached from this build environment.** There is no EPC URL configured here, the `EPC_ACCESS` credential (`prive4demo`) has no bound endpoint available to this session, and there is no public EPC API schema to introspect. Per the Phase-1 fallback ("if only a sample export is available, use that"), the contract below is **derived from the concrete private-holding shapes evidenced in the available sample material** and from the field set the engine's proxy logic actually consumes.
>
> **Every EPC-side claim in this document is therefore marked _sample-derived / unconfirmed against live EPC_.** The adapter (`engine/adapters/epc_adapter.py`) isolates these assumptions: when a real EPC endpoint or export is provided, **only the adapter's field-mapping table changes** — the engine's typed model and all downstream logic stay put. **This document should be confirmed against a live EPC export before client delivery** (see the open question at the end of Phase 1).

Confidence legend used below:
- **Evidenced** — the field is present in sample holding records and/or is a field the proxy engine already consumes.
- **Inferred** — the methodology needs it and it is standard for such a holdings feed, but it was not directly observed; confirm with EPC.
- **Unknown** — not observed; may or may not exist in EPC.

---

## 1. Ingestion model

EPC is treated as a **read-only holdings source**. The engine ingests a set of **holding records**; the private/illiquid subset (those keyed as *internal* rather than exchange-traded/cash) is what the proxy engine acts on.

- A **holding record** carries identity, classification, reporting currency, valuation (last NAV + date), and — for private holdings — a set of **fundamentals** appropriate to its asset class.
- Liquid holdings (exchange-traded, identified by ISIN/OCC, or cash) pass through untouched; they are already analytics-ready and are also the **universe of candidate proxies**.
- The engine never writes back to EPC.

### Holding key
| Field | Type | Confidence | Notes |
|---|---|---|---|
| `key_type` | enum: `Internal` \| `ExchangeTraded` \| `Cash` | Evidenced | `Internal` ⇒ private/illiquid (proxy candidates). |
| `symbol_type` | string (e.g. `INTERNAL`, `ISIN`, `OCC`) | Evidenced | Identifier namespace. |
| `symbol` | string | Evidenced | Unique within `symbol_type`. Used as the holding id. |
| `name` | string | Evidenced | Human-readable holding name. |

---

## 2. Input schema (per private holding)

Field **types** are the engine's canonical types (post-adapter). The **EPC source field** column is the sample-derived name the adapter maps from; confirm against live EPC.

### 2.1 Common / anchoring fields (all private classes)

| Canonical field | Type | EPC source (sample-derived) | Confidence | Methodology use |
|---|---|---|---|---|
| `holding_id` | string | `Symbol` / `id` | Evidenced | Identity, audit key |
| `name` | string | `Name` | Evidenced | Display, reporting |
| `asset_class` | enum (§3) | `Asset_Class` (+ `Sub_Asset_Class`) | Evidenced | Selects mapping tier & required inputs |
| `currency` | ISO-4217 string | `Risk_CCY` / `reportingCurrency` | Evidenced | Currency/FX representation, anchoring |
| `region` | string (region or ISO country) | `Region` | Evidenced | Comparable filter, class basket |
| `sector` | string | `Sector` | Evidenced | Comparable filter, class basket |
| `last_nav` | number (in `currency`) | position value / NAV | **Inferred** | Anchoring, roll-forward, **validation** |
| `last_nav_date` | date (ISO-8601) | valuation date | **Inferred** | Roll-forward start, staleness, validation |
| `leverage` | number (ratio) | `Leverage` | **Inferred** | Risk scaling (observed as a position attribute) |

### 2.2 Class-specific fundamentals (drive the mapping)

These are the exact inputs the proxy logic consumes, by class:

| Canonical field | Type | Applies to | Confidence |
|---|---|---|---|
| `industry_group` | string | Direct PE, Direct PD | Evidenced |
| `revenue` | number (`currency`) | Direct PE, Direct RE | Evidenced |
| `ebitda` | number (`currency`) | Direct PE, Direct RE | Evidenced |
| `net_income` | number (`currency`) | Direct PE, Direct RE | Evidenced |
| `expected_yield` | number (decimal, e.g. 0.065) | Direct PD | Evidenced |
| `maturity` | date or tenor (years) | Direct PD | Evidenced |
| `seniority` | string (e.g. Senior/Subordinated) | Direct PD | Evidenced |
| `credit_rating` | string (e.g. BBB) | Direct PD | Evidenced |
| `occupancy_rate` | number (decimal 0–1) | Direct RE | Evidenced |
| `property_type` | string | Direct RE | Evidenced |
| `strategy_type` | string | PE Fund, PD Fund, RE Fund, Hedge Fund | Evidenced |

### 2.3 Fund-economics fields the methodology *wants* but were not observed

Relevant to fund-type holdings and to validation/roll-forward; **confirm availability in EPC**:

| Canonical field | Type | Confidence | Why we want it |
|---|---|---|---|
| `vintage_year` | integer | Unknown | Sharpens fund class mapping & de-smoothing window |
| `commitment` / `drawn` / `nav_history` | numbers / series | Unknown | Roll-forward accuracy; validation vs realised NAV path |
| `gav` / `net_leverage` | number | Unknown | RE / fund risk scaling |

---

## 3. Asset-class enumeration & required inputs

Mirrors the methodology's supported classes. **Mandatory** inputs must be present or the holding is routed to manual mapping (Phase 0 §7).

| `asset_class` (canonical) | Mandatory inputs | Optional / sharpening inputs |
|---|---|---|
| `DIRECT_PRIVATE_EQUITY` | region, sector | industry_group, revenue, ebitda, net_income, currency |
| `DIRECT_PRIVATE_DEBT` | region, sector | industry_group, expected_yield, maturity, seniority, credit_rating, currency |
| `DIRECT_REAL_ESTATE` | region | revenue, ebitda, net_income, occupancy_rate, property_type, currency |
| `PRIVATE_EQUITY_FUND` | region, sector, strategy_type | — |
| `PRIVATE_DEBT_FUND` | region, sector, strategy_type | — |
| `REAL_ESTATE_FUND` | region, strategy_type | — |
| `HEDGE_FUND` | strategy_type | — |

---

## 4. Gap analysis — methodology need vs EPC availability

For each input the Phase-0 methodology needs, the availability against EPC (**sample-derived, unconfirmed**) is marked `available` / `partial` / `missing`. This bounds how good the proxy can be.

| Methodology input | Needed for | Availability (sample-derived) | Consequence if absent |
|---|---|---|---|
| Asset class | Tier selection, required-input check | **available** | Cannot map at all → manual |
| Region | Tier-1 comparable filter, Tier-3 basket | **available** | Fall back to non-regional class basket |
| Sector | Tier-1 comparable filter | **available** (direct/funds) | Broader, less precise match |
| Reporting currency | FX representation, anchoring | **available** | FX exposure mis-stated |
| Industry group | Tier-1 sharpening (PE/PD) | **available** | Slightly coarser comparable |
| Revenue / EBITDA / Net income | Tier-1 comparable scoring (PE/RE) | **partial** — schema exists, values often sparse | Drops to class/region match; lower confidence |
| Expected yield / Maturity / Seniority / Credit rating | Tier-1 comparable scoring (PD) | **partial** — schema exists, values often sparse | Coarser credit proxy |
| Occupancy / Property type | Tier-1 sharpening (RE) | **partial** | Coarser RE proxy |
| Strategy type | Required for all fund/HF classes | **partial** — mandatory but not always populated | Fund/HF holdings rejected to manual if blank |
| Last NAV + date | Anchoring, roll-forward, **validation** | **partial** — value present at position level; explicit date **inferred** | No validation backtest; roll-forward disabled |
| Leverage | Risk scaling | **partial** | Risk under/over-stated for levered holdings |
| Vintage / commitment / NAV history | Roll-forward & validation quality | **missing** (unconfirmed) | Validation limited to point checks |

**Headline read:** classification fields (class, region, sector, currency) look **reliably available**, so *every* in-scope holding can get at least a Tier-3 class-basket proxy. The **fundamentals and NAV-history** fields are the swing factor — where they are populated, Tier-1/Tier-2 high-confidence proxies are achievable; where they are sparse, the engine degrades gracefully to lower-confidence class proxies and flags it. **Confirming NAV-with-date and fundamental coverage in live EPC is the single highest-value discovery step** and directly determines the validation report (Phase 3).

---

## 5. Decoupling (adapter pattern)

- The engine depends only on the **canonical typed model** (`engine/models/private_holding.py`) via the **`HoldingSource` port** (`engine/adapters/holding_source.py`).
- **`EpcAdapter`** (`engine/adapters/epc_adapter.py`) maps raw EPC records → canonical model using an explicit, single-source-of-truth **field-mapping table**. Unmapped source fields are preserved verbatim in `raw` for audit and future use.
- **When live EPC is available, change only the mapping table** (and, if needed, a fetch implementation). No engine, config, validation, or UI code changes. This is the guarantee that "EPC changes don't ripple into the engine."

```
EPC (raw records) ──► EpcAdapter (field map) ──► PrivateHolding (typed) ──► engine
                       ▲ only this changes when EPC's real shape is known
```

---

## 6. Open question for confirmation (Phase-1 checkpoint)

Because no live EPC endpoint was reachable, confirm how EPC discovery should be finalised:
1. Provide a **live EPC endpoint** the session can call with `prive4demo`, or
2. Provide a **real EPC export** (one private holding record is enough to lock field names/types), or
3. **Proceed on this sample-derived contract** as the working assumption, with the adapter mapping revised when real EPC data arrives.

The typed model and adapter are built either way; only the adapter's mapping table and the availability column above depend on the answer.
