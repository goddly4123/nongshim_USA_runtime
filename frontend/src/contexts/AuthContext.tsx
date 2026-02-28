import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { verifyAdminPassword } from '../api'

interface AuthContextType {
  /** Verify password. Returns true on success. */
  verifyPassword: (password: string) => Promise<{ success: boolean; message?: string }>
  /** Request admin access. Always shows the password modal. Callback receives the verified password. */
  requireAdmin: (onSuccess: (password: string) => void) => void
  /** Session-level authentication state. */
  isAdminAuthenticated: boolean
  setAdminAuthenticated: (authenticated: boolean) => void
  /** Internal: modal state */
  pendingAction: ((password: string) => void) | null
  setPendingAction: (action: ((password: string) => void) | null) => void
  showPasswordModal: boolean
  setShowPasswordModal: (show: boolean) => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [pendingAction, setPendingAction] = useState<((password: string) => void) | null>(null)
  const [isAdminAuthenticated, setAdminAuthenticated] = useState(false)

  const verifyPassword = useCallback(async (password: string) => {
    return await verifyAdminPassword(password)
  }, [])

  const requireAdmin = useCallback((onSuccess: (password: string) => void) => {
    setPendingAction(() => onSuccess)
    setShowPasswordModal(true)
  }, [])

  return (
    <AuthContext.Provider value={{
      verifyPassword, requireAdmin,
      isAdminAuthenticated, setAdminAuthenticated,
      pendingAction, setPendingAction,
      showPasswordModal, setShowPasswordModal,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
