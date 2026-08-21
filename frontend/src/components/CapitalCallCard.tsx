import { formatMetric, type CapitalCall } from '../api'

// Read-only summary of a fund's capital-call / commitment position.
export function CapitalCallCard({ cc }: { cc: CapitalCall }) {
  const pct = cc.pct_called != null ? Math.max(0, Math.min(1, cc.pct_called)) : null
  return (
    <div className="rounded-lg border border-border bg-neutral p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-primary">Capital call position</h3>
        {pct != null && <span className="text-xs text-tertiary tnum">{(pct * 100).toFixed(0)}% called</span>}
      </div>

      {pct != null && (
        <div className="h-2 w-full rounded-full bg-border overflow-hidden mb-3">
          <div className="h-full bg-secondary" style={{ width: `${pct * 100}%` }} />
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
        <Stat label="Commitment" value={fmt(cc.commitment)} />
        <Stat label="Paid-in (called)" value={fmt(cc.paid_in)} />
        <Stat label="Uncalled commitment" value={fmt(cc.uncalled)} />
        <Stat label="Capital-call line" value={fmt(cc.capital_call_line)} />
        <Stat label="Net uncovered" value={fmt(cc.net_uncovered_commitment)} hint="uncalled − credit line" />
        <Stat
          label="Effective market exposure"
          value={fmt(cc.effective_exposure)}
          hint={cc.exposure_basis === 'nav' ? 'from NAV' : cc.exposure_basis === 'paid_in' ? 'from paid-in' : undefined}
          strong
        />
      </div>

      {cc.deployment && (cc.deployment.j_curve_stage || cc.deployment.fund_age_years != null) && (
        <div className="mt-3 border-t border-border pt-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] uppercase tracking-wide text-tertiary font-semibold">Deployment · J-curve</span>
            {cc.deployment.j_curve_stage && (
              <span className="inline-block rounded-full bg-secondary/10 border border-secondary/30 px-2 py-0.5 text-[11px] font-medium text-secondary capitalize">
                {cc.deployment.j_curve_stage}
              </span>
            )}
          </div>
          <JCurve stage={cc.deployment.j_curve_stage} />
          <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-sm mt-2">
            <Stat label="Vintage" value={cc.deployment.vintage_year != null ? String(cc.deployment.vintage_year) : '—'} />
            <Stat label="Fund age" value={cc.deployment.fund_age_years != null ? `${cc.deployment.fund_age_years}y` : '—'} />
            <Stat label="% called" value={cc.deployment.pct_called != null ? `${(cc.deployment.pct_called * 100).toFixed(0)}%` : '—'} />
          </div>
        </div>
      )}

      {cc.calls?.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-[10px] uppercase tracking-wide text-tertiary">
                <th className="text-left py-1 pr-2">Date</th>
                <th className="text-right py-1 pr-2">Amount</th>
                <th className="text-right py-1 pr-2">% commit.</th>
                <th className="text-left py-1">Purpose</th>
              </tr>
            </thead>
            <tbody>
              {cc.calls.map((c, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  <td className="py-1 pr-2 tnum">{c.date ?? '—'}</td>
                  <td className="py-1 pr-2 text-right tnum">{fmt(c.amount)}</td>
                  <td className="py-1 pr-2 text-right tnum">
                    {c.pct_of_commitment != null ? `${(c.pct_of_commitment * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="py-1 text-tertiary">{c.purpose ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-tertiary mt-2">{cc.note}</p>
    </div>
  )
}

const J_STAGES = ['investing', 'deploying', 'maturing', 'harvesting']

function JCurve({ stage }: { stage?: string | null }) {
  const idx = stage ? J_STAGES.indexOf(stage) : -1
  return (
    <div className="flex gap-1">
      {J_STAGES.map((s, i) => (
        <div key={s} className="flex-1">
          <div className={`h-1.5 rounded-full ${i <= idx ? 'bg-secondary' : 'bg-border'}`} />
          <div className={`mt-1 text-[9px] text-center capitalize ${i === idx ? 'text-secondary font-semibold' : 'text-tertiary'}`}>{s}</div>
        </div>
      ))}
    </div>
  )
}

function fmt(v: number | null | undefined): string {
  return v == null ? '—' : formatMetric('market_value', v)
}

function Stat({ label, value, hint, strong }: { label: string; value: string; hint?: string; strong?: boolean }) {
  return (
    <div>
      <div className="text-[11px] text-tertiary">{label}{hint ? ` · ${hint}` : ''}</div>
      <div className={`tnum ${strong ? 'font-semibold text-primary' : 'text-ink'}`}>{value}</div>
    </div>
  )
}
