import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  api, formatMetric, metricLabel, type BaselineAsset, type Config, type PrivateRecord, type Proxy,
} from '../api'
import { Button } from '../components/Button'
import { CapitalCallCard } from '../components/CapitalCallCard'
import { Collapsible } from '../components/Collapsible'
import { ConfidenceChip } from '../components/Chip'
import { ScatterPanel } from '../components/ScatterPanel'
import type { ScatterSeries } from '../components/Scatter'

const CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF', 'JPY', 'HKD', 'SGD', 'CNY', 'AUD', 'CAD']
const REGIONS = ['US', 'GB', 'CH', 'DE', 'FR', 'NL', 'JP', 'CN', 'KR', 'TW', 'EM Asia', 'Europe', 'Global']
const METRIC_INPUTS = ['revenue', 'ebitda', 'net_income', 'last_nav', 'expected_yield', 'occupancy_rate']

type Form = Record<string, string>
type CallRow = { date: string; amount: string; purpose: string }

function initialForm(config: Config, editRecord?: PrivateRecord | null): Form {
  const defaults = { asset_class: config.asset_classes[0]?.value ?? '', currency: 'USD' }
  if (!editRecord) return defaults
  const f: Form = { ...defaults }
  for (const [k, v] of Object.entries(editRecord.input)) {
    if (k === 'capital_calls' || v === null || v === undefined) continue
    f[k] = String(v)
  }
  return f
}

function initialCalls(editRecord?: PrivateRecord | null): CallRow[] {
  const cc = editRecord?.input?.capital_calls
  if (!Array.isArray(cc)) return []
  return cc.map((c: any) => ({
    date: c.date ?? '', amount: c.amount != null ? String(c.amount) : '', purpose: c.purpose ?? '',
  }))
}

