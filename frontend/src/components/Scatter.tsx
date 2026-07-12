// Dependency-free SVG scatter plot. Renders assets as points in a 2-metric
// space; size metrics use a signed-log axis (they span orders of magnitude).
// Points carrying `data` get a rich hover card via the `tooltip` render prop.
import { useMemo, useState, type ReactNode } from 'react'

export interface ScatterPoint {
  x: number
  y: number
  label: string
  r?: number
  data?: unknown // when set (+ a `tooltip` prop), hovering shows a custom card
}

export interface ScatterSeries {
  name: string
  color: string
  points: ScatterPoint[]
  shape?: 'circle' | 'diamond' | 'ring'
  r?: number
  opacity?: number
}

interface Props {
  series: ScatterSeries[]
  xMetric: string
  yMetric: string
  logX?: boolean
  logY?: boolean
  format: (metric: string, v: number) => string
  height?: number
  tooltip?: (data: any) => ReactNode
}

const W = 760
const PAD = { l: 66, r: 18, t: 14, b: 46 }

const slog10 = (v: number) => Math.sign(v) * Math.log10(1 + Math.abs(v))
const invSlog10 = (t: number) => Math.sign(t) * (Math.pow(10, Math.abs(t)) - 1)

type Hover = { data: unknown; mx: number; my: number }

export function Scatter({ series, xMetric, yMetric, logX, logY, format, height = 380, tooltip }: Props) {
  const H = height
  const [hover, setHover] = useState<Hover | null>(null)
  const tX = logX ? slog10 : (v: number) => v
  const tY = logY ? slog10 : (v: number) => v
  const invX = logX ? invSlog10 : (v: number) => v
  const invY = logY ? invSlog10 : (v: number) => v

  const { xmin, xmax, ymin, ymax } = useMemo(() => {
    const xs: number[] = []
    const ys: number[] = []
    for (const s of series)
      for (const p of s.points)
        if (Number.isFinite(p.x) && Number.isFinite(p.y)) {
          xs.push(tX(p.x))
          ys.push(tY(p.y))
        }
    const span = (arr: number[]) => {
      if (!arr.length) return [0, 1]
      let lo = Math.min(...arr)
      let hi = Math.max(...arr)
      if (lo === hi) { lo -= 1; hi += 1 }
      const pad = (hi - lo) * 0.06
      return [lo - pad, hi + pad]
    }
    const [xmin, xmax] = span(xs)
    const [ymin, ymax] = span(ys)
    return { xmin, xmax, ymin, ymax }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series, xMetric, yMetric, logX, logY])

  const px = (v: number) => PAD.l + ((tX(v) - xmin) / (xmax - xmin)) * (W - PAD.l - PAD.r)
  const py = (v: number) => H - PAD.b - ((tY(v) - ymin) / (ymax - ymin)) * (H - PAD.t - PAD.b)

  const ticks = 5
  const xTicks = Array.from({ length: ticks }, (_, i) => xmin + ((xmax - xmin) * i) / (ticks - 1))
  const yTicks = Array.from({ length: ticks }, (_, i) => ymin + ((ymax - ymin) * i) / (ticks - 1))

  const flipX = hover ? hover.mx > window.innerWidth - 300 : false
  const flipY = hover ? hover.my > window.innerHeight - 260 : false

  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${xMetric} vs ${yMetric} scatter`}>
        {/* gridlines + axis labels */}
        {yTicks.map((t, i) => (
          <g key={`y${i}`}>
            <line x1={PAD.l} x2={W - PAD.r} y1={py(invY(t))} y2={py(invY(t))} stroke="#E2E8F0" strokeWidth={1} />
            <text x={PAD.l - 8} y={py(invY(t)) + 3} textAnchor="end" fontSize={10} fill="#64748B" className="tnum">
              {format(yMetric, invY(t))}
            </text>
          </g>
        ))}
        {xTicks.map((t, i) => (
          <g key={`x${i}`}>
            <line x1={px(invX(t))} x2={px(invX(t))} y1={PAD.t} y2={H - PAD.b} stroke="#F1F5F9" strokeWidth={1} />
            <text x={px(invX(t))} y={H - PAD.b + 16} textAnchor="middle" fontSize={10} fill="#64748B" className="tnum">
              {format(xMetric, invX(t))}
            </text>
          </g>
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} stroke="#64748B" strokeWidth={1} />
        <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={H - PAD.b} stroke="#64748B" strokeWidth={1} />

        {/* points */}
        {series.map((s) =>
          s.points
            .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y))
            .map((p, i) => {
              const cx = px(p.x)
              const cy = py(p.y)
              const r = p.r ?? s.r ?? 4
              const common = { opacity: s.opacity ?? 1 }
              const interactive = !!(tooltip && p.data != null)
              const hp = interactive
                ? {
                    onMouseEnter: (e: React.MouseEvent) => setHover({ data: p.data, mx: e.clientX, my: e.clientY }),
                    onMouseMove: (e: React.MouseEvent) => setHover({ data: p.data, mx: e.clientX, my: e.clientY }),
                    onMouseLeave: () => setHover(null),
                    style: { cursor: 'pointer' as const },
                  }
                : {}
              const title = <title>{`${p.label} · ${format(xMetric, p.x)} / ${format(yMetric, p.y)}`}</title>
              const shape =
                s.shape === 'ring' ? (
                  <circle cx={cx} cy={cy} r={r} fill="none" stroke={s.color} strokeWidth={2.5} {...common}>{title}</circle>
                ) : s.shape === 'diamond' ? (
                  <rect x={cx - r} y={cy - r} width={r * 2} height={r * 2} fill={s.color} transform={`rotate(45 ${cx} ${cy})`} {...common}>{title}</rect>
                ) : (
                  <circle cx={cx} cy={cy} r={r} fill={s.color} {...common}>{title}</circle>
                )
              return (
                <g key={`${s.name}${i}`}>
                  {shape}
                  {interactive && <circle cx={cx} cy={cy} r={Math.max(r + 7, 11)} fill="transparent" {...hp} />}
                </g>
              )
            }),
        )}
      </svg>

      {hover && tooltip && (
        <div
          className="fixed z-50 pointer-events-none"
          style={{
            left: flipX ? undefined : hover.mx + 14,
            right: flipX ? window.innerWidth - hover.mx + 14 : undefined,
            top: flipY ? undefined : hover.my + 14,
            bottom: flipY ? window.innerHeight - hover.my + 14 : undefined,
          }}
        >
          {tooltip(hover.data)}
        </div>
      )}
    </>
  )
}
