import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import OnboardingWizard from './components/OnboardingWizard'
import Dashboard from './pages/Dashboard'
import ChartPage from './pages/ChartPage'
import JournalPage from './pages/JournalPage'
import CalendarPage from './pages/CalendarPage'
import StrategyPage from './pages/StrategyPage'
import BotControlPage from './pages/BotControlPage'
import IntelligencePage from './pages/IntelligencePage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  const [showOnboarding, setShowOnboarding] = useState(false)

  useEffect(() => {
    const onboarded = localStorage.getItem('echotrader_onboarded') === '1'
    setShowOnboarding(!onboarded)
  }, [])

  return (
    <ErrorBoundary>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/charts" element={<ChartPage />} />
          <Route path="/journal" element={<JournalPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/strategies" element={<StrategyPage />} />
          <Route path="/bots" element={<BotControlPage />} />
          <Route path="/intelligence" element={<IntelligencePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
      {showOnboarding && <OnboardingWizard onDone={() => setShowOnboarding(false)} />}
    </ErrorBoundary>
  )
}
