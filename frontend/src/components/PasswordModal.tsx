import { useState, useEffect, useRef } from 'react'
import { Lock, Loader2, XCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function PasswordModal() {
  const { showPasswordModal, setShowPasswordModal, verifyPassword, pendingAction, setPendingAction, setAdminAuthenticated } = useAuth()
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (showPasswordModal) {
      setPassword('')
      setError('')
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [showPasswordModal])

  if (!showPasswordModal) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return
    setLoading(true)
    setError('')
    try {
      const result = await verifyPassword(password)
      if (result.success) {
        setAdminAuthenticated(true)
        setShowPasswordModal(false)
        pendingAction?.(password)
        setPendingAction(null)
      } else {
        setError(result.message || 'Incorrect password')
        setPassword('')
        inputRef.current?.focus()
      }
    } catch {
      setError('Verification failed')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setShowPasswordModal(false)
    setPendingAction(null)
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
         onClick={handleClose}>
      <div className="bg-[#2c313a] border border-gray-700/50 rounded-xl shadow-2xl w-full max-w-xs mx-4"
           onClick={e => e.stopPropagation()}>
        <form onSubmit={handleSubmit}>
          <div className="px-6 pt-6 pb-4 flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
              <Lock size={22} className="text-blue-400" />
            </div>
            <h3 className="text-sm font-medium text-white">Admin Password Required</h3>
            <input
              ref={inputRef}
              type="password"
              value={password}
              onChange={e => { setPassword(e.target.value); setError('') }}
              placeholder="Enter password"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white text-center placeholder-gray-600 focus:outline-none focus:border-blue-500"
              autoComplete="off"
            />
            {error && (
              <div className="flex items-center gap-1.5 text-xs text-red-400">
                <XCircle size={14} />
                {error}
              </div>
            )}
          </div>
          <div className="px-6 pb-5 flex gap-2">
            <button type="button" onClick={handleClose}
                    className="flex-1 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-700 transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading || !password.trim()}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              {loading && <Loader2 size={14} className="animate-spin" />}
              Unlock
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
