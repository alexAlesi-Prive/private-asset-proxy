import { useEffect, useState } from 'react'
import { api, type Backtest as BacktestData } from '../api'

// Out-of-sample validation. Hold out traded assets, treat each as private, build
// a proxy from the rest, and measure realised tracking error / correlation vs the
// asset's own return series. Answers the model-validation question the white
// paper previously left open.
export function Backtest() {
  const [data, setData] = useState<BacktestData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.backtest().then(setData).catch((e) => setError(String(e)))
  }, [])

  if (error) return <p className="text-sm text-danger py-10 text-center">Could not run the backtest: {error}</p>
  if (!data) return <p className="text-sm text-tertiary py-16 text-center">Running out-of-sample backtest…</p>

  const a = data.aggregate
  return (
    <div className="max-w-5xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-primary">Out-of-sample backtest</h2>
        <p className="text-sm text-tertiary">
          {data.n_tested} traded assets held out one at a time, treated as private, and proxied from the rest of the
          universe. We then compare each proxy basket's realised returns to the asset's own - a genuine out-of-sample
          test over {data.periods} monthly periods.
        </p>
      </div>

      {/* Illustrative-data disclosure - do not overclaim. */}
      <div className="rounded-lg border border-secondary/30 bg-secondary/[0.06] px-4 py-3 mb-5 text-sm text-ink">
        <span className="font-semibold text-secondary">Illustrative returns.</span>{' '}
        Return series in this prototype are <span className="font-medium">simulated</span> from a transparent
        market + sector + single-name factor model, so the harness and its statistics can be demonstrated end to end.
        In production the identical backtest runs on the client's <span className="font-medium">real return history</span>;
        only the data source changes. By construction the <span className="font-medium">systematic</span> (market/sector)
        component is capturable by comparables while <span className="font-medium">single-name idiosyncratic</span> risk
        is not - which is exactly what a proxy is meant to represent.
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <Tile label="Median tracking error" value={pct(a.median_tracking_error)} tone="ink" hint="annualised" />
        <Tile label="Mean tracking error" value={pct(a.mean_tracking_error)} tone="ink" hint="annualised" />
        <Tile label="Median correlation" value={num(a.median_correlation)} tone="good" hint="proxy vs actual" />
        <Tile label="Median R²" value={num(a.median_r2)} tone="good" hint="variance explained" />
        <Tile label="Mean beta" value={num(a.mean_beta)} tone="ink" hint="actual on proxy" />
        <Tile label="Assets tested" value={String(data.n_tested)} tone="muted" hint={`${data.periods} periods`} />
      </div>

      <div className="rounded-lg border border-border bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-[11px] uppercase tracking-wide text-tertiary">
              <th className="text-left px-3 py-2.5">Held-out asset</th>
              <th className="text-left px-3 py-2.5">Sector</th>
              <th className="text-right px-3 py-2.5">Tracking error</th>
              <th className="text-right px-3 py-2.5">Correlation</th>
              <th className="text-right px-3 py-2.5">R²</th>
              <th className="text-right px-3 py-2.5">Beta</th>
              <th className="text-right px-3 py-2.5">Vol (actual / proxy)</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r) => (
              <tr key={r.asset_id} className="border-b border-border last:border-0 hover:bg-neutral">
                <td className="px-3 py-2">{r.name} <span className="text-tertiary">({r.ticker})</span></td>
                <td className="px-3 py-2 text-tertiary">{r.sector}</td>
                <td className="px-3 py-2 text-right tnum">{pct(r.tracking_error)}</td>
                <td className="px-3 py-2 text-right tnum">{num(r.correlation)}</td>
                <td className="px-3 py-2 text-right tnum">{num(r.r2)}</td>
                <td className="px-3 py-2 text-right tnum">{num(r.beta)}</td>
                <td className="px-3 py-2 text-right tnum text-tertiary">{pct(r.vol_actual)} / {pct(r.vol_proxy)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-tertiary mt-3">{data.note} Config v{data.config_version}.</p>
    </div>
  )
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}
function num(v: number): string {
  return v.toFixed(2)
}

function Tile({ label, value, hint, tone }: {
  label: string; value: string; hint?: string; tone: 'ink' | 'good' | 'muted'
}) {
  const color = tone === 'good' ? 'text-success' : tone === 'muted' ? 'text-tertiary' : 'text-primary'
  return (
    <div className="rounded-lg border border-border bg-white p-3">
      <div className="text-[10px] uppercase tracking-wide text-tertiary font-semibold">{label}</div>
      <div className={`text-xl font-semibold tnum mt-1 ${color}`}>{value}</div>
      {hint && <div className="text-[10px] text-tertiary mt-0.5">{hint}</div>}
    </div>
  )
}
