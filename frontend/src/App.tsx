import type { ReactElement } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { AuthProvider, useAuth } from './lib/AuthContext'
import ContractDetailPage from './pages/ContractDetailPage'
import ContractsPage from './pages/ContractsPage'
import CustomersPage from './pages/CustomersPage'
import DashboardPage from './pages/DashboardPage'
import ExcessReviewPage from './pages/ExcessReviewPage'
import InvoicesPage from './pages/InvoicesPage'
import JobOrderDetailPage from './pages/JobOrderDetailPage'
import JobOrdersPage from './pages/JobOrdersPage'
import Login from './pages/Login'
import ModulesPage from './pages/ModulesPage'

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
        <Route path="/" element={<DashboardPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/contracts" element={<ContractsPage />} />
        <Route path="/contracts/:id" element={<ContractDetailPage />} />
        <Route path="/job-orders" element={<JobOrdersPage />} />
        <Route path="/job-orders/:id" element={<JobOrderDetailPage />} />
        <Route path="/excess-review" element={<ExcessReviewPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="/modules" element={<ModulesPage />} />
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
