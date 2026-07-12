import { metricLabel, type BaselineAsset, type Config, type Proxy } from '../api'
import { CapitalCallCard } from './CapitalCallCard'
import { ConfidenceChip } from './Chip'
import { ScatterPanel } from './ScatterPanel'
import type { ScatterSeries } from './Scatter'

// Read-only view of a constructed proxy: the metric-space scatter (baseline,
// comparables, holding, proxy point) plus the basket composition.
export function ProxyView({ proxy, baseline, config }: {
  proxy: Proxy; baseline: BaselineAsset[]; config: Config
}) {
  if (proxy.status !== 'constructed') {
    return (
      <div>
        <p className="text-sm text-danger py-2">{proxy.reason ?? proxy.status}</p>
        {proxy.capital_call && <div className="mt-2"><CapitalCallCard cc={proxy.capital_call} /></div>}
      </div>
    )
  }

  const hasCapitalCall = !!proxy.capital_call

  const comparableIds = new Set(proxy.comparables.map((c) => c.asset_id))
  const weightById = new Map(proxy.comparables.map((c) => [c.asset_id, c.weight]))

  const buildSeries = (x: string, y: string): ScatterSeries[] => {
    const series: ScatterSeries[] = [
      {
        name: 'Baseline', color: '#CBD5E1', r: 3, opacity: 0.75,
        points: baseline.filter((a) => !comparableIds.has(a.id))
          .map((a) => ({ x: a.metrics[x], y: a.metrics[y], label: a.name })),
      },
      {
        name: 'Comparables', color: '#1F6FA8',
        points: proxy.comparables.map((c) => ({
          x: c.metrics[x], y: c.metrics[y], label: `${c.name} · ${(c.weight * 100).toFixed(1)}%`,
          r: 4 + (weightById.get(c.asset_id) ?? 0) * 22,
        })),
      },
    ]
    if (x in proxy.holding_metrics && y in proxy.holding_metrics)
      series.push({
        name: 'This holding', color: '#0E3C5C', shape: 'ring', r: 8,
        points: [{ x: proxy.holding_metrics[x], y: proxy.holding_metrics[y], label: proxy.holding_name }],
      })
    if (x in proxy.proxy_point && y in proxy.proxy_point)
      series.push({
        name: 'Constructed proxy', color: '#5FC08D', shape: 'diamond', r: 7,
        points: [{ x: proxy.proxy_point[x], y: proxy.proxy_point[y], label: 'Constructed proxy' }],
      })
    return series
  }

  return (
    <div>
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm mb-3">
        <span className="flex items-center gap-2 text-tertiary">confidence <ConfidenceChip value={proxy.confidence} /></span>
        <span className="text-tertiary">coverage <strong className="text-ink">{Math.round((proxy.coverage ?? 0) * 100)}%</strong></span>
        <span className="text-tertiary">metrics <strong className="text-ink">{proxy.metrics_used.map(metricLabel).join(', ')}</strong></span>
        {proxy.filters_relaxed && <span className="text-danger">filters relaxed</span>}
      </div>

      <div className={hasCapitalCall ? 'grid lg:grid-cols-2 gap-6 items-start' : ''}>
        {/* left: scatter + basket */}
        <div>
          <ScatterPanel
            availableAxes={config.scatter.available_axes}
            defaultX={config.scatter.default_x}
            defaultY={config.scatter.default_y}
            buildSeries={buildSeries}
            height={320}
            legend={[
              { name: 'Baseline', color: '#CBD5E1' },
              { name: 'Comparables', color: '#1F6FA8' },
              { name: 'This holding', color: '#0E3C5C', shape: 'ring' },
              { name: 'Proxy', color: '#5FC08D', shape: 'diamond' },
            ]}
          />
          <h3 className="text-sm font-semibold text-primary mt-4 mb-1">Basket composition</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-[11px] uppercase tracking-wide text-tertiary">
                  <th className="text-left py-1.5 pr-2">Weight</th>
                  <th className="text-left py-1.5 pr-2">Comparable</th>
                  <th className="text-left py-1.5 pr-2">Sector</th>
                  <th className="text-right py-1.5">Distance</th>
                </tr>
              </thead>
              <tbody>
                {proxy.comparables.map((c) => (
                  <tr key={c.asset_id} className="border-b border-border last:border-0">
                    <td className="py-1.5 pr-2 tnum font-medium text-secondary">{(c.weight * 100).toFixed(1)}%</td>
                    <td className="py-1.5 pr-2">{c.name} <span className="text-tertiary">({c.ticker})</span></td>
                    <td className="py-1.5 pr-2 text-tertiary">{c.sector}</td>
                    <td className="py-1.5 text-right tnum text-tertiary">{c.distance.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* right: capital call, next to the scatter */}
        {hasCapitalCall && (
          <div className="mt-6 lg:mt-0">
            <CapitalCallCard cc={proxy.capital_call!} />
          </div>
        )}
      </div>

      <p className="text-[11px] text-tertiary mt-3">Config v{proxy.config_version} · generated {new Date(proxy.generated_at).toLocaleString()}</p>
    </div>
  )
}
