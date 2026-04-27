import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './components/layout/PrivateRoute'
import Navbar from './components/layout/Navbar'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import DashboardPage from './pages/DashboardPage'
import CampaignsListPage from './pages/CampaignsListPage'
import NewCampaignPage from './pages/NewCampaignPage'
import CampaignLeadsPage from './pages/CampaignLeadsPage'
import LeadDetailPage from './pages/LeadDetailPage'
import ProductsPage from './pages/ProductsPage'
import AIDraftsPage from './pages/AIDraftsPage'
import InboxPage from './pages/InboxPage'
import TradeDataPage from './pages/TradeDataPage'
import SettingsPage from './pages/SettingsPage'

function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main>
        <Routes>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="campaigns" element={<CampaignsListPage />} />
          <Route path="campaigns/new" element={<NewCampaignPage />} />
          <Route path="campaigns/:id/leads" element={<CampaignLeadsPage />} />
          <Route path="leads/:id" element={<LeadDetailPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="ai-drafts" element={<AIDraftsPage />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="trade-data" element={<TradeDataPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route element={<PrivateRoute />}>
          <Route path="/*" element={<AppLayout />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
