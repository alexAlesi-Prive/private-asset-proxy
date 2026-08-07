import { useEffect, useState } from 'react'
import { api, type BaselineAsset, type Config, type PrivateRecord } from './api'
import Logo from './components/Logo'
import { AddPrivateAsset } from './tabs/AddPrivateAsset'
import { PrivateAssets } from './tabs/PrivateAssets'
import { PortfolioScatter } from './tabs/PortfolioScatter'
import { BaselineUniverse } from './tabs/BaselineUniverse'
import { About } from './tabs/About'

type Tab = 'assets' | 'add' | 'scatter' | 'baseline' | 'about'

const TABS: { id: Tab; label: string }[] = [
  { id: 'assets', label: 'Private Assets' },
  { id: 'add', label: 'Add Private Asset' },
  { id: 'scatter', label: 'Portfolio Scatter' },
  { id: 'baseline', label: 'Baseline Universe' },
  { id: 'about', label: 'About' },
]

export default function App() {
  const [config, setConfig] = useState<Config | null>(null)
  const [baseline, setBaseline] = useState<BaselineAsset[]>([])
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('assets')
  const [refreshKey, setRefreshKey] = useState(0)
  const [editRecord, setEditRecord] = useState<PrivateRecord | null>(null)

  useEffect(() => {
    Promise.all([api.config(), api.baseline()])
      .then(([c, b]) => { setConfig(c); setBaseline(b.assets) })
      .catch((e) => setError(String(e)))
  }, [])

  const onSaved = () => {
    setRefreshKey((k) => k + 1)
    setEditRecord(null)
    setTab('assets')
  }
  const startAdd = () => { setEditRecord(null); setTab('add') }
  const startEdit = (record: PrivateRecord) => { setEditRecord(record); setTab('add') }

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Logo />
            <div className="hidden sm:block border-l border-border pl-4">
              <div className="text-sm font-semibold text-primary leading-tight">Proxy-Asset Engine</div>
              <div className="text-[11px] text-tertiary">Private-asset risk/analytics representation</div>
            </div>
          </div>
          {config && (
            <span className="text-[11px] text-tertiary">
              config <span className="font-medium text-ink">v{config.version}</span>
            </span>
          )}
        </div>
        <nav className="max-w-6xl mx-auto px-6 flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => { if (t.id === 'add') setEditRecord(null); setTab(t.id) }}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition
                ${tab === t.id ? 'border-primary text-primary' : 'border-transparent text-tertiary hover:text-ink'}`}
            >
              {t.id === 'add' && editRecord ? 'Edit Private Asset' : t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {error && tab !== 'about' && (
          <div className="rounded-md border border-danger/30 bg-danger/5 text-danger text-sm px-4 py-3 mb-4">
            Could not reach the engine API: {error}
          </div>
        )}
        {/* About is static pitch content — always available, even before the engine responds. */}
        {tab === 'about' ? (
          <About />
        ) : !config ? (
          <p className="text-sm text-tertiary py-16 text-center">Loading…</p>
        ) : tab === 'assets' ? (
          <PrivateAssets config={config} baseline={baseline} refreshKey={refreshKey} onAdd={startAdd} onEdit={startEdit} />
        ) : tab === 'add' ? (
          <AddPrivateAsset key={editRecord?.id ?? 'new'} config={config} baseline={baseline} onSaved={onSaved} editRecord={editRecord} />
        ) : tab === 'scatter' ? (
          <PortfolioScatter config={config} baseline={baseline} />
        ) : (
          <BaselineUniverse baseline={baseline} />
        )}
      </main>

      <footer className="max-w-6xl mx-auto px-6 py-6 text-[11px] text-tertiary">
        Proxy = risk/analytics representation, not a valuation. Baseline universe is prototype data (EPC in production).
      </footer>
    </div>
  )
}
