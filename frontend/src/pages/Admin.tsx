import { useState } from 'react'
import { KeyRound, Lock, Eye, EyeOff, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { changeAdminPassword } from '../api'

export default function Admin() {
  const { requireAdmin, isAdminAuthenticated } = useAuth()
  const [verifiedPassword, setVerifiedPassword] = useState('')

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const canSubmit =
    newPassword.length > 0 &&
    confirmPassword.length > 0 &&
    newPassword === confirmPassword &&
    !saving

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return

    if (newPassword !== confirmPassword) {
      setResult({ ok: false, msg: 'New passwords do not match' })
      return
    }

    setSaving(true)
    setResult(null)
    try {
      await changeAdminPassword(verifiedPassword, newPassword)
      setResult({ ok: true, msg: 'Password changed successfully' })
      setVerifiedPassword(newPassword)
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      const msg = err?.message || 'Failed to change password'
      setResult({ ok: false, msg: msg.includes('403') ? 'Current password is incorrect' : msg })
    } finally {
      setSaving(false)
    }
  }

  if (!isAdminAuthenticated) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center">
          <Lock size={28} className="text-gray-500" />
        </div>
        <h2 className="text-base font-medium text-white">Admin Settings</h2>
        <p className="text-sm text-gray-500">Admin password required to access this page</p>
        <button
          onClick={() => requireAdmin((pw) => { setVerifiedPassword(pw) })}
          className="px-5 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors"
        >
          Unlock
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-700/40 shrink-0">
        <div className="w-9 h-9 rounded-lg bg-gray-800 flex items-center justify-center">
          <KeyRound size={18} className="text-gray-400" />
        </div>
        <div className="flex-1">
          <h1 className="text-base font-semibold text-white">Admin Settings</h1>
          <p className="text-xs text-gray-500">Manage admin password</p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-md">
          {/* Change Password Card */}
          <div className="rounded-xl border border-gray-700/50 bg-gray-800/30 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Lock size={20} className="text-blue-400" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">Change Password</h2>
                <p className="text-xs text-gray-500">Update the admin password for this system</p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* New Password */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">New Password</label>
                <div className="relative">
                  <input
                    type={showNew ? 'text' : 'password'}
                    value={newPassword}
                    onChange={e => { setNewPassword(e.target.value); setResult(null) }}
                    className="w-full px-3 py-2 pr-10 rounded-lg bg-gray-900/60 border border-gray-700/50 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20"
                    placeholder="Enter new password"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew(p => !p)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                  >
                    {showNew ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Confirm New Password</label>
                <div className="relative">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={e => { setConfirmPassword(e.target.value); setResult(null) }}
                    className={`w-full px-3 py-2 pr-10 rounded-lg bg-gray-900/60 border text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 ${
                      confirmPassword && newPassword !== confirmPassword
                        ? 'border-red-500/50 focus:border-red-500/50 focus:ring-red-500/20'
                        : 'border-gray-700/50 focus:border-blue-500/50 focus:ring-blue-500/20'
                    }`}
                    placeholder="Re-enter new password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm(p => !p)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                  >
                    {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {confirmPassword && newPassword !== confirmPassword && (
                  <p className="text-xs text-red-400 mt-1">Passwords do not match</p>
                )}
              </div>

              {/* Result Message */}
              {result && (
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                  result.ok
                    ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {result.ok ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
                  {result.msg}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={!canSubmit}
                className="w-full py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
              >
                {saving ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    Changing...
                  </>
                ) : (
                  'Change Password'
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
