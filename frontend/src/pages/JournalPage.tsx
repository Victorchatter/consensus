import { useEffect, useState, useMemo } from 'react'
import {
  listJournalEntries,
  createJournalEntry,
  updateJournalEntry,
  deleteJournalEntry,
  getPerformanceSummary,
  listTrades,
} from '@/services/api'
import type { JournalEntry, Trade } from '@/types'
import {
  Plus,
  Search,
  Calendar,
  Smile,
  Frown,
  Meh,
  Zap,
  Trash2,
  Edit3,
  Save,
  X,
  Link as LinkIcon,
  Image as ImageIcon,
  BookOpen,
} from 'lucide-react'

interface PerfReport {
  total_trades: number
  win_count: number
  loss_count: number
  win_rate: number
  profit_factor: number
  total_pnl: number
  avg_trade_pnl: number
  best_trade?: number
  worst_trade?: number
  max_drawdown: number
}

const MOODS = [
  { key: 'confident', label: 'Confident', icon: Zap },
  { key: 'calm', label: 'Calm', icon: Smile },
  { key: 'neutral', label: 'Neutral', icon: Meh },
  { key: 'anxious', label: 'Anxious', icon: Frown },
  { key: 'frustrated', label: 'Frustrated', icon: Frown },
]

const ENTRY_TYPES = [
  { key: 'note', label: 'Note' },
  { key: 'pre_trade', label: 'Pre-Trade' },
  { key: 'post_trade', label: 'Post-Trade' },
  { key: 'mistake', label: 'Mistake' },
  { key: 'lesson', label: 'Lesson' },
]

