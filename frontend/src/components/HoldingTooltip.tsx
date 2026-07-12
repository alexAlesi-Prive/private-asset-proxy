import { formatMetric, type PrivateRecord } from '../api'
import { ConfidenceChip } from './Chip'

// Hover mini-card for a private asset on the metric map.
export function HoldingTooltip({ record }: { record: PrivateRecord }) {
  const i = record.input
  const s = record.proxy_summary
  const hasCapitalCall = !!(
    (Array.isArray(i.capital_calls) && i.capital_calls.length) ||
    i.commitment || i.paid_in || i.capital_call_line
  )
  return (
    <div className="w-64 rounded-lg border border-border bg-white shadow-xl p-3">
      <div className="text-sm font-semibold text-primary leading-tight">{i.name}</div>
      <div className="text-[11px] text-tertiary mb-2">
        {(i.asset_class ?? '—').replaceAll('_', ' ').toLowerCase()} · {i.currency ?? '—'}
      </div>

      <div className="space-y-1 text-xs">
        <Row label="Last NAV" value={i.last_nav != null ? formatMetric('market_value', i.last_nav) : '—'} />
        <Row label="Revenue" value={i.revenue != null ? formatMetric('revenue', i.revenue) : '—'} />
        <Row label="EBITDA" value={i.ebitda != null ? formatMetric('ebitda', i.ebitda) : '—'} />
        <Row label="Top comparable" value={s?.top_comparable ?? '—'} />
        <Row label="Capital calls" value={hasCapitalCall ? 'Yes' : 'No'} highlight={hasCapitalCall} />
      </div>

      <div className="flex items-center justify-between mt-2 pt-2 border-t border-border">
        <span className="text-[11px] text-tertiary">
          {s?.status === 'constructed' ? 'Proxy built' : s?.status === 'insufficient_data' ? 'Needs a metric' : s?.status ?? '—'}
        </span>
        {s?.status === 'constructed' && <ConfidenceChip value={s?.confidence} />}
      </div>
    </div>
  )
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-tertiary">{label}</span>
      <span className={`text-right tnum ${highlight ? 'text-secondary font-medium' : 'text-ink'}`}>{value}</span>
    </div>
  )
}
