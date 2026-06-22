import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Assets
export const listAssets = (params?: Record<string, string>) =>
  api.get('/assets', { params }).then((r) => r.data)

export const createAsset = (payload: unknown) =>
  api.post('/assets', payload).then((r) => r.data)

export const getAssetBars = (assetId: number, timeframe = '1d', limit = 500) =>
  api.get(`/assets/${assetId}/bars`, { params: { timeframe, limit } }).then((r) => r.data)

export const getAssetQuote = (assetId: number) =>
  api.get(`/assets/${assetId}/quote`).then((r) => r.data)

export const loadAssetHistory = (assetId: number, params?: Record<string, unknown>) =>
  api.post(`/assets/${assetId}/load-history`, null, { params }).then((r) => r.data)

export const getIndicators = (
  assetId: number,
  indicator: string,
  period = 20,
  timeframe = '1d',
  limit = 500,
) =>
  api
    .get(`/assets/${assetId}/indicators`, { params: { indicator, period, timeframe, limit } })
    .then((r) => r.data)

// Trades
export const listTrades = (params?: Record<string, unknown>) =>
  api.get('/trades', { params }).then((r) => r.data)

export const createTrade = (payload: unknown) =>
  api.post('/trades', payload).then((r) => r.data)

export const updateTrade = (id: number, payload: unknown) =>
  api.patch(`/trades/${id}`, payload).then((r) => r.data)

// Journal
export const listJournalEntries = (params?: Record<string, unknown>) =>
  api.get('/journal/entries', { params }).then((r) => r.data)

export const getJournalEntry = (id: number) =>
  api.get(`/journal/entries/${id}`).then((r) => r.data)

export const createJournalEntry = (payload: unknown) =>
  api.post('/journal/entries', payload).then((r) => r.data)

export const updateJournalEntry = (id: number, payload: unknown) =>
  api.patch(`/journal/entries/${id}`, payload).then((r) => r.data)

export const deleteJournalEntry = (id: number) =>
  api.delete(`/journal/entries/${id}`).then((r) => r.data)

export const getPerformance = (params?: Record<string, unknown>) =>
  api.get('/journal/performance', { params }).then((r) => r.data)

// Calendar
export const listCalendarEvents = (params?: Record<string, unknown>) =>
  api.get('/calendar/events', { params }).then((r) => r.data)

export const createCalendarEvent = (payload: unknown) =>
  api.post('/calendar/events', payload).then((r) => r.data)

export const updateCalendarEvent = (id: number, payload: unknown) =>
  api.patch(`/calendar/events/${id}`, payload).then((r) => r.data)

export const deleteCalendarEvent = (id: number) =>
  api.delete(`/calendar/events/${id}`).then((r) => r.data)

export const getDailyPnL = (params?: Record<string, unknown>) =>
  api.get('/calendar/daily-pnl', { params }).then((r) => r.data)

// Bots
export const listBots = () => api.get('/bots').then((r) => r.data)

export const getBot = (id: string) => api.get(`/bots/${id}`).then((r) => r.data)

export const createBot = (payload: unknown) => api.post('/bots', payload).then((r) => r.data)

export const startBot = (id: string) => api.post(`/bots/${id}/start`).then((r) => r.data)

export const stopBot = (id: string) => api.post(`/bots/${id}/stop`).then((r) => r.data)

export const deleteBot = (id: string) => api.delete(`/bots/${id}`).then((r) => r.data)

// Agents
export const listAgentReports = (params?: Record<string, unknown>) =>
  api.get('/agents/reports', { params }).then((r) => r.data)

export const listAgentSignals = (params?: Record<string, unknown>) =>
  api.get('/agents/signals', { params }).then((r) => r.data)

export const listNewsSignals = (params?: Record<string, unknown>) =>
  api.get('/agents/news', { params }).then((r) => r.data)

export const getMacroRegimes = (params?: Record<string, unknown>) =>
  api.get('/agents/macro', { params }).then((r) => r.data)

export const runAgentNow = (agentType: string) =>
  api.post(`/agents/run/${agentType}`).then((r) => r.data)

export const getCouncilLatest = () =>
  api.get('/agents/council/latest').then((r) => r.data)

export const listMediaFeeds = () => api.get('/agents/feeds').then((r) => r.data)

export const addMediaFeed = (url: string) =>
  api.post('/agents/feeds', { url }).then((r) => r.data)

export const removeMediaFeed = (url: string) =>
  api.delete('/agents/feeds', { data: { url } }).then((r) => r.data)

// Brokers
export const listBrokerConnections = (params?: Record<string, unknown>) =>
  api.get('/brokers/connections', { params }).then((r) => r.data)

export const createBrokerConnection = (payload: unknown) =>
  api.post('/brokers/connections', payload).then((r) => r.data)

export const updateBrokerConnection = (id: number, payload: unknown) =>
  api.patch(`/brokers/connections/${id}`, payload).then((r) => r.data)

export const deleteBrokerConnection = (id: number) =>
  api.delete(`/brokers/connections/${id}`).then((r) => r.data)

export const testBrokerConnection = (id: number, masterPassword?: string) =>
  api.post(`/brokers/connections/${id}/test`, null, { params: { master_password: masterPassword } }).then((r) => r.data)

export const getBrokerWizardRecommend = (params: Record<string, string>) =>
  api.get('/brokers/wizard-recommend', { params }).then((r) => r.data)

// Performance (enhanced analytics)
export const getPerformanceSummary = (params?: Record<string, unknown>) =>
  api.get('/performance/summary', { params }).then((r) => r.data)

// Regime Detection
export const detectRegime = (assetId: number, window = 20) =>
  api.get(`/regime/detect/${assetId}`, { params: { window } }).then((r) => r.data)

export const getRegimeHistory = (assetId: number, window = 20, limit = 100) =>
  api.get(`/regime/history/${assetId}`, { params: { window, limit } }).then((r) => r.data)

// Strategies
export const listStrategies = () => api.get('/strategies').then((r) => r.data)

export const createStrategy = (payload: unknown) =>
  api.post('/strategies', payload).then((r) => r.data)

export const confirmBotLive = (id: string) =>
  api.post(`/bots/${id}/confirm-live`).then((r) => r.data)

// Backtest
export const runBacktest = (payload: unknown) =>
  api.post('/backtest/run', payload).then((r) => r.data)

export const getBacktest = (id: number) =>
  api.get(`/backtest/${id}`).then((r) => r.data)

export const listBacktests = (params?: Record<string, unknown>) =>
  api.get('/backtest', { params }).then((r) => r.data)

// Paper Trading
export const placePaperOrder = (payload: unknown) =>
  api.post('/paper/order', payload).then((r) => r.data)

export const getPaperSummary = () =>
  api.get('/paper/summary').then((r) => r.data)

export const listPaperOrders = () =>
  api.get('/paper/orders').then((r) => r.data)

export default api
