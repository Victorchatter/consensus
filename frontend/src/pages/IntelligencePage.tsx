import { useEffect, useState } from 'react'
import {
  listAgentReports,
  listAgentSignals,
  listNewsSignals,
  getMacroRegimes,
  runAgentNow,
  getCouncilLatest,
  listMediaFeeds,
  addMediaFeed,
  removeMediaFeed,
} from '@/services/api'
import {
  Radar,
  RefreshCw,
  Zap,
  TrendingUp,
  Newspaper,
  Activity,
  Globe,
  AlertTriangle,
  Play,
  Link,
  Trash2,
  Plus,
} from 'lucide-react'

interface AgentReport {
  id: number
  agent_type: string
  timestamp: string
  summary: string
  bias_score?: number
  confidence?: number
  raw_data_json?: any
}

interface AgentSignal {
  id: number
  agent_type: string
  symbol?: string
  signal: string
  strength?: number
  created_at: string
  expires_at?: string
}

interface NewsSignal {
  id: number
  timestamp: string
  symbol?: string
  headline?: string
  sentiment_score?: number
  severity?: string
  source?: string
}

interface MacroRegime {
  id: number
  date: string
  regime_label?: string
  volatility_regime?: string
  trend_strength?: number
  confidence?: number
}

const AGENT_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  news_prodigy: { label: 'News Prodigy', icon: Newspaper, color: '#FFB800' },
  financial_analyst: { label: 'Financial Analyst', icon: TrendingUp, color: '#00D4AA' },
  economic_expert: { label: 'Economic Expert', icon: Globe, color: '#00BFFF' },
  economic_analyst: { label: 'Economic Analyst', icon: Globe, color: '#00BFFF' },
  political_analyst: { label: 'Political Analyst', icon: AlertTriangle, color: '#FF6B6B' },
  strategy_expert: { label: 'Strategy Expert', icon: Zap, color: '#9B59B6' },
  agent_council: { label: 'Agent Council', icon: Radar, color: '#00D4AA' },
  ceo_agent: { label: 'CEO Agent', icon: Radar, color: '#00D4AA' },
}

interface CouncilDecision {
  timestamp: string
  summary: string
  bias_score?: number
  confidence?: number
  raw_data_json?: {
    decision?: string
    risk_level?: string
    heartbeat?: string
    article_summaries?: Array<{ headline: string; source: string }>
    executed_trades?: Array<{
      asset_id: number
      symbol: string
      direction: string
      size: number
      entry_price: number
    }>
  }
}

