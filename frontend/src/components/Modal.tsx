import { useEffect, type ReactNode } from 'react'

// Centered dialog over a dimmed, blurred backdrop. Closes on backdrop click or Esc.
export function Modal({
  open, onClose, title, children,
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  children: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 sm:p-6 overflow-y-auto">
      {/* backdrop */}
      <div className="fixed inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} aria-hidden />
      {/* dialog */}
      <div
        role="dialog"
        aria-modal="true"
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-5xl my-4"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border sticky top-0 bg-white rounded-t-xl">
          <h3 className="text-base font-semibold text-primary pr-8">{title}</h3>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-tertiary hover:text-ink text-xl leading-none -mr-1"
          >
            ×
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}
