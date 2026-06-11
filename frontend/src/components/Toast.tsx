import { useEffect, useState } from 'react'

interface ToastData {
  id: string
  city?: string
  message: string
  color?: string
}

type Listener = (t: ToastData) => void
const listeners = new Set<Listener>()

export function showToast(opts: Omit<ToastData, 'id'>) {
  const id = Math.random().toString(36).slice(2)
  listeners.forEach(fn => fn({ id, ...opts }))
}

function ToastItem({ toast, onDismiss }: { toast: ToastData; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 6000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  const color = toast.color ?? '#3b82f6'

  return (
    <div className="flex items-stretch overflow-hidden bg-[var(--surface-card)] rounded-xl shadow-lg border border-[var(--surface-border)] max-w-[300px] w-full">
      <div className="w-1 shrink-0" style={{ background: color }} />
      <div className="flex items-start gap-2 px-3 py-2.5 flex-1 min-w-0">
        <div className="flex-1 min-w-0">
          {toast.city && (
            <p className="text-xs font-semibold text-[var(--text-primary)] truncate">{toast.city}</p>
          )}
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">{toast.message}</p>
        </div>
        <button
          onClick={onDismiss}
          className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] shrink-0 text-lg leading-none pt-0.5"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  )
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastData[]>([])

  useEffect(() => {
    const fn: Listener = toast => setToasts(prev => [...prev.slice(-4), toast])
    listeners.add(fn)
    return () => { listeners.delete(fn) }
  }, [])

  function dismiss(id: string) {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  if (!toasts.length) return null

  return (
    <div className="fixed bottom-20 right-4 md:bottom-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      {toasts.map(toast => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem toast={toast} onDismiss={() => dismiss(toast.id)} />
        </div>
      ))}
    </div>
  )
}
