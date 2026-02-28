import { WorkerStatus } from '../types'

const cfg = {
  running: {
    label: 'RUNNING',
    dot: 'bg-green-400 animate-pulse',
    badge: 'bg-green-500/10 text-green-400 border border-green-500/20',
  },
  initializing: {
    label: 'STARTING',
    dot: 'bg-amber-400 animate-pulse',
    badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  },
  stopped: {
    label: 'STOPPED',
    dot: 'bg-gray-500',
    badge: 'bg-gray-700/40 text-gray-400 border border-gray-700',
  },
  error: {
    label: 'ERROR',
    dot: 'bg-red-400',
    badge: 'bg-red-500/10 text-red-400 border border-red-500/20',
  },
}

export default function StatusBadge({ status }: { status: WorkerStatus }) {
  const { label, dot, badge } = cfg[status]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}
