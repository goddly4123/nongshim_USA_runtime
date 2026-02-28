import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Collection from './pages/Collection'
import Lines from './pages/Lines'
import History from './pages/History'
import Storage from './pages/Storage'
import Admin from './pages/Admin'
import { AuthProvider } from './contexts/AuthContext'
import PasswordModal from './components/PasswordModal'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="collection" element={<Collection />} />
          <Route path="lines" element={<Lines />} />
          <Route path="history" element={<History />} />
          <Route path="settings" element={<Storage />} />
          <Route path="admin" element={<Admin />} />
        </Route>
      </Routes>
      <PasswordModal />
    </AuthProvider>
  )
}
