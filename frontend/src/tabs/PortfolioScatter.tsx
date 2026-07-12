import { useEffect, useMemo, useState } from 'react'
import { api, type BaselineAsset, type Config, type MetricMap, type PrivateRecord } from '../api'
import { HoldingTooltip } from '../components/HoldingTooltip'
import { ScatterPanel } from '../components/ScatterPanel'
import type { ScatterSeries } from '../components/Scatter'

// Mirror of the engine's metric extraction, for plotting saved holdings without
// an extra round-trip per asset.
function metricsFromInput(inp: Record<string, any>): MetricMap {
  const n = (v: any) => (v === null || v === undefined || v === '' ? null : Number(v))
  const rev = n(inp.revenue), eb = n(inp.ebitda), ni = n(inp.net_income)
  const mv = n(inp.market_cap) ?? n(inp.last_nav), ey = n(inp.expected_yield)
  const m: MetricMap = {}
  if (rev != null && !Number.isNaN(rev)) m.revenue = rev
  if (eb != null && !Number.isNaN(eb)) m.ebitda = eb
  if (ni != null && !Number.isNaN(ni)) m.net_income = ni
  if (mv != null && !Number.isNaN(mv)) m.market_value = mv
  if (ey != null && !Number.isNaN(ey)) m.expected_yield = ey
  if (rev && eb != null) m.ebitda_margin = eb / rev
  if (rev && ni != null) m.net_margin = ni / rev
  return m
}

export function PortfolioScatter({ config, baseline }: { config: Config; baseline: BaselineAsset[] }) {
  const [records, setRecords] = useState<PrivateRecord[]>([])
  useEffect(() => {
    api.list().then((r) => setRecords(r.assets))
  }, [])

  const holdings = useMemo(
    () => records.map((r) => ({ record: r, metrics: metricsFromInput(r.input) })),
    [records],
  )

  const buildSeries = (x: string, y: string): ScatterSeries[] => [
    {
      name: 'Baseline', color: '#E2E8F0', r: 3, opacity: 0.7,
      points: baseline.map((a) => ({ x: a.metrics[x], y: a.metrics[y], label: a.name })),
    },
    {
      name: 'Private assets', color: '#0E3C5C', r: 6,
      points: holdings
        .filter((h) => x in h.metrics && y in h.metrics)
        .map((h) => ({ x: h.metrics[x], y: h.metrics[y], label: h.record.input.name, data: h.record })),
    },
  ]

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-primary">Private assets — metric map</h2>
        <p className="text-sm text-tertiary">
          Your private holdings ({holdings.length}) plotted against the traded universe. Switch the axes to compare on
          different metrics.
        </p>
      </div>

      {holdings.length === 0 ? (
        <p className="text-sm text-tertiary py-10 text-center">No private assets yet — add one to see it here.</p>
      ) : (
        <div className="rounded-lg border border-border bg-white p-5">
          <ScatterPanel
            availableAxes={config.scatter.available_axes}
            defaultX={config.scatter.default_x}
            defaultY={config.scatter.default_y}
            buildSeries={buildSeries}
            height={440}
            tooltip={(record: PrivateRecord) => <HoldingTooltip record={record} />}
            legend={[
              { name: 'Baseline (traded)', color: '#E2E8F0' },
              { name: 'Private assets', color: '#0E3C5C' },
            ]}
          />
        </div>
      )}
    </div>
  )
}
