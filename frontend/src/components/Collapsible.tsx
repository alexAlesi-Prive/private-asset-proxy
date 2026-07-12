import { useState, type ReactNode } from 'react'

// User-toggled expandable section — collapsed by default, opened when applicable.
export function Collapsible({
  title, subtitle, defaultOpen = false, children,
}: {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-border rounded-lg mt-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
      >
        <span>
          <span className="block text-sm font-medium text-primary">{title}</span>
          {subtitle && <span className="block text-xs text-tertiary">{subtitle}</span>}
        </span>
        <span className="text-tertiary text-xs">{open ? '▾ Hide' : '▸ Add'}</span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  )
}
