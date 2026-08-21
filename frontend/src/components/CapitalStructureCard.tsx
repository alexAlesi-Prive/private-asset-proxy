import { formatMetric, type CapitalStructure } from '../api'

// Capital structure & Hamada equity-beta relevering: how the holding's leverage
// compares to its comparables', and the factor the analytics stack applies to
// the proxy basket's equity beta to correct for the difference.
export function CapitalStructureCard({ cs }: { cs: CapitalStructure }) {
  const factor = cs.relever_factor
  return (
    <div className="rounded-lg border border-border bg-neutral p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-primary">Capital structure · beta relevering</h3>
        {factor != null && (
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold tnum ${
              factor > 1.02
                ? 'bg-danger/10 text-danger border border-danger/30'
                : factor < 0.98
                ? 'bg-success/10 text-success border border-success/30'
                : 'bg-neutral text-tertiary border border-border'
            }`}
          >
            ×{factor.toFixed(2)} beta
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
        <Stat label="Holding leverage" value={lev(cs.holding_leverage)} hint="net debt / EBITDA" />
        <Stat label="Basket leverage" value={lev(cs.basket_leverage)} hint="weighted avg" />
        <Stat label="Holding D/E" value={ratio(cs.holding_debt_to_equity)} hint="net debt / equity" />
        <Stat label="Basket D/E" value={ratio(cs.basket_debt_to_equity)} hint="weighted avg" />
        <Stat label="Net debt" value={cs.holding_net_debt != null ? formatMetric('market_value', cs.holding_net_debt) : '-'} />
        <Stat label="Equity (NAV)" value={cs.holding_equity != null ? formatMetric('market_value', cs.holding_equity) : '-'} />
      </div>

      <p className="text-[11px] text-tertiary mt-2">{cs.note}</p>
    </div>
  )
}

function lev(v: number | null | undefined): string {
  return v == null ? '-' : `${v.toFixed(1)}x`
}
function ratio(v: number | null | undefined): string {
  return v == null ? '-' : v.toFixed(2)
}
function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <div className="text-[11px] text-tertiary">{label}{hint ? ` · ${hint}` : ''}</div>
      <div className="tnum text-ink">{value}</div>
    </div>
  )
}