export function AddPrivateAsset({
  config, baseline, onSaved, editRecord,
}: {
  config: Config
  baseline: BaselineAsset[]
  onSaved: () => void
  editRecord?: PrivateRecord | null
}) {
  const isEditing = !!editRecord
  const [form, setForm] = useState<Form>(() => initialForm(config, editRecord))
  const [calls, setCalls] = useState<CallRow[]>(() => initialCalls(editRecord))
  const capitalOpen = calls.length > 0 || !!(form.commitment || form.paid_in || form.capital_call_line)
  const [proxy, setProxy] = useState<Proxy | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))
  const addCall = () => setCalls((cs) => [...cs, { date: '', amount: '', purpose: '' }])
  const updateCall = (i: number, k: keyof CallRow, v: string) =>
    setCalls((cs) => cs.map((c, idx) => (idx === i ? { ...c, [k]: v } : c)))
  const removeCall = (i: number) => setCalls((cs) => cs.filter((_, idx) => idx !== i))

  const hasAnyMetric = METRIC_INPUTS.some((m) => form[m]?.trim())
  const hasCapitalCall = !!(
    form.commitment?.trim() || form.paid_in?.trim() || form.capital_call_line?.trim() ||
    calls.some((c) => c.amount || c.date || c.purpose)
  )
  const mandatoryOk = !!form.name?.trim() && !!form.asset_class && !!form.currency
  const sectors = useMemo(
    () => Array.from(new Set(baseline.map((b) => b.sector).filter(Boolean))) as string[],
    [baseline],
  )

  const payload = useMemo(
    () => ({ ...form, capital_calls: calls.filter((c) => c.amount || c.date || c.purpose) }),
    [form, calls],
  )

  // Debounced live preview.
  useEffect(() => {
    window.clearTimeout(timer.current)
    if (!hasAnyMetric && !hasCapitalCall) {
      setProxy(null)
      return
    }
    timer.current = window.setTimeout(() => {
      api.preview(payload).then((r) => setProxy(r.proxy)).catch(() => setProxy(null))
    }, 350)
    return () => window.clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(payload)])

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      if (isEditing) await api.update(editRecord!.id, payload)
      else await api.add(payload)
      onSaved()
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  const comparableIds = new Set((proxy?.comparables ?? []).map((c) => c.asset_id))
  const weightById = new Map((proxy?.comparables ?? []).map((c) => [c.asset_id, c.weight]))

  const buildSeries = (x: string, y: string): ScatterSeries[] => {
    const base: ScatterSeries = {
      name: 'Baseline',
      color: '#CBD5E1',
      r: 3,
      opacity: 0.75,
      points: baseline
        .filter((a) => !comparableIds.has(a.id))
        .map((a) => ({ x: a.metrics[x], y: a.metrics[y], label: a.name })),
    }
    const comps: ScatterSeries = {
      name: 'Comparables',
      color: '#1F6FA8',
      points: (proxy?.comparables ?? []).map((c) => ({
        x: c.metrics[x], y: c.metrics[y], label: `${c.name} · ${(c.weight * 100).toFixed(1)}%`,
        r: 4 + (weightById.get(c.asset_id) ?? 0) * 22,
      })),
    }
    const series: ScatterSeries[] = [base, comps]
    if (proxy?.holding_metrics && x in proxy.holding_metrics && y in proxy.holding_metrics) {
      series.push({
        name: 'This holding', color: '#0E3C5C', shape: 'ring', r: 8,
        points: [{ x: proxy.holding_metrics[x], y: proxy.holding_metrics[y], label: form.name || 'This holding' }],
      })
    }
    if (proxy?.proxy_point && x in proxy.proxy_point && y in proxy.proxy_point) {
      series.push({
        name: 'Constructed proxy', color: '#5FC08D', shape: 'diamond', r: 7,
        points: [{ x: proxy.proxy_point[x], y: proxy.proxy_point[y], label: 'Constructed proxy' }],
      })
    }
    return series
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* ---- form ---- */}
      <div className="rounded-lg border border-border bg-white p-5">
        <h2 className="text-lg font-semibold text-primary mb-1">
          {isEditing ? `Edit · ${editRecord!.input.name ?? 'private asset'}` : 'Add a private asset'}
        </h2>
        <p className="text-sm text-tertiary mb-4">
          Fields marked <span className="text-danger font-medium">*</span> are required.
          {' '}<span className="font-medium">{config.mandatory_note}</span>
        </p>

        <SectionTitle>Classification</SectionTitle>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Name" required full>
            <input className={inputCls} value={form.name ?? ''} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Project Helios" />
          </Field>
          <Field label="Asset class" required>
            <select className={inputCls} value={form.asset_class} onChange={(e) => set('asset_class', e.target.value)}>
              {config.asset_classes.map((c) => (
                <option key={c.value} value={c.value}>{c.value.replaceAll('_', ' ').toLowerCase()}</option>
              ))}
            </select>
          </Field>
          <Field label="Currency" required>
            <select className={inputCls} value={form.currency} onChange={(e) => set('currency', e.target.value)}>
              {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Region">
            <select className={inputCls} value={form.region ?? ''} onChange={(e) => set('region', e.target.value)}>
              <option value="">—</option>
              {REGIONS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Sector">
            <select className={inputCls} value={form.sector ?? ''} onChange={(e) => set('sector', e.target.value)}>
              <option value="">—</option>
              {sectors.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
        </div>

        <SectionTitle>Financial metrics <span className="normal-case text-tertiary font-normal">(optional; size figures in USD millions)</span></SectionTitle>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Revenue"><input type="number" className={inputCls} value={form.revenue ?? ''} onChange={(e) => set('revenue', e.target.value)} placeholder="e.g. 18000" /></Field>
          <Field label="EBITDA"><input type="number" className={inputCls} value={form.ebitda ?? ''} onChange={(e) => set('ebitda', e.target.value)} placeholder="e.g. 5200" /></Field>
          <Field label="Net income"><input type="number" className={inputCls} value={form.net_income ?? ''} onChange={(e) => set('net_income', e.target.value)} placeholder="e.g. 2600" /></Field>
          <Field label="Last NAV / market value"><input type="number" className={inputCls} value={form.last_nav ?? ''} onChange={(e) => set('last_nav', e.target.value)} placeholder="e.g. 90000" /></Field>
          <Field label="Expected yield (decimal)"><input type="number" step="0.001" className={inputCls} value={form.expected_yield ?? ''} onChange={(e) => set('expected_yield', e.target.value)} placeholder="e.g. 0.075" /></Field>
          <Field label="Occupancy rate (decimal)"><input type="number" step="0.01" className={inputCls} value={form.occupancy_rate ?? ''} onChange={(e) => set('occupancy_rate', e.target.value)} placeholder="e.g. 0.93" /></Field>
        </div>

        <SectionTitle>Additional details <span className="normal-case text-tertiary font-normal">(optional)</span></SectionTitle>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Strategy type"><input className={inputCls} value={form.strategy_type ?? ''} onChange={(e) => set('strategy_type', e.target.value)} placeholder="e.g. Buyout" /></Field>
          <Field label="Industry group"><input className={inputCls} value={form.industry_group ?? ''} onChange={(e) => set('industry_group', e.target.value)} /></Field>
          <Field label="Seniority"><input className={inputCls} value={form.seniority ?? ''} onChange={(e) => set('seniority', e.target.value)} /></Field>
          <Field label="Credit rating"><input className={inputCls} value={form.credit_rating ?? ''} onChange={(e) => set('credit_rating', e.target.value)} /></Field>
          <Field label="Vintage year"><input type="number" className={inputCls} value={form.vintage_year ?? ''} onChange={(e) => set('vintage_year', e.target.value)} /></Field>
        </div>

        <Collapsible
          title="Capital call management"
          subtitle="For commitment-based funds — commitment, paid-in, and the drawdown schedule"
          defaultOpen={capitalOpen}
        >
          <div className="grid grid-cols-2 gap-3">
            <Field label="Total commitment"><input type="number" className={inputCls} value={form.commitment ?? ''} onChange={(e) => set('commitment', e.target.value)} placeholder="e.g. 50000" /></Field>
            <Field label="Paid-in (called to date)"><input type="number" className={inputCls} value={form.paid_in ?? ''} onChange={(e) => set('paid_in', e.target.value)} placeholder="e.g. 30000" /></Field>
            <Field label="Capital-call line of credit"><input type="number" className={inputCls} value={form.capital_call_line ?? ''} onChange={(e) => set('capital_call_line', e.target.value)} placeholder="e.g. 5000" /></Field>
          </div>

          <div className="flex items-center justify-between mt-4 mb-2">
            <span className="text-[11px] uppercase tracking-wide text-tertiary font-semibold">Capital calls (drawdowns)</span>
            <button type="button" onClick={addCall} className="text-xs text-secondary hover:underline">+ Add call</button>
          </div>
          {calls.length === 0 && (
            <p className="text-xs text-tertiary">No calls added. Paid-in above is used if no schedule is entered.</p>
          )}
          {calls.map((c, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-center">
              <input type="date" aria-label="Call date" className={`${inputCls} col-span-3`} value={c.date} onChange={(e) => updateCall(i, 'date', e.target.value)} />
              <input type="number" placeholder="amount" aria-label="Call amount" className={`${inputCls} col-span-3`} value={c.amount} onChange={(e) => updateCall(i, 'amount', e.target.value)} />
              <input placeholder="purpose" aria-label="Call purpose" className={`${inputCls} col-span-5`} value={c.purpose} onChange={(e) => updateCall(i, 'purpose', e.target.value)} />
              <button type="button" onClick={() => removeCall(i)} aria-label="Remove call" className="col-span-1 text-danger text-sm">✕</button>
            </div>
          ))}
          <p className="text-[11px] text-tertiary mt-1">
            Paid-in defaults to the sum of calls when a schedule is entered. Uncalled commitment is treated as a
            liquidity obligation, not market exposure.
          </p>
        </Collapsible>

        <div className="mt-5 flex items-center gap-3">
          <Button variant="primary" disabled={!mandatoryOk || saving} onClick={save}>
            {saving ? 'Saving…' : isEditing ? 'Update proxy' : 'Save proxy'}
          </Button>
          <Button variant="secondary" onClick={() => { setForm(initialForm(config, editRecord)); setCalls(initialCalls(editRecord)); setProxy(null) }}>
            Reset
          </Button>
          {!mandatoryOk && <span className="text-xs text-tertiary">Complete required fields to save.</span>}
          {error && <span className="text-xs text-danger">{error}</span>}
        </div>
      </div>

      {/* ---- live proxy + scatter ---- */}
      <div className="rounded-lg border border-border bg-white p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-primary">Proposed proxy</h2>
          {proxy && proxy.status === 'constructed' && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-tertiary">confidence</span>
              <ConfidenceChip value={proxy.confidence} />
            </div>
          )}
        </div>

        {!hasAnyMetric && !hasCapitalCall && (
          <p className="text-sm text-tertiary py-10 text-center">
            Enter at least one financial metric to construct a proxy.
          </p>
        )}

        {(hasAnyMetric || hasCapitalCall) && proxy && proxy.status !== 'constructed' && (
          <p className="text-sm text-danger py-4">{proxy.reason}</p>
        )}

        {proxy && proxy.status === 'constructed' && (
          <>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm mb-3">
              <span className="text-tertiary">Coverage <strong className="text-ink">{Math.round((proxy.coverage ?? 0) * 100)}%</strong></span>
              <span className="text-tertiary">Metrics used <strong className="text-ink">{proxy.metrics_used.map(metricLabel).join(', ')}</strong></span>
              {proxy.filters_relaxed && <span className="text-danger">filters relaxed</span>}
            </div>

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
            <p className="text-[11px] text-tertiary mt-2">
              Proposal only — review on the scatter, then Save. Config v{proxy.config_version}.
            </p>
          </>
        )}

        {proxy?.capital_call && <div className="mt-4"><CapitalCallCard cc={proxy.capital_call} /></div>}
      </div>
    </div>
  )
}

const inputCls =
  'w-full rounded-md border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-secondary'

function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="text-[11px] uppercase tracking-wide text-tertiary font-semibold mt-5 mb-2">{children}</div>
}

function Field({ label, required, full, children }: {
  label: string; required?: boolean; full?: boolean; children: ReactNode
}) {
  return (
    <label className={`block ${full ? 'col-span-2' : ''}`}>
      <span className={`block text-xs mb-1 ${required ? 'text-ink font-medium' : 'text-tertiary'}`}>
        {label} {required && <span className="text-danger">*</span>}
      </span>
      {children}
    </label>
  )
}
