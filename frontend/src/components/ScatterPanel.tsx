import { useState, type ReactNode } from 'react'
import { LOG_METRICS, formatMetric, metricLabel } from '../api'
import { Scatter, type ScatterSeries } from './Scatter'

interface LegendItem { name: string; color: string; shape?: 'circle' | 'diamond' | 'ring' }

interface Props {
  availableAxes: string[]
  defaultX: string
  defaultY: string
  buildSeries: (x: string, y: string) => ScatterSeries[]
  legend: LegendItem[]
  height?: number
  tooltip?: (data: any) => ReactNode
}

function AxisSelect({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-tertiary uppercase text-[11px] tracking-wide font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-secondary"
      >
        {options.map((o) => (
          <option key={o} value={o}>{metricLabel(o)}</option>
        ))}
      </select>
    </label>
  )
}

export function ScatterPanel({ availableAxes, defaultX, defaultY, buildSeries, legend, height, tooltip }: Props) {
  const [x, setX] = useState(defaultX)
  const [y, setY] = useState(defaultY)
  const series = buildSeries(x, y)

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4 mb-3">
        <AxisSelect label="X axis" value={x} options={availableAxes} onChange={setX} />
        <AxisSelect label="Y axis" value={y} options={availableAxes} onChange={setY} />
        <div className="flex flex-wrap items-center gap-3 ml-auto">
          {legend.map((l) => (
            <span key={l.name} className="flex items-center gap-1.5 text-xs text-tertiary">
              <span
                className="inline-block"
                style={{
                  width: 10, height: 10, background: l.shape === 'ring' ? 'transparent' : l.color,
                  border: l.shape === 'ring' ? `2px solid ${l.color}` : 'none',
                  borderRadius: l.shape === 'diamond' ? 2 : 999,
                  transform: l.shape === 'diamond' ? 'rotate(45deg)' : 'none',
                }}
              />
              {l.name}
            </span>
          ))}
        </div>
      </div>
      <Scatter
        series={series}
        xMetric={x}
        yMetric={y}
        logX={LOG_METRICS.has(x)}
        logY={LOG_METRICS.has(y)}
        format={formatMetric}
        height={height}
        tooltip={tooltip}
      />
    </div>
  )
}