export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [report, setReport] = useState<PerfReport | null>(null)
  const [loading, setLoading] = useState(false)

  // Filters
  const [filterType, setFilterType] = useState('')
  const [filterMood, setFilterMood] = useState('')
  const [filterTradeId, setFilterTradeId] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterStart, setFilterStart] = useState('')
  const [filterEnd, setFilterEnd] = useState('')

  // Form state
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formContent, setFormContent] = useState('')
  const [formType, setFormType] = useState('note')
  const [formMood, setFormMood] = useState('')
  const [formTradeId, setFormTradeId] = useState('')
  const [formImages, setFormImages] = useState('')
  const [formMistakes, setFormMistakes] = useState('')
  const [formLessons, setFormLessons] = useState('')
  const [previewMode, setPreviewMode] = useState(false)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {}
      if (filterType) params.entry_type = filterType
      if (filterMood) params.mood = filterMood
      if (filterTradeId) params.trade_id = Number(filterTradeId)
      if (filterSearch) params.search = filterSearch
      if (filterStart) params.start_date = filterStart
      if (filterEnd) params.end_date = filterEnd

      const [entriesData, tradesData, perfData] = await Promise.all([
        listJournalEntries(params),
        listTrades(),
        getPerformanceSummary(),
      ])
      setEntries(entriesData)
      setTrades(tradesData)
      if (perfData?.report) setReport(perfData.report)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [filterType, filterMood, filterTradeId, filterStart, filterEnd])

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => fetchAll(), 400)
    return () => clearTimeout(t)
  }, [filterSearch])

  const resetForm = () => {
    setFormContent('')
    setFormType('note')
    setFormMood('')
    setFormTradeId('')
    setFormImages('')
    setFormMistakes('')
    setFormLessons('')
    setPreviewMode(false)
    setEditingId(null)
  }

  const openCreate = () => {
    resetForm()
    setShowForm(true)
  }

  const openEdit = (entry: JournalEntry) => {
    setEditingId(entry.id)
    setFormContent(entry.content)
    setFormType(entry.entry_type)
    setFormMood(entry.mood || '')
    setFormTradeId(entry.trade_id ? String(entry.trade_id) : '')
    setFormImages((entry.image_urls || []).join('\n'))
    setFormMistakes((entry.mistakes || []).join(', '))
    setFormLessons((entry.lessons || []).join(', '))
    setPreviewMode(false)
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!formContent.trim()) return
    const payload = {
      content: formContent,
      entry_type: formType,
      mood: formMood || null,
      trade_id: formTradeId ? Number(formTradeId) : null,
      image_urls: formImages
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
      mistakes: formMistakes
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      lessons: formLessons
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    }
    try {
      if (editingId) {
        await updateJournalEntry(editingId, payload)
      } else {
        await createJournalEntry(payload)
      }
      setShowForm(false)
      resetForm()
      fetchAll()
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this journal entry?')) return
    try {
      await deleteJournalEntry(id)
      fetchAll()
    } catch (e) {
      console.error(e)
    }
  }

  const linkedTrade = (tradeId?: number) => trades.find((t) => t.id === tradeId)

  return (
    <div className="p-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen size={24} className="text-accent" />
            Trading Journal
          </h2>
          <p className="text-sm text-muted mt-1">Log, review, and learn from every trade</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light transition-colors flex items-center gap-2"
        >
          <Plus size={16} />
          New Entry
        </button>
      </header>

      {/* Performance summary */}
      {report && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
          <MetricCard label="Win Rate" value={`${(report.win_rate * 100).toFixed(1)}%`} />
          <MetricCard label="Profit Factor" value={report.profit_factor.toFixed(2)} />
          <MetricCard label="Total P&L" value={`$${report.total_pnl.toFixed(0)}`} accent={report.total_pnl >= 0} />
          <MetricCard label="Max DD" value={`${report.max_drawdown.toFixed(1)}%`} danger />
          <MetricCard label="Avg Trade" value={`$${report.avg_trade_pnl.toFixed(2)}`} />
          <MetricCard label="Trades" value={String(report.total_trades)} />
        </div>
      )}

      {/* Filters */}
      <div className="bg-surface border border-border rounded-lg p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              placeholder="Search entries..."
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              className="w-full bg-bg border border-border rounded-md pl-8 pr-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-bg border border-border rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          {ENTRY_TYPES.map((t) => (
            <option key={t.key} value={t.key}>{t.label}</option>
          ))}
        </select>
        <select
          value={filterMood}
          onChange={(e) => setFilterMood(e.target.value)}
          className="bg-bg border border-border rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Moods</option>
          {MOODS.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>
        <select
          value={filterTradeId}
          onChange={(e) => setFilterTradeId(e.target.value)}
          className="bg-bg border border-border rounded-md px-3 py-2 text-sm"
        >
          <option value="">Any Trade</option>
          {trades.map((t) => (
            <option key={t.id} value={t.id}>
              #{t.id} {t.direction.toUpperCase()} {t.pnl !== undefined ? `($${t.pnl.toFixed(0)})` : ''}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={filterStart}
            onChange={(e) => setFilterStart(e.target.value)}
            className="bg-bg border border-border rounded-md px-2 py-2 text-sm"
          />
          <span className="text-muted text-xs">to</span>
          <input
            type="date"
            value={filterEnd}
            onChange={(e) => setFilterEnd(e.target.value)}
            className="bg-bg border border-border rounded-md px-2 py-2 text-sm"
          />
        </div>
      </div>

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-surface border border-border rounded-xl w-full max-w-2xl max-h-[90vh] overflow-auto shadow-xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h3 className="text-lg font-semibold">
                {editingId ? 'Edit Entry' : 'New Journal Entry'}
              </h3>
              <button onClick={() => setShowForm(false)} className="text-muted hover:text-text">
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-muted uppercase mb-1 block">Type</label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    {ENTRY_TYPES.map((t) => (
                      <option key={t.key} value={t.key}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted uppercase mb-1 block">Mood</label>
                  <select
                    value={formMood}
                    onChange={(e) => setFormMood(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="">Select...</option>
                    {MOODS.map((m) => (
                      <option key={m.key} value={m.key}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted uppercase mb-1 block">Linked Trade</label>
                  <select
                    value={formTradeId}
                    onChange={(e) => setFormTradeId(e.target.value)}
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  >
                    <option value="">None</option>
                    {trades.map((t) => (
                      <option key={t.id} value={t.id}>
                        #{t.id} {t.direction.toUpperCase()} ${t.entry_price}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setPreviewMode(false)}
                  className={`px-3 py-1 rounded text-xs font-medium ${!previewMode ? 'bg-accent text-bg' : 'bg-elevated text-muted'}`}
                >
                  Write
                </button>
                <button
                  onClick={() => setPreviewMode(true)}
                  className={`px-3 py-1 rounded text-xs font-medium ${previewMode ? 'bg-accent text-bg' : 'bg-elevated text-muted'}`}
                >
                  Preview
                </button>
              </div>

              {!previewMode ? (
                <textarea
                  value={formContent}
                  onChange={(e) => setFormContent(e.target.value)}
                  placeholder="Write your journal entry... Markdown supported."
                  rows={8}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono leading-relaxed focus:outline-none focus:border-accent"
                />
              ) : (
                <div className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm min-h-[160px] overflow-auto">
                  <MarkdownPreview text={formContent} />
                </div>
              )}

              <div>
                <label className="text-xs text-muted uppercase mb-1 block">Image URLs (one per line)</label>
                <textarea
                  value={formImages}
                  onChange={(e) => setFormImages(e.target.value)}
                  placeholder="https://example.com/chart1.png"
                  rows={2}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted uppercase mb-1 block">Mistakes (comma separated)</label>
                  <input
                    value={formMistakes}
                    onChange={(e) => setFormMistakes(e.target.value)}
                    placeholder="revenge trading, oversized position"
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted uppercase mb-1 block">Lessons (comma separated)</label>
                  <input
                    value={formLessons}
                    onChange={(e) => setFormLessons(e.target.value)}
                    placeholder="wait for confirmation, stick to plan"
                    className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-border bg-surface/50">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-md text-sm text-muted hover:text-text transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light transition-colors flex items-center gap-2"
              >
                <Save size={16} />
                Save Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Entries list */}
      <div className="space-y-4">
        {loading && entries.length === 0 && (
          <p className="text-muted text-sm">Loading entries...</p>
        )}
        {entries.map((entry) => {
          const trade = linkedTrade(entry.trade_id)
          return (
            <div
              key={entry.id}
              className="bg-elevated border border-border rounded-lg p-5 hover:border-border-hover transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-accent/10 text-accent font-semibold">
                    {entry.entry_type.replace('_', ' ')}
                  </span>
                  {entry.mood && (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-surface text-muted font-semibold flex items-center gap-1">
                      {MOODS.find((m) => m.key === entry.mood)?.icon && (
                        <span>{(() => {
                          const M = MOODS.find((m) => m.key === entry.mood)?.icon
                          return M ? <M size={10} /> : null
                        })()}</span>
                      )}
                      {entry.mood}
                    </span>
                  )}
                  {trade && (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-surface text-muted font-semibold flex items-center gap-1">
                      <LinkIcon size={10} />
                      Trade #{trade.id} {trade.direction.toUpperCase()} {' '}
                      {trade.pnl !== undefined ? `($${trade.pnl.toFixed(2)})` : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEdit(entry)}
                    className="text-muted hover:text-accent transition-colors"
                    title="Edit"
                  >
                    <Edit3 size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(entry.id)}
                    className="text-muted hover:text-danger transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="text-sm text-text leading-relaxed mb-3">
                <MarkdownPreview text={entry.content} />
              </div>

              {(entry.image_urls?.length ?? 0) > 0 && (
                <div className="flex gap-2 flex-wrap mb-3">
                  {entry.image_urls!.map((url, idx) => (
                    <a
                      key={idx}
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-accent hover:underline bg-accent/5 px-2 py-1 rounded"
                    >
                      <ImageIcon size={12} />
                      Image {idx + 1}
                    </a>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                {(entry.mistakes?.length ?? 0) > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-[10px] text-danger uppercase tracking-wider">Mistakes:</span>
                    {entry.mistakes!.map((m, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-danger/10 text-danger">
                        {m}
                      </span>
                    ))}
                  </div>
                )}
                {(entry.lessons?.length ?? 0) > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-[10px] text-accent uppercase tracking-wider">Lessons:</span>
                    {entry.lessons!.map((l, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">
                        {l}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-3 text-[11px] text-muted flex items-center gap-1">
                <Calendar size={11} />
                {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
              </div>
            </div>
          )
        })}
        {entries.length === 0 && !loading && (
          <div className="text-center py-12 text-muted">
            <BookOpen size={32} className="mx-auto mb-3 opacity-50" />
            <p className="text-sm">No journal entries yet.</p>
            <p className="text-xs mt-1">Click "New Entry" to log your first trade reflection.</p>
          </div>
        )}
      </div>
    </div>
  )
}

/* Simple markdown preview with basic XSS protection */
function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sanitizeUrl(url: string): string {
  const lower = url.trim().toLowerCase()
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
    return '#'
  }
  return url
}

function MarkdownPreview({ text }: { text: string }) {
  const html = useMemo(() => {
    if (!text) return ''
    let processed = escapeHtml(text)

    // Headers
    processed = processed.replace(/^### (.*$)/gim, '<h3 class="text-sm font-bold mt-2 mb-1">$1</h3>')
    processed = processed.replace(/^## (.*$)/gim, '<h2 class="text-base font-bold mt-2 mb-1">$1</h2>')
    processed = processed.replace(/^# (.*$)/gim, '<h1 class="text-lg font-bold mt-2 mb-1">$1</h1>')

    // Bold / italic
    processed = processed.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
    processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>')

    // Code
    processed = processed.replace(/`([^`]+)`/g, '<code class="bg-surface px-1 py-0.5 rounded text-xs font-mono">$1</code>')

    // Links — sanitize href to block javascript:/data: schemes
    processed = processed.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      (_, label: string, href: string) => {
        const safeHref = sanitizeUrl(href)
        return `<a href="${safeHref}" target="_blank" rel="noreferrer" class="text-accent hover:underline">${label}</a>`
      }
    )

    // Lists
    processed = processed.replace(/^\s*[-*] (.*$)/gim, '<li class="ml-4">$1</li>')

    // Line breaks
    processed = processed.replace(/\n/g, '<br />')

    return processed
  }, [text])

  return <div dangerouslySetInnerHTML={{ __html: html }} className="markdown-preview" />
}

function MetricCard({
  label,
  value,
  accent,
  danger,
}: {
  label: string
  value: string
  accent?: boolean
  danger?: boolean
}) {
  const color = danger ? 'text-danger' : accent ? 'text-accent' : 'text-text'
  return (
    <div className="bg-elevated border border-border rounded-lg p-4">
      <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  )
}
