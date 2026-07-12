import { useEffect, useState, type MouseEvent } from 'react'
import { api, formatMetric, type BaselineAsset, type Config, type PrivateRecord, type Proxy } from '../api'
import { Button } from '../components/Button'
import { ConfidenceChip, StatusChip } from '../components/Chip'
import { Modal } from '../components/Modal'
import { ProxyView } from '../components/ProxyView'

export function PrivateAssets({
  config, baseline, refreshKey, onAdd, onEdit,
}: {
  config: Config
  baseline: BaselineAsset[]
  refreshKey: number
  onAdd: () => void
  onEdit: (record: PrivateRecord) => void
}) {
  const [records, setRecords] = useState<PrivateRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<PrivateRecord | null>(null)
  const [detail, setDetail] = useState<Proxy | null>(null)

  const load = () => {
    setLoading(true)
    api.list().then((r) => setRecords(r.assets)).finally(() => setLoading(false))
  }
  useEffect(load, [refreshKey])

  const openDetail = (record: PrivateRecord) => {
    setSelected(record)
    setDetail(null)
    api.get(record.id).then((r) => setDetail(r.proxy)).catch(() => setDetail(null))
  }
  const closeDetail = () => { setSelected(null); setDetail(null) }

  const edit = (record: PrivateRecord, e: MouseEvent) => { e.stopPropagation(); onEdit(record) }
  const remove = async (id: string, e: MouseEvent) => {
    e.stopPropagation()
    await api.remove(id)
    load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-primary">Private assets</h2>
          <p className="text-sm text-tertiary">{records.length} holding{records.length === 1 ? '' : 's'} · click a row to review its proxy.</p>
        </div>
        <Button variant="primary" onClick={onAdd}>+ Add private asset</Button>
      </div>

      {loading ? (
        <p className="text-sm text-tertiary py-10 text-center">Loading…</p>
      ) : records.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-white py-12 text-center">
          <p className="text-tertiary mb-3">No private assets yet.</p>
          <Button variant="outlined" onClick={onAdd}>Add your first private asset</Button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-[11px] uppercase tracking-wide text-tertiary">
                <th className="text-left px-3 py-2.5">Name</th>
                <th className="text-left px-3 py-2.5">Class</th>
                <th className="text-left px-3 py-2.5">CCY</th>
                <th className="text-right px-3 py-2.5">Last NAV</th>
                <th className="text-left px-3 py-2.5">Proxy</th>
                <th className="text-left px-3 py-2.5">Confidence</th>
                <th className="text-left px-3 py-2.5">Top comparable</th>
                <th className="px-3 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => {
                const s = r.proxy_summary
                return (
                  <tr
                    key={r.id}
                    onClick={() => openDetail(r)}
                    className="border-b border-border last:border-0 cursor-pointer hover:bg-neutral"
                  >
                    <td className="px-3 py-2 font-medium">
                      {r.input.name}
                      {r.input.capital_calls && <span className="ml-2 text-[10px] text-secondary align-middle">◇ capital calls</span>}
                    </td>
                    <td className="px-3 py-2 text-tertiary">{(r.input.asset_class ?? '').replaceAll('_', ' ').toLowerCase()}</td>
                    <td className="px-3 py-2 text-tertiary">{r.input.currency}</td>
                    <td className="px-3 py-2 text-right tnum">{r.input.last_nav != null ? formatMetric('market_value', r.input.last_nav) : '—'}</td>
                    <td className="px-3 py-2"><StatusChip status={s?.status} /></td>
                    <td className="px-3 py-2">{s?.status === 'constructed' ? <ConfidenceChip value={s?.confidence} /> : <span className="text-tertiary">—</span>}</td>
                    <td className="px-3 py-2 text-tertiary">{s?.top_comparable ?? '—'}</td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <button onClick={(e) => edit(r, e)} className="text-secondary text-xs hover:underline">Edit</button>
                      <span className="text-border mx-2">|</span>
                      <button onClick={(e) => remove(r.id, e)} className="text-danger text-xs hover:underline">Delete</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={!!selected}
        onClose={closeDetail}
        title={
          <span className="flex items-center gap-3">
            Proxy · {selected?.input.name}
            {selected && (
              <button
                onClick={() => { const rec = selected; closeDetail(); onEdit(rec) }}
                className="text-secondary text-xs font-normal hover:underline"
              >
                Edit inputs
              </button>
            )}
          </span>
        }
      >
        {detail ? (
          <ProxyView proxy={detail} baseline={baseline} config={config} />
        ) : (
          <p className="text-sm text-tertiary py-6">Loading proxy…</p>
        )}
      </Modal>
    </div>
  )
}
