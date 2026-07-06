import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import ExperimentPage from './pages/ExperimentPage'
import AnalyticsPage from './pages/AnalyticsPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/experiment" element={<ExperimentPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
