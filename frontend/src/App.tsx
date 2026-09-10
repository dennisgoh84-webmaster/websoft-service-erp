import type { ReactElement } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { AuthProvider, useAuth } from './lib/AuthContext'
import ContractDetailPage from './pages/ContractDetailPage'
import ContractsPage from './pages/ContractsPage'
import CustomersPage from './pages/CustomersPage'
import ExcessReviewPage from './pages/ExcessReviewPage'
import InvoicesPage from './pages/InvoicesPage'
import Login from './pages/Login'
import TicketDetailPage from './pages/TicketDetailPage'
import TicketsPage from './pages/TicketsPage'

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return <p style={{ padding: 24 }}>Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<CustomersPage />} />
        <Route path="/contracts" element={<ContractsPage />} />
        <Route path="/contracts/:id" element={<ContractDetailPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
        <Route path="/excess-review" element={<ExcessReviewPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
