import type { ReactNode } from 'react'

// About — a short, sales-ready explainer of the proxy-asset methodology.
// Sourced from the Privé "Private Asset Methodology" white paper (v1.0). Kept
// deliberately tight and scannable so a rep can pitch straight down the page.

const ANALYTICS = [
  'Value-at-Risk & CVaR',
  'Tracking error',
  'Stress tests',
  'Factor attribution',
  'Contribution-to-risk',
  'Coverage',
]

const ASSET_CLASSES = [
  'Direct Private Equity',
  'Direct Private Debt',
  'Direct Real Estate',
  'Private Equity Fund',
  'Private Debt Fund',
  'Real Estate Fund',
  'Hedge Fund',
]

const STEPS: { title: string; body: string }[] = [
  {
    title: 'Place',
    body: "The holding's own fundamentals — revenue, EBITDA, margins, yield — position it as a point among thousands of traded assets in one shared metric space.",
  },
  {
    title: 'Match',
    body: 'Find its nearest traded comparables in that space. Classic comparable-company logic, run on the numbers.',
  },
  {
    title: 'Weight',
    body: 'Build a basket weighted by closeness — nearer comparables count for more — normalised to sum to 100%.',
  },
  {
    title: 'Explain',
    body: 'Ship the proxy with its full workings, a scatter-plot view, a confidence flag, and a one-click human override.',
  },
]

const WINS: { title: string; body: string }[] = [
  {
    title: 'No black box',
    body: 'The "factors" are the client’s own input metrics — nothing proprietary to defend. The fit is visible on a scatter plot.',
  },
  {
    title: 'Auditable & reproducible',
    body: 'Every proxy carries its full explanation and a config version. Identical inputs give an identical proxy, every time.',
  },
  {
    title: 'Human-in-the-loop',
    body: 'The proxy is a proposal, not a verdict. Accept, edit, replace or reject — each change logged with who / when / why.',
  },
  {
    title: 'Degrades gracefully',
    body: 'Uses whatever metrics exist and flags confidence — high / medium / low — instead of failing.',
  },
  {
    title: 'Fund-aware',
    body: 'Sizes market exposure to invested capital; reports uncalled commitment separately as a liquidity obligation.',
  },
  {
    title: 'One risk engine',
    body: 'Private positions run through the same analytics stack as listed ones — no separate, manual private-asset process.',
  },
]

