// Confidence / status chips. Never colour-only — always carry the text label.
const CONFIDENCE: Record<string, string> = {
  high: 'bg-success/10 text-success border-success/30',
  medium: 'bg-secondary/10 text-secondary border-secondary/30',
  low: 'bg-tertiary/10 text-tertiary border-tertiary/40',
}

export function ConfidenceChip({ value }: { value?: string | null }) {
  const key = value ?? 'n/a'
  const cls = CONFIDENCE[key] ?? 'bg-tertiary/10 text-tertiary border-tertiary/40'
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {value ?? 'n/a'}
    </span>
  )
}

export function StatusChip({ status }: { status?: string }) {
  const ok = status === 'constructed'
  const cls = ok
    ? 'bg-success/10 text-success border-success/30'
    : 'bg-danger/10 text-danger border-danger/30'
  const label = status === 'constructed' ? 'Proxy built' : status === 'insufficient_data' ? 'Needs a metric' : status === 'no_comparables' ? 'No comparables' : status ?? '—'
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
