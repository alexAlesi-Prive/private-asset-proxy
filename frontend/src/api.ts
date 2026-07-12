// Typed client for the engine's JSON API + shared formatting helpers.

export type MetricMap = Record<string, number>

export interface BaselineAsset {
  id: string
  name: string
  ticker?: string
  sector?: string
  region?: string
  currency?: string
  metrics: MetricMap
}

export interface Comparable {
  asset_id: string
  name: string
  ticker?: string
  sector?: string
  region?: string
  currency?: string
  distance: number
  weight: number
  metrics: MetricMap
}

export interface CapitalCallEntry {
  date?: string | null
  amount?: number | null
  purpose?: string | null
  pct_of_commitment?: number | null
}

export interface CapitalCall {
  commitment?: number | null
  paid_in?: number | null
  uncalled?: number | null
  pct_called?: number | null
  capital_call_line?: number | null
  net_uncovered_commitment?: number | null
  effective_exposure?: number | null
  exposure_basis?: 'nav' | 'paid_in' | null
  calls: CapitalCallEntry[]
  note: string
}

export interface Proxy {
  holding_id: string
  holding_name: string
  asset_class?: string | null
  status: 'constructed' | 'insufficient_data' | 'no_comparables' | string
  reason?: string | null
  metrics_used: string[]
  filters_applied: Record<string, unknown>
  filters_relaxed: boolean
  comparables: Comparable[]
  proxy_point: MetricMap
  holding_metrics: MetricMap
  confidence?: 'high' | 'medium' | 'low' | null
  coverage: number
  config_version: string
  generated_at: string
  capital_call?: CapitalCall | null
}

export interface PrivateRecord {
  id: string
  created_at: string
  input: Record<string, any>
  proxy_summary?: {
    status: string
    confidence?: string | null
    coverage?: number
    n_comparables?: number
    top_comparable?: string | null
  }
}

export interface AssetClassInfo { value: string; mandatory_inputs: string[] }

export interface Config {
  version: string
  metrics: string[]
  scatter: { default_x: string; default_y: string; available_axes: string[] }
  mandatory_fields: string[]
  mandatory_note: string
  asset_classes: AssetClassInfo[]
  metric_fields: string[]
}

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`)
  return r.json() as Promise<T>
}

const jsonPost = (url: string, body: unknown, method = 'POST') =>
  fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const api = {
  config: () => fetch('/api/config').then(j<Config>),
  baseline: () => fetch('/api/baseline').then(j<{ count: number; assets: BaselineAsset[] }>),
  list: () => fetch('/api/private-assets').then(j<{ count: number; assets: PrivateRecord[] }>),
  get: (id: string) =>
    fetch(`/api/private-assets/${id}`).then(j<{ record: PrivateRecord; proxy: Proxy }>),
  add: (body: Record<string, any>) =>
    jsonPost('/api/private-assets', body).then(j<{ record: PrivateRecord; proxy: Proxy }>),
  update: (id: string, body: Record<string, any>) =>
    jsonPost(`/api/private-assets/${id}`, body, 'PUT').then(j<{ record: PrivateRecord; proxy: Proxy }>),
  remove: (id: string) => jsonPost(`/api/private-assets/${id}`, {}, 'DELETE').then(j<{ ok: boolean }>),
  preview: (body: Record<string, any>) =>
    jsonPost('/api/proxy/preview', body).then(j<{ proxy: Proxy }>),
}

// ---- formatting ---------------------------------------------------------- //
export const METRIC_LABELS: Record<string, string> = {
  revenue: 'Revenue',
  ebitda: 'EBITDA',
  net_income: 'Net income',
  market_value: 'Market value / NAV',
  ebitda_margin: 'EBITDA margin',
  net_margin: 'Net margin',
  expected_yield: 'Expected yield',
}

export const LOG_METRICS = new Set(['revenue', 'ebitda', 'net_income', 'market_value'])

export function metricLabel(m: string): string {
  return METRIC_LABELS[m] ?? m
}

/** Values for size metrics are in USD millions; margins/yields are decimals. */
export function formatMetric(metric: string, v: number | undefined | null): string {
  if (v === undefined || v === null || Number.isNaN(v)) return '—'
  if (metric.includes('margin') || metric === 'expected_yield' || metric === 'occupancy_rate')
    return `${(v * 100).toFixed(1)}%`
  const a = Math.abs(v)
  if (a >= 1e6) return `${(v / 1e6).toFixed(2)}T`
  if (a >= 1e3) return `${(v / 1e3).toFixed(1)}B`
  return `${v.toFixed(0)}M`
}