const FAQ: { q: string; a: string }[] = [
  {
    q: 'Is this a valuation?',
    a: 'No — a behavioural stand-in for risk analytics. It never says what a holding is worth; NAV stays an input.',
  },
  {
    q: 'What’s the minimum to build one?',
    a: 'A name, an asset class, a currency, and one numeric metric. Every extra metric sharpens the match.',
  },
  {
    q: 'Why not a named factor model?',
    a: 'Transparency. There’s no proprietary factor table to defend — the factors are the client’s metrics, visible on a scatter.',
  },
  {
    q: 'Can the client disagree with a proxy?',
    a: 'Yes. They can accept, edit weights, replace comparables or reject it — every override kept as a full audit trail.',
  },
  {
    q: 'Is the result reproducible?',
    a: 'Yes. Identical inputs plus an identical config version always produce an identical proxy.',
  },
]

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="text-[11px] uppercase tracking-wide text-tertiary font-semibold mb-3">{title}</h3>
      {children}
    </section>
  )
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-border bg-white p-5 ${className}`}>{children}</div>
}

export function About() {
  return (
    <div className="max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-primary">About the methodology</h2>
        <p className="text-sm text-tertiary">
          A sales-ready walkthrough of how Privé represents private assets. Pitch straight down the page.
        </p>
      </div>

      <div className="space-y-8">
        {/* Lede + one-line pitch */}
        <Card className="border-primary/20 bg-primary/[0.03]">
          <p className="text-[15px] leading-relaxed text-ink">
            Privé lets illiquid private holdings run through the <span className="font-semibold">same risk and
            portfolio analytics as listed positions</span>. We build each holding a{' '}
            <span className="font-semibold text-primary">proxy-asset</span> — a basket of liquid, traded assets that
            behaves the way the holding behaves — so a private position flows through VaR, stress tests, tracking error
            and factor attribution exactly like a public one.
          </p>
          <p className="mt-4 border-l-2 border-secondary pl-3 text-sm italic text-secondary">
            “Give every private asset a liquid stand-in, and the whole portfolio — public and private — runs through one
            risk engine, transparently and auditably.”
          </p>
        </Card>

        {/* Problem / Solution */}
        <Section title="The problem → what we do">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-danger mb-1.5">The problem</div>
              <p className="text-sm text-ink leading-relaxed">
                A private holding has no continuous market price. A risk engine can’t measure what it can’t price,
                so private assets sit outside portfolio risk — or get handled by hand.
              </p>
            </Card>
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-success mb-1.5">What we do</div>
              <p className="text-sm text-ink leading-relaxed">
                Represent the holding as an explicit, auditable basket of traded assets whose combined behaviour
                approximates it. The basket has a live price history, so every analytic that runs on a listed line now
                runs on the private one.
              </p>
            </Card>
          </div>
        </Section>

        {/* How it works */}
        <Section title="How it works — four steps">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <Card key={s.title}>
                <div className="flex items-center gap-2.5 mb-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white">
                    {i + 1}
                  </span>
                  <span className="text-sm font-semibold text-primary">{s.title}</span>
                </div>
                <p className="text-[13px] leading-relaxed text-tertiary">{s.body}</p>
              </Card>
            ))}
          </div>
          <p className="mt-3 text-xs text-tertiary">
            Under the hood it’s a deterministic, config-versioned pipeline: metrics are log-scaled and z-scored, then
            the nearest comparables are chosen by standardised distance and inverse-distance weighted.
          </p>
        </Section>

        {/* Why it wins */}
        <Section title="Why it wins">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {WINS.map((w) => (
              <Card key={w.title}>
                <div className="text-sm font-semibold text-primary mb-1">{w.title}</div>
                <p className="text-[13px] leading-relaxed text-tertiary">{w.body}</p>
              </Card>
            ))}
          </div>
        </Section>

        {/* Scope boundary */}
        <Section title="Set the boundary early">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="border-success/30 bg-success/[0.04]">
              <div className="text-xs font-semibold uppercase tracking-wide text-success mb-2">In scope</div>
              <p className="text-sm font-medium text-ink">Risk &amp; analytics representation</p>
              <p className="mt-1 text-[13px] leading-relaxed text-tertiary">
                Answers “how does this holding behave vs. traded markets?” Output: a basket of traded comparables the
                analytics stack can consume.
              </p>
            </Card>
            <Card className="bg-neutral">
              <div className="text-xs font-semibold uppercase tracking-wide text-tertiary mb-2">Out of scope</div>
              <p className="text-sm font-medium text-ink">Valuation / fair-value marking</p>
              <p className="mt-1 text-[13px] leading-relaxed text-tertiary">
                We never say what a holding is worth. NAV is an input for anchoring and validation only — never
                re-derived as an output.
              </p>
            </Card>
          </div>
          <p className="mt-3 text-xs text-tertiary">
            Leading with this keeps the conversation defensible — Privé is the risk layer, not a pricing opinion.
          </p>
        </Section>

        {/* Coverage */}
        <Section title="What it covers">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-tertiary mb-2.5">
                Supported asset classes
              </div>
              <div className="flex flex-wrap gap-1.5">
                {ASSET_CLASSES.map((c) => (
                  <span
                    key={c}
                    className="inline-block rounded-full border border-border bg-neutral px-2.5 py-0.5 text-xs font-medium text-ink"
                  >
                    {c}
                  </span>
                ))}
              </div>
              <p className="mt-2.5 text-xs text-tertiary">
                Unrecognised classes route to manual mapping — never guessed.
              </p>
            </Card>
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-tertiary mb-2.5">
                Analytics it unlocks
              </div>
              <div className="flex flex-wrap gap-1.5">
                {ANALYTICS.map((a) => (
                  <span
                    key={a}
                    className="inline-block rounded-full border border-secondary/30 bg-secondary/10 px-2.5 py-0.5 text-xs font-medium text-secondary"
                  >
                    {a}
                  </span>
                ))}
              </div>
              <p className="mt-2.5 text-xs text-tertiary">
                The same analytics already run on listed positions — now applied to private ones.
              </p>
            </Card>
          </div>
        </Section>

        {/* Talking points */}
        <Section title="Talking points — handling the obvious questions">
          <Card className="divide-y divide-border p-0">
            {FAQ.map((f) => (
              <div key={f.q} className="px-5 py-3.5">
                <p className="text-sm font-semibold text-primary">{f.q}</p>
                <p className="mt-1 text-[13px] leading-relaxed text-tertiary">{f.a}</p>
              </div>
            ))}
          </Card>
        </Section>

        <p className="text-[11px] text-tertiary">
          Source: Privé Technologies — Private Asset Methodology white paper, v1.0. Proxy = risk/analytics
          representation, not a valuation.
        </p>
      </div>
    </div>
  )
}
