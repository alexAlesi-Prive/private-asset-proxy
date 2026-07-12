# Provenance Note — Proxy-Asset Methodology

**Purpose:** flag, for human/legal review, which parts of the methodology are standard/public technique versus anything that may be a third-party work product. **This note does not assert Privé holds rights to anything — it surfaces items for confirmation.**

1. **Privé's construction is standard/public technique.** The proxy is built by **comparable-company / nearest-neighbour approximation in standardised metric space** — i.e. compare a holding's fundamentals (revenue, EBITDA, net income, margins, yield, etc.) to traded assets described by the same metrics and take the closest as a weighted basket. Comparables/"multiples" analysis, standardisation (z-scoring), log-scaling of size variables, and nearest-neighbour weighting are all textbook, widely used methods. This is safe to implement in Privé's own code.

2. **No third-party factor library is used — a cleaner IP position than a factor-model approach.** Privé deliberately does **not** depend on a curated library of named risk factors or any calibrated factor→index weight tables. That removes the two items previously flagged for licensing/clean-room review (proprietary factor calibrations, and commercial index-data licences for a named-factor library). The "factors" here are simply the client-supplied input metrics.

3. **Interfaces only were observed from the reference material — not internal algorithms.** Any comparable-scoring / selection logic is Privé's own; nothing proprietary was reproduced.

4. **Prototype baseline data — confirm before production.** In this prototype the baseline universe of traded assets is an **illustrative sample of ~50 public companies with representative fundamentals**, assembled for demonstration. It is **not** licensed market data. For production this universe is sourced from the **EPC endpoint**; confirm data/market-data licensing for whatever real universe ships.

5. **De-smoothing / NAV roll-forward** (§6 of the methodology) are published academic/industry methods; de-smoothing is a proposed Privé addition, not extracted from the reference.

6. **Branding:** all former-employer and legacy product names are scrubbed from Privé's authored artifacts; the method is re-expressed in Privé's own words and public technique. Any client-specific data in the reference material is not reused.

**Recommended action:** legal/compliance to confirm (a) market-data licensing for the production baseline universe delivered via EPC, and (b) that the re-implemented comparable-construction code is clean-room relative to the reference material (reference-only, slated for deletion).
