import { useMemo, useState } from 'react'
import { formatMetric, type BaselineAsset } from '../api'

const COLS: { key: string; label: string; num?: boolean }[] = [
  { key: 'ticker', label: 'Ticker' },
  { key: 'name', label: 'Name' },
  { key: 'sector', label: 'Sector' },
  { key: 'region', label: 'Region' },
  { key: 'currency', label: 'CCY' },
  { key: 'revenue', label: 'Revenue', num: true },
  { key: 'ebitda', label: 'EBITDA', num: true },
  { key: 'net_income', label: 'Net income', num: true },
  { key: 'net_debt', label: 'Net debt', num: true },
  { key: 'market_value', label: 'Market value', num: true },
]

export function BaselineUniverse({ baseline }: { baseline: BaselineAsset[] }) {
  const [q, setQ] = useState('')
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    if (!needle) return baseline
    return baseline.filter(
      (a) =>
        a.name.toLowerCase().includes(needle) ||
        (a.ticker ?? '').toLowerCase().includes(needle) ||
        (a.sector ?? '').toLowerCase().includes(needle) ||
        (a.region ?? '').toLowerCase().includes(needle),
    )
  }, [baseline, q])

  return (
    <div>
      {/* Heads-up: what the baseline universe actually is. */}
      <div className="rounded-lg border border-secondary/30 bg-secondary/[0.06] px-4 py-3 mb-4 text-sm text-ink">
        <span className="font-semibold text-secondary">Heads-up — the baseline universe is client-specific.</span>{' '}
        In production this is the <span className="font-medium">investible universe available to the client</span>: it
        matches whatever market-data subscription they hold, so the pool of eligible proxies changes from client to
        client. The list shown here is <span className="font-medium">illustrative prototype ("dummy") data</span> and is
        not a fixed or recommended universe — each deployment is wired to the client's own EPC feed.
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-primary">Baseline traded universe</h2>
          <p className="text-sm text-tertiary">
            The pool of liquid comparables used to construct proxies.{' '}
            <span className="font-medium">Prototype sample of {baseline.length} assets</span> — in production this is
            sourced from the EPC endpoint.
          </p>
        </div>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-tertiary">⌕</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, ticker, sector…"
            className="w-72 rounded-full border border-border bg-white pl-8 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-secondary"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {COLS.map((c) => (
                <th
                  key={c.key}
                  className={`px-3 py-2.5 text-[11px] uppercase tracking-wide text-tertiary font-medium ${c.num ? 'text-right' : 'text-left'}`}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-b border-border last:border-0 hover:bg-neutral">
                <td className="px-3 py-2 font-medium text-secondary">{a.ticker}</td>
                <td className="px-3 py-2">{a.name}</td>
                <td className="px-3 py-2 text-tertiary">{a.sector}</td>
                <td className="px-3 py-2 text-tertiary">{a.region}</td>
                <td className="px-3 py-2 text-tertiary">{a.currency}</td>
                {(['revenue', 'ebitda', 'net_income', 'net_debt', 'market_value'] as const).map((m) => (
                  <td key={m} className="px-3 py-2 text-right tnum">
                    {formatMetric(m, a.metrics[m])}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={COLS.length} className="px-3 py-8 text-center text-tertiary">
                  No assets match “{q}”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
