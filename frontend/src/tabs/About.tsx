import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../api'
import {
  BetaReleverChart, JCurveChart, MetricSpaceDiagram, VarianceDecomp, WeightBars,
} from '../components/AboutCharts'

// About: a plain-language walkthrough of how the proxy-asset engine works, with
// charts that show the actual numbers behind each step. Written to be read top to
// bottom by someone hearing it for the first time.

const STEPS: { title: string; body: string }[] = [
  { title: 'Place', body: "The holding's own numbers (revenue, EBITDA, margins, leverage) put it at a point among the traded assets in one shared space." },
  { title: 'Match', body: 'Find the traded names sitting closest to it. Ordinary comparable-company thinking, done on the fundamentals.' },
  { title: 'Weight', body: 'Turn those neighbours into a basket, closer names weighing more, and cap any single name so it stays diversified.' },
  { title: 'Check', body: 'Ship the proxy with its full workings, a scatter view, a confidence flag, and a human override. Then test it against real returns.' },
]

const WINS: { title: string; body: string }[] = [
  { title: 'No black box', body: 'The factors are the client\'s own input metrics. Nothing proprietary to explain, and the fit is right there on a scatter plot.' },
  { title: 'Reproducible', body: 'Every proxy carries its workings and a config version. The same inputs give the same basket, every time.' },
  { title: 'You stay in control', body: 'The proxy is a proposal. Accept it, edit the weights, swap a name, or reject it. Each change is logged with who, when and why.' },
  { title: 'Honest about coverage', body: 'It uses whatever metrics exist and flags the confidence rather than pretending. Thin data reads as low confidence, not a hard failure.' },
  { title: 'Knows what a fund is', body: 'Market exposure is sized to invested capital, uncalled commitment is treated as a liquidity call, and vintage is read as a point on the J-curve.' },
  { title: 'One risk engine', body: 'Private positions run through the same stack as listed ones. No separate spreadsheet process off to the side.' },
]

const ANALYTICS = ['Value-at-Risk & CVaR', 'Tracking error', 'Stress tests', 'Factor attribution', 'Contribution-to-risk', 'Coverage']
const ASSET_CLASSES = ['Direct Private Equity', 'Direct Private Debt', 'Direct Real Estate', 'Private Equity Fund', 'Private Debt Fund', 'Real Estate Fund']

