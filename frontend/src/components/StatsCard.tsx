import { ReactNode } from 'react'

interface Props {
  label: string
  value: string | number
  sub?: string
  color?: 'default' | 'red' | 'green' | 'blue' | 'yellow'
  icon?: ReactNode
}

const colorMap = {
  default: 'text-white',
  red: 'text-red-400',
  green: 'text-green-400',
  blue: 'text-blue-400',
  yellow: 'text-yellow-400',
}

export default function StatsCard({ label, value, sub, color = 'default', icon }: Props) {
  return (
    <div className="border rounded-xl px-4 py-3 flex items-center gap-3" style={{ backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(12px)' }}>
      {icon && <div className="text-gray-600 shrink-0">{icon}</div>}
      <div className="min-w-0">
        <p className="text-xs text-gray-500 uppercase tracking-wider font-medium leading-tight">{label}</p>
        <p className={`text-xl font-bold leading-tight mt-0.5 ${colorMap[color]}`}>{value}</p>
        {sub && <p className="text-xs text-gray-600 leading-tight mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}
