// Small, self-contained SVG charts for the About page. No chart library: each is
// a hand-drawn SVG using the app palette, so the explanation of the methodology
// is visual, not just prose. All figures here are illustrative examples.

const C = {
  primary: '#0E3C5C',   // the holding
  secondary: '#1F6FA8', // comparables / bars
  green: '#5FC08D',     // the constructed proxy
  success: '#16A34A',
  gray: '#CBD5E1',      // baseline / residual
  grid: '#EEF2F6',
  ink: '#0F2433',
  muted: '#64748B',
}

function Figure({ caption, children }: { caption: string; children: React.ReactNode }) {
  return (
    <figure className="m-0">
      <div className="rounded-lg border border-border bg-white p-4">{children}</div>
      <figcaption className="mt-2 text-[11px] text-tertiary">{caption}</figcaption>
    </figure>
  )
}

// 1) Metric space: a holding, its nearest comparables, and the proxy point. ----
export function MetricSpaceDiagram() {
  // Fixed illustrative coordinates in a 0..100 space (x = size, y = margin).
  const baseline = [
    [12, 30], [20, 62], [26, 18], [34, 78], [40, 44], [46, 70], [52, 24],
    [58, 88], [64, 40], [72, 66], [78, 20], [84, 54], [90, 82], [30, 52],
    [68, 14], [16, 84],
  ]
  const holding = [50, 55]
  const comps: [number, number, number][] = [
    [46, 60, 8], [56, 58, 7], [52, 46, 6], // x, y, radius (weight)
  ]
  const proxy = [51, 55]
  const X = (v: number) => 40 + (v / 100) * 300
  const Y = (v: number) => 150 - (v / 100) * 120

  return (
    <Figure caption="Every asset is a point placed by its own fundamentals. The proxy is a weighted basket of the holding's nearest traded neighbours. Illustrative.">
      <svg viewBox="0 0 360 175" width="100%" role="img" aria-label="Metric-space diagram">
        {/* axes */}
        <line x1={40} y1={150} x2={350} y2={150} stroke={C.muted} strokeWidth={1} />
        <line x1={40} y1={20} x2={40} y2={150} stroke={C.muted} strokeWidth={1} />
        <text x={195} y={170} textAnchor="middle" fontSize={10} fill={C.muted}>Size (log revenue / EBITDA)</text>
        <text x={14} y={90} textAnchor="middle" fontSize={10} fill={C.muted} transform="rotate(-90 14 90)">Profitability</text>
        {/* baseline */}
        {baseline.map(([x, y], i) => (
          <circle key={i} cx={X(x)} cy={Y(y)} r={3} fill={C.gray} />
        ))}
        {/* links holding -> comparables */}
        {comps.map(([x, y], i) => (
          <line key={i} x1={X(holding[0])} y1={Y(holding[1])} x2={X(x)} y2={Y(y)} stroke={C.secondary} strokeWidth={1} strokeDasharray="2 2" opacity={0.5} />
        ))}
        {/* comparables (size = weight) */}
        {comps.map(([x, y, r], i) => (
          <circle key={i} cx={X(x)} cy={Y(y)} r={r} fill={C.secondary} />
        ))}
        {/* proxy point (diamond) */}
        <rect x={X(proxy[0]) - 5} y={Y(proxy[1]) - 5} width={10} height={10} fill={C.green} transform={`rotate(45 ${X(proxy[0])} ${Y(proxy[1])})`} />
        {/* holding (ring) */}
        <circle cx={X(holding[0])} cy={Y(holding[1])} r={7} fill="none" stroke={C.primary} strokeWidth={2.5} />
      </svg>
      <Legend items={[
        { label: 'Baseline (traded)', color: C.gray, shape: 'dot' },
        { label: 'Comparables (weighted)', color: C.secondary, shape: 'dot' },
        { label: 'This holding', color: C.primary, shape: 'ring' },
        { label: 'Proxy', color: C.green, shape: 'diamond' },
      ]} />
    </Figure>
  )
}