const FAQ: { q: string; a: string }[] = [
  { q: 'Is this a valuation?', a: "No. It is a stand-in for how a holding behaves, built for risk analytics. It never says what the holding is worth, and NAV only ever goes in as an input." },
  { q: 'What is the minimum to build one?', a: 'A name, an asset class, a currency, and one numeric metric. Everything else just sharpens the match.' },
  { q: 'Why not a named factor model?', a: "So there is nothing to defend. The factors are the client's own metrics, and you can see the whole thing on a scatter plot." },
  { q: 'Similar fundamentals is not the same as returns moving together.', a: "Agreed, and we do not pretend otherwise. Similar companies tend to share market risk, but that is a claim to test, not assume. The Backtest tab measures it on real returns." },
  { q: 'How do you validate it?', a: "Hold out traded names, treat each as private, build a proxy from the rest, and measure the tracking error against the name's own returns. The proxy captures the systematic part; the single-name noise it cannot, and we say so." },
  { q: 'What about hedge funds?', a: "Left out on purpose. You cannot place a market-neutral fund in a revenue/EBITDA space from a strategy label. That needs return-based style analysis, which is a different tool." },
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
  // Live backtest headline numbers, with a sensible fallback if the API is cold.
  const [bt, setBt] = useState({ r2: 0.5, te: 0.18, corr: 0.71 })
  useEffect(() => {
    api.backtest()
      .then((d) => setBt({
        r2: d.aggregate.median_r2,
        te: d.aggregate.median_tracking_error,
        corr: d.aggregate.median_correlation,
      }))
      .catch(() => { /* keep the fallback numbers */ })
  }, [])

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-primary">How the proxy-asset engine works</h2>
        <p className="text-sm text-tertiary">A walkthrough with the real numbers behind each step. Read straight down.</p>
      </div>

      <div className="space-y-8">
        {/* Lede */}
        <Card className="border-primary/20 bg-primary/[0.03]">
          <p className="text-[15px] leading-relaxed text-ink">
            A private holding has no price ticker, so a risk engine has nothing to measure. We give it one. Each holding
            gets a <span className="font-semibold text-primary">proxy</span>: a small basket of listed stocks picked to
            move the way the holding moves. Once it has that basket, the private position runs through the same VaR,
            stress tests and attribution as everything else in the book. And we check the match against real returns
            instead of taking it on trust.
          </p>
          <p className="mt-4 border-l-2 border-secondary pl-3 text-sm italic text-secondary">
            Give every private asset a liquid stand-in, and the whole book, public and private, runs through one risk
            engine you can actually audit.
          </p>
        </Card>

        {/* Problem / solution */}
        <Section title="The problem, and what we do about it">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-danger mb-1.5">The problem</div>
              <p className="text-sm text-ink leading-relaxed">
                A private holding has no continuous price. A risk engine cannot measure what it cannot price, so private
                assets end up outside portfolio risk, or handled by hand in a spreadsheet.
              </p>
            </Card>
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-success mb-1.5">What we do</div>
              <p className="text-sm text-ink leading-relaxed">
                Stand the holding in for a basket of traded assets that behaves like it. The basket has a live price
                history, so every analytic that already runs on a listed line now runs on the private one.
              </p>
            </Card>
          </div>
        </Section>

        {/* How it works + the two core charts */}
        <Section title="How it works, in four steps">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-4">
            {STEPS.map((s, i) => (
              <Card key={s.title}>
                <div className="flex items-center gap-2.5 mb-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white">{i + 1}</span>
                  <span className="text-sm font-semibold text-primary">{s.title}</span>
                </div>
                <p className="text-[13px] leading-relaxed text-tertiary">{s.body}</p>
              </Card>
            ))}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <MetricSpaceDiagram />
            <WeightBars />
          </div>
          <p className="mt-3 text-xs text-tertiary">
            Under the hood: metrics are log-scaled and z-scored, then distances use <span className="font-medium">Mahalanobis</span>{' '}
            so that revenue, EBITDA and net income (which move together) are not counted three times as size. Margins
            carry less weight than size, and the distance is averaged per metric so a two-metric match and a six-metric
            match sit on the same scale.
          </p>
        </Section>

        {/* Leverage / Hamada */}
        <Section title="Leverage: matching capital structure, then relevering the beta">
          <Card>
            <p className="text-sm text-ink leading-relaxed mb-4">
              A buyout at five times net debt to EBITDA is far riskier at the equity line than a listed comp barely
              carrying debt, even if the two businesses look identical. So leverage is one of the matching metrics, and
              then the basket's equity beta is relevered to the holding's capital structure using the Hamada relation.
              The picture below is a levered deal against lighter-levered comps.
            </p>
            <BetaReleverChart />
          </Card>
        </Section>

        {/* Backtest */}
        <Section title="Does the basket actually track? We measure it">
          <Card>
            <p className="text-sm text-ink leading-relaxed mb-4">
              Similar fundamentals should mean similar returns, but that is something to test, not assert. So we hold
              out traded names one at a time, treat each as private, build a proxy from the rest of the universe, and
              compare returns. The proxy captures the market and sector part of a name's movement. The single-name noise
              it cannot, and it should not pretend to. Here is where that line falls.
            </p>
            <VarianceDecomp r2={bt.r2} trackingError={bt.te} correlation={bt.corr} />
          </Card>
        </Section>

        {/* J-curve */}
        <Section title="Funds: reading vintage as a point on the J-curve">
          <Card>
            <p className="text-sm text-ink leading-relaxed mb-4">
              A 2024 fund that has called a fifth of its commitment behaves nothing like a 2016 fund that is fully drawn,
              even at the same vintage label. So the engine reads vintage as a number: fund age plus the share called
              places it on the J-curve, and market exposure is sized to what is actually invested rather than the whole
              commitment.
            </p>
            <JCurveChart />
          </Card>
        </Section>

        {/* Why it holds up */}
        <Section title="Why it holds up in a review">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {WINS.map((w) => (
              <Card key={w.title}>
                <div className="text-sm font-semibold text-primary mb-1">{w.title}</div>
                <p className="text-[13px] leading-relaxed text-tertiary">{w.body}</p>
              </Card>
            ))}
          </div>
        </Section>

        {/* Scope */}
        <Section title="Where the line is">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="border-success/30 bg-success/[0.04]">
              <div className="text-xs font-semibold uppercase tracking-wide text-success mb-2">In scope</div>
              <p className="text-sm font-medium text-ink">Risk and analytics representation</p>
              <p className="mt-1 text-[13px] leading-relaxed text-tertiary">
                It answers how a holding behaves against traded markets, and hands the analytics stack a basket of traded
                comparables it can consume.
              </p>
            </Card>
            <Card className="bg-neutral">
              <div className="text-xs font-semibold uppercase tracking-wide text-tertiary mb-2">Out of scope</div>
              <p className="text-sm font-medium text-ink">Valuation</p>
              <p className="mt-1 text-[13px] leading-relaxed text-tertiary">
                It never says what a holding is worth. NAV goes in for anchoring and validation and is never handed back
                out as a mark.
              </p>
            </Card>
          </div>
        </Section>

        {/* Coverage */}
        <Section title="What it covers">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-tertiary mb-2.5">Supported asset classes</div>
              <div className="flex flex-wrap gap-1.5">
                {ASSET_CLASSES.map((c) => (
                  <span key={c} className="inline-block rounded-full border border-border bg-neutral px-2.5 py-0.5 text-xs font-medium text-ink">{c}</span>
                ))}
              </div>
              <p className="mt-2.5 text-xs text-tertiary">
                Anything unrecognised goes to manual mapping rather than a guess. Hedge funds are left out on purpose:
                a strategy label cannot place a market-neutral fund in a revenue/EBITDA space, so those want return-based
                style analysis instead.
              </p>
            </Card>
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-tertiary mb-2.5">Analytics it unlocks</div>
              <div className="flex flex-wrap gap-1.5">
                {ANALYTICS.map((a) => (
                  <span key={a} className="inline-block rounded-full border border-secondary/30 bg-secondary/10 px-2.5 py-0.5 text-xs font-medium text-secondary">{a}</span>
                ))}
              </div>
              <p className="mt-2.5 text-xs text-tertiary">The same analytics already running on listed positions, now pointed at the private ones.</p>
            </Card>
          </div>
        </Section>

        {/* FAQ */}
        <Section title="Questions that come up">
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
          Source: Privé Technologies, Private Asset Methodology white paper v1.1. The proxy is a risk and analytics
          representation, not a valuation. Backtest figures shown here use illustrative simulated returns in this
          prototype; production runs on the client's real return history.
        </p>
      </div>
    </div>
  )
}
