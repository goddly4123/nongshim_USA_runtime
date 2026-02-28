import { useState, useEffect } from 'react'
import { Edit2, RotateCcw, Play, Square, AlertTriangle, Settings2, Lock } from 'lucide-react'
import { InspectionLine, InspectionConfig } from '../types'
import StatusBadge from '../components/StatusBadge'
import LineModal, { defaultConfig } from '../components/LineModal'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../api'

export default function Lines() {
  const { requireAdmin, isAdminAuthenticated } = useAuth()
  const [lines, setLines] = useState<InspectionLine[]>([])
  const [loading, setLoading] = useState(true)
  const [modalLine, setModalLine] = useState<InspectionLine | null | undefined>(undefined)
  // undefined = closed, null = new line, InspectionLine = edit

  const loadLines = async () => {
    try {
      const data = await api.fetchLines()
      setLines(data)
    } catch {
      // 백엔드 미실행 시 빈 목록 유지
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadLines() }, [])

  // 활성화 / 비활성화 토글
  const handleEnable = async (line: InspectionLine) => {
    const nowEnabled = line.config.enabled !== false
    // 낙관적 업데이트
    setLines(prev =>
      prev.map(l =>
        l.config.line_name === line.config.line_name
          ? { ...l, config: { ...l.config, enabled: !nowEnabled } }
          : l
      )
    )
    try {
      if (nowEnabled) await api.disableLine(line.config.line_name)
      else await api.enableLine(line.config.line_name)
    } catch {
      await loadLines()
    }
  }

  // Start / Stop 토글
  const handleToggle = async (line: InspectionLine) => {
    const isRunning = line.stats.status === 'running'
    setLines(prev =>
      prev.map(l =>
        l.config.line_name === line.config.line_name
          ? { ...l, stats: { ...l.stats, status: isRunning ? 'stopped' : 'running' } }
          : l
      )
    )
    try {
      if (isRunning) await api.stopLine(line.config.line_name)
      else await api.startLine(line.config.line_name)
    } catch {
      await loadLines()
    }
  }

  const handleReset = async (lineName: string) => {
    if (!window.confirm(`Reset statistics for "${lineName}"? (total_count and defect_count will be set to 0)`)) return
    try {
      await api.resetLine(lineName)
      await loadLines()
    } catch (e) {
      alert(`Reset failed: ${e}`)
    }
  }

  const handleSave = async (config: InspectionConfig) => {
    // modalLine이 null이면 신규, 아니면 수정
    const isNew = modalLine === null
    try {
      if (isNew) {
        await api.addLine(config)
      } else {
        // URL에는 반드시 원래 line_name(폴더명) 사용
        await api.updateLine(modalLine!.config.line_name, config)
      }
      await loadLines()
    } catch (e) {
      alert(`Save failed: ${e}`)
    }
    setModalLine(undefined)
  }

  if (!isAdminAuthenticated) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center">
          <Lock size={28} className="text-gray-500" />
        </div>
        <h2 className="text-base font-medium text-white">Line Manager</h2>
        <p className="text-sm text-gray-500">Admin password required to access this page</p>
        <button
          onClick={() => requireAdmin(() => {})}
          className="px-5 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors"
        >
          Unlock
        </button>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-amber-600/20 border border-amber-500/30 rounded-lg flex items-center justify-center">
            <Settings2 size={18} className="text-amber-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Line Manager</h1>
            <p className="text-xs text-gray-500">Configure and control inspection lines</p>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-xl overflow-hidden" style={{ backgroundColor: '#2c313a', borderColor: '#3e4451' }}>
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-700/60">
              {['', 'Line Name', 'Product', 'Detector', 'Camera IP', 'Status', ''].map((h, i) => (
                <th
                  key={i}
                  className={`px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                    h === 'Line Name' ? 'text-left' :
                    h === 'Product'  ? 'text-left' :
                    h === 'Detector' ? 'text-left' :
                    h === 'Status'   ? 'text-left' :
                    h === ''         ? '' :
                    'text-right'
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/40">
            {lines.map(line => {
              const enabled  = line.config.enabled !== false
              const isRunning = line.stats.status === 'running'
              const isError   = line.stats.status === 'error'
              const defRate   = parseFloat(line.stats.defect_rate)

              return (
                <tr
                  key={line.config.line_name}
                  className={`transition-colors ${
                    enabled
                      ? 'hover:bg-gray-800/40'
                      : 'opacity-40 pointer-events-none'
                  }`}
                >
                  {/* 활성화 체크박스 — pointer-events-none 예외 처리 */}
                  <td className="pl-4 pr-2 py-3.5 pointer-events-auto">
                    <button
                      onClick={() => handleEnable(line)}
                      title={enabled ? 'Deactivate this line' : 'Activate this line'}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                        enabled
                          ? 'bg-blue-600 border-blue-600'
                          : 'bg-transparent border-gray-600 hover:border-gray-400'
                      }`}
                    >
                      {enabled && (
                        <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                          <path d="M1 4l2.5 2.5L9 1" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                    </button>
                  </td>

                  <td className="pl-2 pr-4 py-3.5">
                    <p className="text-[10px] font-semibold text-gray-500 mb-1 font-mono">{line.stats.worker_folder || '-'}</p>
                    <p className="text-sm font-medium text-white">{line.config.project_name || line.config.line_name}</p>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="text-xs font-medium text-blue-400/80">
                      {line.config.active_product ?? '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${
                      (line.config.detector_type ?? 'yolo') === 'yolo'      ? 'bg-purple-500/15 text-purple-400' :
                      (line.config.detector_type ?? 'yolo') === 'paddleocr' ? 'bg-green-500/15 text-green-400' :
                      (line.config.detector_type ?? 'yolo') === 'cnn'       ? 'bg-orange-500/15 text-orange-400' :
                      'bg-gray-500/15 text-gray-400'
                    }`}>
                      {(line.config.detector_type ?? 'yolo').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-sm text-gray-400 font-mono">{line.config.camera_ip}</td>
                  <td className="px-4 py-3.5">
                    <div>
                      <StatusBadge status={line.stats.status} />
                      {isError && (
                        <p className="text-xs text-red-400/70 mt-1 max-w-[160px] truncate">
                          {line.stats.last_error}
                        </p>
                      )}
                    </div>
                  </td>

                  {/* 액션 버튼들 — pointer-events 항상 허용 */}
                  <td className="px-4 py-3.5 pointer-events-auto">
                    <div className="flex items-center justify-end gap-1">
                      {/* Start / Stop — 활성화 라인만 */}
                      {enabled && (
                        isError ? (
                          <span className="p-1.5 text-red-500/50" title={line.stats.last_error}>
                            <AlertTriangle size={14} />
                          </span>
                        ) : (
                          <button
                            onClick={() => handleToggle(line)}
                            className={`p-1.5 rounded transition-colors ${
                              isRunning
                                ? 'text-red-400 hover:bg-red-500/10'
                                : 'text-green-400 hover:bg-green-500/10'
                            }`}
                            title={isRunning ? 'Stop' : 'Start'}
                          >
                            {isRunning ? <Square size={14} /> : <Play size={14} />}
                          </button>
                        )
                      )}
                      <button
                        onClick={() => setModalLine(line)}
                        className="p-1.5 rounded text-gray-600 hover:text-gray-300 hover:bg-gray-700 transition-colors"
                        title="Edit"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        onClick={() => handleReset(line.config.line_name)}
                        className="p-1.5 rounded text-gray-700 hover:text-yellow-400 hover:bg-yellow-500/10 transition-colors"
                        title="Reset statistics"
                      >
                        <RotateCcw size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {!loading && lines.length === 0 && (
          <div className="py-20 text-center">
            <p className="text-gray-600 text-sm">No inspection lines configured.</p>
            <p className="text-gray-700 text-xs mt-1">Click "Add Line" to get started.</p>
          </div>
        )}
        {loading && (
          <div className="py-20 text-center">
            <p className="text-gray-700 text-sm">Loading...</p>
          </div>
        )}
      </div>

      {/* Modal */}
      {modalLine !== undefined && (
        <LineModal
          line={modalLine}
          onClose={() => setModalLine(undefined)}
          onSave={handleSave}
        />
      )}
    </div>
  )
}