// 2) Basket weights (an example proxy). --------------------------------------
export function WeightBars() {
  const rows = [
    ['AMD', 15.4], ['SAP', 14.4], ['Salesforce', 13.8], ['Starbucks', 12.5],
    ['General Electric', 11.6], ['Adobe', 11.3], ['ASML', 11.0], ['Netflix', 9.8],
  ] as const
  const max = 16
  return (
    <Figure caption="Nearer comparables carry more weight. A distance floor and a 35% single-name cap keep the basket diversified. Example basket for a US tech growth deal.">
      <div className="space-y-1.5">
        {rows.map(([name, w]) => (
          <div key={name} className="flex items-center gap-2">
            <span className="w-32 shrink-0 text-[11px] text-ink text-right">{name}</span>
            <div className="flex-1">
              <div
                className="h-4 rounded-r"
                style={{ width: `${(w / max) * 100}%`, background: C.secondary }}
              />
            </div>
            <span className="w-10 shrink-0 text-[11px] tnum text-tertiary">{w.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </Figure>
  )
}

// 3) Hamada equity-beta relevering (the calculation). ------------------------
export function BetaReleverChart() {
  const basketBeta = 1.0
  const factor = 1.47
  const relevered = basketBeta * factor
  const scale = 90 / 1.6 // px per beta unit within a 0..1.6 range
  return (
    <Figure caption="A 5.0x-levered buyout (D/E 1.25) carries more equity risk than its comparables (D/E 0.19). The proxy's beta is scaled by the leverage difference. Illustrative.">
      <div className="text-[11px] tnum text-tertiary mb-3">
        relever factor = [1 + (1 - t)·(D/E)<sub>holding</sub>] / [1 + (1 - t)·(D/E)<sub>basket</sub>]
        {' '}= [1 + 0.75·1.25] / [1 + 0.75·0.19] = <span className="font-semibold text-ink">×1.47</span>{'  '}(t = 25%)
      </div>
      <div className="flex items-end gap-8 h-28 pl-2">
        <Bar label="Basket beta" value={basketBeta} h={basketBeta * scale} color={C.gray} />
        <div className="flex items-center pb-6 text-tertiary text-lg">→</div>
        <Bar label="Holding beta (relevered)" value={relevered} h={relevered * scale} color={C.secondary} />
      </div>
    </Figure>
  )
}

function Bar({ label, value, h, color }: { label: string; value: number; h: number; color: string }) {
  return (
    <div className="flex flex-col items-center">
      <div className="text-[11px] tnum font-semibold text-ink mb-1">{value.toFixed(2)}</div>
      <div className="w-14 rounded-t" style={{ height: `${h}px`, background: color }} />
      <div className="w-20 text-center text-[10px] text-tertiary mt-1 leading-tight">{label}</div>
    </div>
  )
}

// 4) Backtest: how much of the return the proxy actually explains. ------------
export function VarianceDecomp({ r2, trackingError, correlation }: {
  r2: number; trackingError: number; correlation: number
}) {
  const captured = Math.round(r2 * 100)
  const residual = 100 - captured
  return (
    <Figure caption="Out-of-sample, the proxy explains the systematic (market/sector) part of a holding's returns. The rest is single-name risk no proxy can capture. Prototype uses simulated returns; production uses real history.">
      <div className="grid grid-cols-3 gap-3 mb-4">
        <Stat label="Median tracking error" value={`${(trackingError * 100).toFixed(1)}%`} />
        <Stat label="Median correlation" value={correlation.toFixed(2)} />
        <Stat label="Median R²" value={r2.toFixed(2)} />
      </div>
      <div className="flex h-7 w-full overflow-hidden rounded" style={{ background: C.gray }}>
        <div className="flex items-center justify-center text-[11px] font-semibold text-white"
          style={{ width: `${captured}%`, background: C.secondary }}>
          {captured}% systematic
        </div>
        <div className="flex items-center justify-center text-[11px] font-medium text-tertiary"
          style={{ width: `${residual}%` }}>
          {residual}% idiosyncratic
        </div>
      </div>
      <div className="mt-2 flex justify-between text-[10px] text-tertiary">
        <span>captured by the proxy</span>
        <span>not capturable (single-name)</span>
      </div>
    </Figure>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-neutral p-2 text-center">
      <div className="text-lg font-semibold tnum text-primary">{value}</div>
      <div className="text-[10px] text-tertiary leading-tight mt-0.5">{label}</div>
    </div>
  )
}

// 5) The J-curve, with deployment stages. ------------------------------------
export function JCurveChart() {
  // A classic J: value dips (fees, early marks) then rises past commitment.
  const path = 'M 40 70 C 90 120, 150 120, 200 90 C 250 60, 300 40, 340 30'
  const stages = [
    { x: 70, label: 'investing' },
    { x: 150, label: 'deploying' },
    { x: 240, label: 'maturing' },
    { x: 320, label: 'harvesting' },
  ]
  return (
    <Figure caption="Vintage year is read numerically: fund age plus % called place a fund on its J-curve, so a 2024 fund at 20% called is not treated like a 2016 fund fully deployed.">
      <svg viewBox="0 0 360 150" width="100%" role="img" aria-label="Fund J-curve">
        <line x1={40} y1={75} x2={345} y2={75} stroke={C.grid} strokeWidth={1} />
        <line x1={40} y1={20} x2={40} y2={130} stroke={C.muted} strokeWidth={1} />
        <text x={36} y={30} textAnchor="end" fontSize={9} fill={C.muted}>+</text>
        <text x={36} y={128} textAnchor="end" fontSize={9} fill={C.muted}>-</text>
        <text x={30} y={72} textAnchor="end" fontSize={9} fill={C.muted}>0</text>
        <path d={path} fill="none" stroke={C.secondary} strokeWidth={2.5} />
        {stages.map((s) => (
          <g key={s.label}>
            <line x1={s.x} y1={20} x2={s.x} y2={132} stroke={C.grid} strokeWidth={1} />
            <text x={s.x} y={145} textAnchor="middle" fontSize={9} fill={C.muted}>{s.label}</text>
          </g>
        ))}
      </svg>
    </Figure>
  )
}

// Shared small legend row. ----------------------------------------------------
function Legend({ items }: { items: { label: string; color: string; shape: 'dot' | 'ring' | 'diamond' }[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
      {items.map((it) => (
        <span key={it.label} className="flex items-center gap-1.5 text-[10px] text-tertiary">
          <span
            style={{
              width: 9, height: 9,
              background: it.shape === 'ring' ? 'transparent' : it.color,
              border: it.shape === 'ring' ? `2px solid ${it.color}` : 'none',
              borderRadius: it.shape === 'diamond' ? 2 : 999,
              transform: it.shape === 'diamond' ? 'rotate(45deg)' : 'none',
              display: 'inline-block',
            }}
          />
          {it.label}
        </span>
      ))}
    </div>
  )
}
