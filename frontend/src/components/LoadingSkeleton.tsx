function Shimmer({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

export function CardSkeleton() {
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6 flex flex-col gap-3">
      <Shimmer className="h-3 w-20" />
      <Shimmer className="h-16 w-24 mt-1" />
      <Shimmer className="h-5 w-28 rounded-full" />
      <Shimmer className="h-3 w-36 mt-2" />
    </div>
  )
}

const BAR_HEIGHTS = [40, 65, 55, 80, 60, 75, 50, 85, 70, 60, 45, 90]

export function ChartSkeleton() {
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-6">
      <Shimmer className="h-4 w-36 mb-8" />
      <div className="flex items-end gap-2 h-44">
        {BAR_HEIGHTS.map((h, i) => (
          <div key={i} className="skeleton flex-1 rounded-t-sm" style={{ height: `${h}%` }} />
        ))}
      </div>
    </div>
  )
}

export function StatSkeleton() {
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] p-4 flex flex-col items-center gap-3">
      <Shimmer className="h-3 w-16" />
      <Shimmer className="h-9 w-14" />
    </div>
  )
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  const widths = ['w-24', 'w-20', 'w-12', 'w-12', 'w-16', 'w-20']
  return (
    <div className="bg-[var(--surface-card)] rounded-xl border border-[var(--surface-border)] overflow-hidden">
      <div className="flex items-center gap-4 px-4 py-3 border-b border-[var(--surface-border)]">
        {widths.map((w, i) => <Shimmer key={i} className={`h-3 ${w}`} />)}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3.5 border-b border-[var(--surface-border)] last:border-0">
          {widths.map((w, j) => <Shimmer key={j} className={`h-3 ${w}`} />)}
        </div>
      ))}
    </div>
  )
}