export default function IntelligencePage() {
  const [reports, setReports] = useState<AgentReport[]>([])
  const [signals, setSignals] = useState<AgentSignal[]>([])
  const [news, setNews] = useState<NewsSignal[]>([])
  const [macro, setMacro] = useState<MacroRegime[]>([])
  const [council, setCouncil] = useState<CouncilDecision | null>(null)
  const [loading, setLoading] = useState(false)
  const [runningAgent, setRunningAgent] = useState<string | null>(null)
  const [feeds, setFeeds] = useState<string[]>([])
  const [newFeedUrl, setNewFeedUrl] = useState('')

  const fetchFeeds = async () => {
    try {
      const data = await listMediaFeeds()
      setFeeds(data.feeds || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleAddFeed = async () => {
    if (!newFeedUrl.trim()) return
    try {
      await addMediaFeed(newFeedUrl.trim())
      setNewFeedUrl('')
      await fetchFeeds()
    } catch (e) {
      console.error(e)
    }
  }

  const handleRemoveFeed = async (url: string) => {
    try {
      await removeMediaFeed(url)
      await fetchFeeds()
    } catch (e) {
      console.error(e)
    }
  }

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [r, s, n, m, c] = await Promise.all([
        listAgentReports({ limit: 50 }),
        listAgentSignals({ limit: 50 }),
        listNewsSignals({ limit: 30 }),
        getMacroRegimes({ limit: 30 }),
        getCouncilLatest().catch(() => null),
      ])
      setReports(r || [])
      setSignals(s || [])
      setNews(n || [])
      setMacro(m || [])
      if (c && !c.error) setCouncil(c)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    fetchFeeds()
    const interval = setInterval(fetchAll, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleRunAgent = async (agentType: string) => {
    setRunningAgent(agentType)
    try {
      await runAgentNow(agentType)
      await fetchAll()
    } catch (e) {
      console.error(e)
    } finally {
      setRunningAgent(null)
    }
  }

  // Aggregate sentiment per symbol
  const symbolSentiment: Record<string, number[]> = {}
  news.forEach((n) => {
    if (n.symbol && n.sentiment_score !== undefined) {
      symbolSentiment[n.symbol] = symbolSentiment[n.symbol] || []
      symbolSentiment[n.symbol].push(n.sentiment_score)
    }
  })

  return (
    <div className="p-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Radar size={24} className="text-accent" />
            Intelligence
          </h2>
          <p className="text-sm text-muted mt-1">
            Agent swarm outputs, macro regimes, and sentiment gauges
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAll}
            className="bg-elevated border border-border hover:border-border-hover text-muted hover:text-text px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </header>

      {/* Sentiment gauges */}
      {Object.keys(symbolSentiment).length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3">News Sentiment</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            {Object.entries(symbolSentiment).map(([sym, scores]) => {
              const avg = scores.reduce((a, b) => a + b, 0) / scores.length
              return (
                <div key={sym} className="bg-elevated border border-border rounded-lg p-4">
                  <div className="text-xs text-muted uppercase tracking-wider mb-1">{sym}</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, Math.max(0, (avg + 1) * 50))}%`,
                          backgroundColor: avg > 0.1 ? '#00D4AA' : avg < -0.1 ? '#FF4757' : '#8A8A98',
                        }}
                      />
                    </div>
                    <span className="text-xs font-mono w-8 text-right">{avg.toFixed(2)}</span>
                  </div>
                  <div className="text-[10px] text-muted mt-1">{scores.length} headlines</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* CEO Decision Banner */}
      {council && (
        <div className="mb-6 bg-elevated border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold uppercase tracking-wider text-accent">CEO Agent — Latest Decision</h3>
            <span className="text-[10px] text-muted">{council.timestamp ? new Date(council.timestamp).toLocaleString() : '—'}</span>
          </div>
          <p className="text-sm text-text mb-2">{council.summary}</p>
          {council.raw_data_json?.article_summaries && council.raw_data_json.article_summaries.length > 0 && (
            <div className="mb-2 space-y-1">
              <span className="text-[10px] uppercase text-muted">Key Headlines</span>
              {council.raw_data_json.article_summaries.slice(0, 6).map((a, i) => (
                <div key={i} className="flex items-start gap-2 text-xs bg-surface border border-border rounded-md px-2 py-1">
                  <span className="text-muted shrink-0">{a.source}</span>
                  <span className="text-text">{a.headline}</span>
                </div>
              ))}
            </div>
          )}
          {council.raw_data_json?.heartbeat && (
            <div className="mb-2 px-3 py-2 bg-accent/5 border border-accent/20 rounded-md text-sm text-accent">
              <span className="font-semibold">Heartbeat:</span> {council.raw_data_json.heartbeat}
            </div>
          )}
          {council.raw_data_json?.executed_trades && council.raw_data_json.executed_trades.length > 0 && (
            <div className="mb-2 space-y-1">
              <span className="text-[10px] uppercase text-muted">Executed Trades</span>
              {council.raw_data_json.executed_trades.map((t, i) => (
                <div key={i} className="flex items-center gap-2 text-xs bg-surface border border-border rounded-md px-2 py-1">
                  <span className="font-mono font-semibold">{t.symbol}</span>
                  <span className={`text-[10px] px-1 rounded ${t.direction === 'long' ? 'bg-accent/10 text-accent' : 'bg-danger/10 text-danger'}`}>
                    {t.direction.toUpperCase()}
                  </span>
                  <span className="text-muted">{t.size.toFixed(4)} @ ${t.entry_price.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-3 text-[10px]">
            <span className={`px-1.5 py-0.5 rounded font-semibold ${
              council.raw_data_json?.risk_level === 'critical' ? 'bg-danger/10 text-danger' :
              council.raw_data_json?.risk_level === 'high' ? 'bg-warning/10 text-warning' :
              council.raw_data_json?.risk_level === 'medium' ? 'bg-accent/10 text-accent' :
              'bg-muted/10 text-muted'
            }`}>
              Risk: {council.raw_data_json?.risk_level?.toUpperCase() || 'UNKNOWN'}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-surface text-muted font-semibold">
              Confidence: {(council.confidence || 0).toFixed(0)}%
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent report feed */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted">Agent Reports</h3>
            <div className="flex gap-2 flex-wrap">
              {['news_prodigy', 'financial_analyst', 'economic_analyst', 'political_analyst', 'ceo_agent'].map((agent) => (
                <button
                  key={agent}
                  onClick={() => handleRunAgent(agent)}
                  disabled={runningAgent === agent}
                  className="flex items-center gap-1 bg-accent/10 text-accent hover:bg-accent/20 px-2 py-1 rounded text-xs font-medium transition-colors disabled:opacity-50"
                >
                  <Play size={10} />
                  {runningAgent === agent ? 'Running...' : `Run ${AGENT_META[agent]?.label || agent}`}
                </button>
              ))}
              <button
                onClick={async () => {
                  setRunningAgent('all')
                  try {
                    for (const agent of ['news_prodigy', 'financial_analyst', 'economic_analyst', 'political_analyst', 'ceo_agent']) {
                      await runAgentNow(agent)
                      await new Promise((r) => setTimeout(r, 2000)) // stagger to avoid overload
                    }
                    await fetchAll()
                  } catch (e) {
                    console.error(e)
                  } finally {
                    setRunningAgent(null)
                  }
                }}
                disabled={runningAgent === 'all'}
                className="flex items-center gap-1 bg-warning/10 text-warning hover:bg-warning/20 px-2 py-1 rounded text-xs font-medium transition-colors disabled:opacity-50"
              >
                <Play size={10} />
                {runningAgent === 'all' ? 'Running all...' : 'Run All Agents'}
              </button>
            </div>
          </div>

          {reports.map((report) => {
            const meta = AGENT_META[report.agent_type] || {
              label: report.agent_type,
              icon: Activity,
              color: '#8A8A98',
            }
            const Icon = meta.icon
            return (
              <div
                key={report.id}
                className="bg-elevated border border-border rounded-lg p-4 hover:border-border-hover transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon size={14} style={{ color: meta.color }} />
                  <span className="text-xs font-semibold" style={{ color: meta.color }}>
                    {meta.label}
                  </span>
                  <span className="text-[10px] text-muted">
                    {new Date(report.timestamp).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm text-text">{report.summary}</p>
                {(report.bias_score !== undefined || report.confidence !== undefined) && (
                  <div className="flex gap-3 mt-2">
                    {report.bias_score !== undefined && (
                      <div className="text-[10px] text-muted">
                        Bias: {' '}
                        <span
                          className={`font-semibold ${
                            report.bias_score > 50 ? 'text-accent' : report.bias_score < 50 ? 'text-danger' : ''
                          }`}
                        >
                          {report.bias_score.toFixed(0)}
                        </span>
                      </div>
                    )}
                    {report.confidence !== undefined && (
                      <div className="text-[10px] text-muted">
                        Confidence: {' '}
                        <span className="font-semibold text-text">{report.confidence.toFixed(0)}%</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
          {reports.length === 0 && !loading && (
            <div className="text-center py-8 text-muted">
              <Radar size={24} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">No agent reports yet.</p>
              <p className="text-xs mt-1">Agents run on a schedule and will populate this feed.</p>
            </div>
          )}
        </div>

        {/* Sidebar: signals + macro */}
        <div className="space-y-6">
          {/* Active signals */}
          <div className="bg-elevated border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3">Active Signals</h3>
            <div className="space-y-2">
              {signals.map((sig) => {
                const bullish = sig.signal === 'bullish'
                const bearish = sig.signal === 'bearish'
                return (
                  <div key={sig.id} className="flex items-center justify-between bg-surface border border-border rounded-md px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs">{sig.symbol || '—'}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                          bullish
                            ? 'bg-accent/10 text-accent'
                            : bearish
                            ? 'bg-danger/10 text-danger'
                            : 'bg-muted/10 text-muted'
                        }`}
                      >
                        {sig.signal.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-surface rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent"
                          style={{ width: `${(sig.strength || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-muted">
                        {((sig.strength || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                )
              })}
              {signals.length === 0 && (
                <p className="text-xs text-muted">No active signals.</p>
              )}
            </div>
          </div>

          {/* Macro regime timeline */}
          <div className="bg-elevated border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3 flex items-center gap-1">
              <Globe size={12} /> Macro Regimes
            </h3>
            <div className="space-y-2 max-h-64 overflow-auto">
              {macro.map((m) => (
                <div key={m.id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted">{m.date}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                        m.regime_label === 'TRENDING'
                          ? 'bg-accent/10 text-accent'
                          : m.regime_label === 'RANGING'
                          ? 'bg-warning/10 text-warning'
                          : m.regime_label === 'VOLATILE'
                          ? 'bg-danger/10 text-danger'
                          : 'bg-muted/10 text-muted'
                      }`}
                    >
                      {m.regime_label || 'UNKNOWN'}
                    </span>
                  </div>
                  {m.confidence !== undefined && (
                    <span className="text-[10px] text-muted">{(m.confidence * 100).toFixed(0)}%</span>
                  )}
                </div>
              ))}
              {macro.length === 0 && (
                <p className="text-xs text-muted">No macro regime data.</p>
              )}
            </div>
          </div>

          {/* Recent headlines */}
          <div className="bg-elevated border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3 flex items-center gap-1">
              <Newspaper size={12} /> Recent Headlines
            </h3>
            <div className="space-y-2 max-h-64 overflow-auto">
              {news.slice(0, 10).map((n) => (
                <div key={n.id} className="bg-surface border border-border rounded-md p-2.5">
                  <div className="text-xs text-text leading-snug">{n.headline || '—'}</div>
                  <div className="flex items-center justify-between mt-1">
                    <div className="flex items-center gap-1">
                      {n.symbol && <span className="text-[10px] text-muted font-mono">{n.symbol}</span>}
                      <span
                        className={`text-[10px] px-1 py-0.5 rounded ${
                          n.severity === 'critical'
                            ? 'bg-danger/10 text-danger'
                            : n.severity === 'high'
                            ? 'bg-warning/10 text-warning'
                            : 'bg-muted/10 text-muted'
                        }`}
                      >
                        {n.severity || 'low'}
                      </span>
                    </div>
                    {n.sentiment_score !== undefined && (
                      <span
                        className={`text-[10px] font-mono ${
                          n.sentiment_score > 0 ? 'text-accent' : n.sentiment_score < 0 ? 'text-danger' : 'text-muted'
                        }`}
                      >
                        {n.sentiment_score > 0 ? '+' : ''}
                        {n.sentiment_score.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {news.length === 0 && (
                <p className="text-xs text-muted">No news signals yet.</p>
              )}
            </div>
          </div>

          {/* Media Sources */}
          <div className="bg-elevated border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3 flex items-center gap-1">
              <Link size={12} /> Media Sources
            </h3>
            <div className="space-y-2 max-h-48 overflow-auto">
              {feeds.map((url) => (
                <div key={url} className="flex items-center justify-between bg-surface border border-border rounded-md px-2 py-1.5">
                  <span className="text-[10px] text-text truncate flex-1 mr-2">{url}</span>
                  <button
                    onClick={() => handleRemoveFeed(url)}
                    className="text-muted hover:text-danger transition-colors"
                    title="Remove feed"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
              {feeds.length === 0 && <p className="text-xs text-muted">No custom feeds configured.</p>}
            </div>
            <div className="flex gap-2 mt-3">
              <input
                type="text"
                value={newFeedUrl}
                onChange={(e) => setNewFeedUrl(e.target.value)}
                placeholder="https://example.com/feed.xml"
                className="flex-1 bg-bg border border-border rounded-md px-2 py-1.5 text-xs text-text placeholder-muted focus:outline-none focus:border-accent"
              />
              <button
                onClick={handleAddFeed}
                disabled={!newFeedUrl.trim()}
                className="bg-accent/10 text-accent hover:bg-accent/20 px-2 py-1.5 rounded-md text-xs font-medium transition-colors disabled:opacity-50"
              >
                <Plus size={12} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
