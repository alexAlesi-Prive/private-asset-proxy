"""Generator for the prototype baseline universe (engine/data/baseline_universe.json).

PROTOTYPE DATA — NOT LICENSED MARKET DATA. These ~50 well-known public
companies carry *illustrative, rounded* fundamentals (USD millions) assembled
only to demonstrate the comparable-construction engine and its scatter view. In
production this universe is replaced by the EPC endpoint (see docs/provenance-note.md).

Financials are stored in a common currency (USD mn) so size metrics are
comparable across listings; `currency` is the listing currency (display only).

Run: python3 -m engine.data._build_baseline
"""
from __future__ import annotations

import json
from pathlib import Path

# (name, ticker, sector, region, currency, revenue, ebitda, net_income, market_cap)  [USD mn]
_COMPANIES = [
    # --- Technology (US) ---
    ("Apple", "AAPL", "Technology", "US", "USD", 391000, 134000, 97000, 3300000),
    ("Microsoft", "MSFT", "Technology", "US", "USD", 245000, 128000, 88000, 3100000),
    ("Alphabet", "GOOGL", "Communication Services", "US", "USD", 350000, 120000, 100000, 2100000),
    ("NVIDIA", "NVDA", "Technology", "US", "USD", 130000, 82000, 73000, 3200000),
    ("Meta Platforms", "META", "Communication Services", "US", "USD", 156000, 78000, 62000, 1300000),
    ("Oracle", "ORCL", "Technology", "US", "USD", 53000, 22000, 10000, 380000),
    ("Adobe", "ADBE", "Technology", "US", "USD", 21500, 9500, 5900, 230000),
    ("Salesforce", "CRM", "Technology", "US", "USD", 37900, 10500, 6200, 300000),
    ("Advanced Micro Devices", "AMD", "Technology", "US", "USD", 25800, 5200, 1600, 260000),
    ("Intel", "INTC", "Technology", "US", "USD", 53000, 8000, -1600, 90000),
    # --- Consumer / Comms (US) ---
    ("Amazon", "AMZN", "Consumer Discretionary", "US", "USD", 638000, 111000, 59000, 2300000),
    ("Netflix", "NFLX", "Communication Services", "US", "USD", 39000, 10500, 8700, 380000),
    ("Walt Disney", "DIS", "Communication Services", "US", "USD", 91000, 15500, 5000, 200000),
    ("Coca-Cola", "KO", "Consumer Staples", "US", "USD", 46000, 15000, 10700, 270000),
    ("PepsiCo", "PEP", "Consumer Staples", "US", "USD", 92000, 18000, 9600, 210000),
    ("McDonald's", "MCD", "Consumer Discretionary", "US", "USD", 26000, 14000, 8800, 210000),
    ("Nike", "NKE", "Consumer Discretionary", "US", "USD", 48000, 7200, 5200, 110000),
    ("Starbucks", "SBUX", "Consumer Discretionary", "US", "USD", 36000, 6500, 3800, 110000),
    # --- Healthcare (US) ---
    ("Johnson & Johnson", "JNJ", "Healthcare", "US", "USD", 88000, 28000, 14000, 360000),
    ("Pfizer", "PFE", "Healthcare", "US", "USD", 63000, 17000, 8000, 150000),
    ("Merck & Co", "MRK", "Healthcare", "US", "USD", 64000, 22000, 14500, 250000),
    ("UnitedHealth Group", "UNH", "Healthcare", "US", "USD", 400000, 32000, 15000, 480000),
    ("AbbVie", "ABBV", "Healthcare", "US", "USD", 56000, 22000, 4800, 320000),
    ("Eli Lilly", "LLY", "Healthcare", "US", "USD", 45000, 16000, 10600, 780000),
    # --- Financials (US) ---
    ("JPMorgan Chase", "JPM", "Financials", "US", "USD", 158000, 68000, 49000, 660000),
    ("Bank of America", "BAC", "Financials", "US", "USD", 101000, 40000, 27000, 320000),
    ("Visa", "V", "Financials", "US", "USD", 36000, 25000, 19000, 560000),
    ("Mastercard", "MA", "Financials", "US", "USD", 28000, 17000, 12600, 460000),
    ("Goldman Sachs", "GS", "Financials", "US", "USD", 53000, 20000, 12000, 170000),
    # --- Industrials / Energy (US) ---
    ("Caterpillar", "CAT", "Industrials", "US", "USD", 64000, 14500, 10300, 175000),
    ("Boeing", "BA", "Industrials", "US", "USD", 78000, -1500, -8000, 130000),
    ("General Electric", "GE", "Industrials", "US", "USD", 38000, 6800, 4400, 200000),
    ("Exxon Mobil", "XOM", "Energy", "US", "USD", 340000, 65000, 34000, 480000),
    ("Chevron", "CVX", "Energy", "US", "USD", 200000, 42000, 21000, 280000),
    # --- Europe ---
    ("Nestle", "NESN", "Consumer Staples", "CH", "CHF", 103000, 20000, 12000, 250000),
    ("Novartis", "NOVN", "Healthcare", "CH", "CHF", 50000, 18000, 12000, 220000),
    ("Roche", "ROG", "Healthcare", "CH", "CHF", 66000, 24000, 13000, 240000),
    ("LVMH", "MC", "Consumer Discretionary", "FR", "EUR", 90000, 27000, 15000, 340000),
    ("SAP", "SAP", "Technology", "DE", "EUR", 37000, 9500, 5500, 260000),
    ("Siemens", "SIE", "Industrials", "DE", "EUR", 82000, 13000, 9000, 160000),
    ("ASML", "ASML", "Technology", "NL", "EUR", 30000, 11000, 8000, 320000),
    ("Shell", "SHEL", "Energy", "GB", "GBP", 290000, 55000, 20000, 220000),
    ("AstraZeneca", "AZN", "Healthcare", "GB", "GBP", 52000, 17000, 7000, 210000),
    ("Unilever", "ULVR", "Consumer Staples", "GB", "GBP", 64000, 12000, 7000, 130000),
    ("TotalEnergies", "TTE", "Energy", "FR", "EUR", 210000, 45000, 18000, 150000),
    # --- Asia ---
    ("Taiwan Semiconductor", "TSM", "Technology", "TW", "TWD", 90000, 55000, 36000, 900000),
    ("Samsung Electronics", "005930", "Technology", "KR", "KRW", 200000, 45000, 22000, 370000),
    ("Toyota Motor", "7203", "Consumer Discretionary", "JP", "JPY", 310000, 48000, 32000, 280000),
    ("Sony Group", "6758", "Technology", "JP", "JPY", 88000, 15000, 8000, 120000),
    ("Tencent", "0700", "Communication Services", "CN", "HKD", 90000, 38000, 22000, 450000),
]


def build() -> list[dict]:
    assets = []
    for name, ticker, sector, region, currency, rev, ebitda, ni, mcap in _COMPANIES:
        assets.append({
            "id": ticker,
            "name": name,
            "ticker": ticker,
            "isin": None,
            "asset_class": "PublicEquity",
            "sector": sector,
            "region": region,
            "currency": currency,
            "revenue": rev,
            "ebitda": ebitda,
            "net_income": ni,
            "market_cap": mcap,
        })
    return assets


def main() -> int:
    out = Path(__file__).resolve().parent / "baseline_universe.json"
    assets = build()
    payload = {
        "_note": "PROTOTYPE illustrative data (USD millions); replaced by EPC in production.",
        "count": len(assets),
        "assets": assets,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(assets)} baseline assets to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
