import { useEffect, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import {
  listTrades,
  listJournalEntries,
  listCalendarEvents,
  createCalendarEvent,
  deleteCalendarEvent,
  getDailyPnL,
} from '@/services/api'
import type { Trade, JournalEntry } from '@/types'
import {
  Plus,
  X,
  Calendar as CalendarIcon,
  TrendingUp,
  TrendingDown,
  Minus,
  BookOpen,
  AlertCircle,
} from 'lucide-react'

interface CalendarEvent {
  id: number
  date: string
  event_type: string
  title?: string
  description?: string
  trade_ids?: number[]
  pnl_summary?: number
}

interface DailyPnL {
  date: string
  realized_pnl: number
  total_trades: number
  win_count: number
  loss_count: number
}

export default function CalendarPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([])
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([])
  const [dailyPnL, setDailyPnL] = useState<DailyPnL[]>([])
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [showEventForm, setShowEventForm] = useState(false)
  const [eventTitle, setEventTitle] = useState('')
  const [eventType, setEventType] = useState('economic_event')
  const [eventDesc, setEventDesc] = useState('')

  // Fetch all data on mount
  useEffect(() => {
    const calEnd = new Date()
    calEnd.setMonth(calEnd.getMonth() + 12)
    const calStart = new Date()
    calStart.setMonth(calStart.getMonth() - 3)
    const pnlEnd = new Date()
    const pnlStart = new Date()
    pnlStart.setMonth(pnlStart.getMonth() - 3)

    Promise.all([
      listTrades({ status: 'closed' }),
      listCalendarEvents({
        start_date: calStart.toISOString().split('T')[0],
        end_date: calEnd.toISOString().split('T')[0],
      }),
      getDailyPnL({
        start_date: pnlStart.toISOString().split('T')[0],
        end_date: pnlEnd.toISOString().split('T')[0],
      }),
    ]).then(([tradesData, eventsData, pnlData]) => {
      setTrades(tradesData)
      setCalendarEvents(eventsData)
      setDailyPnL(pnlData)
    })
  }, [])

  // Fetch journal entries when date selected
  useEffect(() => {
    if (!selectedDate) {
      setJournalEntries([])
      return
    }
    listJournalEntries({
      start_date: selectedDate,
      end_date: selectedDate,
    }).then(setJournalEntries)
  }, [selectedDate])

  const pnlMap = new Map<string, number>()
  dailyPnL.forEach((d) => pnlMap.set(d.date, d.realized_pnl))

  const tradeMap = new Map<string, Trade[]>()
  trades.forEach((t) => {
    const d = t.exit_time?.split('T')[0] || t.entry_time.split('T')[0]
    if (!tradeMap.has(d)) tradeMap.set(d, [])
    tradeMap.get(d)!.push(t)
  })

  const events = [
    // Trade events
    ...trades
      .filter((t) => t.exit_time)
      .map((t) => {
        const date = t.exit_time!.split('T')[0]
        const profit = (t.pnl ?? 0) >= 0
        return {
          id: `trade-${t.id}`,
          title: `${t.direction.toUpperCase().slice(0, 1)} ${profit ? '+' : ''}$${(t.pnl ?? 0).toFixed(0)}`,
          date,
          backgroundColor: profit ? 'rgba(0, 212, 170, 0.2)' : 'rgba(255, 71, 87, 0.2)',
          borderColor: profit ? '#00D4AA' : '#FF4757',
          textColor: profit ? '#00D4AA' : '#FF4757',
          extendedProps: { trade: t },
        }
      }),
    // Calendar events
    ...calendarEvents.map((ev) => ({
      id: `event-${ev.id}`,
      title: ev.title || ev.event_type,
      date: ev.date,
      backgroundColor: 'rgba(255, 184, 0, 0.15)',
      borderColor: '#FFB800',
      textColor: '#FFB800',
      extendedProps: { event: ev },
    })),
  ]

  const dayTrades = selectedDate ? tradeMap.get(selectedDate) || [] : []
  const dayEvents = selectedDate
    ? calendarEvents.filter((e) => e.date === selectedDate)
    : []
  const dayPnl = pnlMap.get(selectedDate || '') ?? dayTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0)
  const dayWins = dayTrades.filter((t) => (t.pnl ?? 0) > 0).length
  const dayLosses = dayTrades.filter((t) => (t.pnl ?? 0) <= 0).length

  const dayCellDidMount = (arg: any) => {
    const dateStr = arg.date.toISOString().split('T')[0]
    const pnl = pnlMap.get(dateStr)
    if (pnl !== undefined) {
      if (pnl > 0) {
        arg.el.style.backgroundColor = 'rgba(0, 212, 170, 0.06)'
      } else if (pnl < 0) {
        arg.el.style.backgroundColor = 'rgba(255, 71, 87, 0.06)'
      }
    }
    // Add a small dot if there are trades
    const dayTradeList = tradeMap.get(dateStr)
    if (dayTradeList && dayTradeList.length > 0) {
      const dot = document.createElement('div')
      const allProfit = dayTradeList.every((t) => (t.pnl ?? 0) >= 0)
      const allLoss = dayTradeList.every((t) => (t.pnl ?? 0) < 0)
      dot.className = 'absolute bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full'
      dot.style.backgroundColor = allProfit ? '#00D4AA' : allLoss ? '#FF4757' : '#8A8A98'
      arg.el.querySelector('.fc-daygrid-day-top')?.appendChild(dot)
    }
  }

  // Wider fetch window: 3 months past → 12 months future so events don't disappear
  const fetchCalendarEvents = async () => {
    const end = new Date()
    end.setMonth(end.getMonth() + 12)
    const start = new Date()
    start.setMonth(start.getMonth() - 3)
    const eventsData = await listCalendarEvents({
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
    })
    setCalendarEvents(eventsData)
  }

  const handleAddEvent = async () => {
    if (!selectedDate || !eventTitle.trim()) return
    try {
      await createCalendarEvent({
        date: selectedDate,
        event_type: eventType,
        title: eventTitle,
        description: eventDesc,
      })
      setShowEventForm(false)
      setEventTitle('')
      setEventDesc('')
      setEventType('economic_event')
      await fetchCalendarEvents()
    } catch (e) {
      console.error(e)
    }
  }

  const handleDeleteEvent = async (id: number) => {
    if (!confirm('Delete this event?')) return
    try {
      await deleteCalendarEvent(id)
      setCalendarEvents((prev) => prev.filter((e) => e.id !== id))
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="p-8 flex gap-6 h-full">
      <div className="flex-1 min-w-0">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Trading Calendar</h2>
            <p className="text-sm text-muted mt-1">Visualize your trades, P&L, and important events by day</p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-accent"></span> Profit Day
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-danger"></span> Loss Day
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-warning"></span> Event
            </span>
          </div>
        </header>

        <div className="bg-elevated border border-border rounded-lg p-4">
          <style>{`
            .fc { font-family: 'Inter', system-ui, sans-serif; }
            .fc-theme-standard td, .fc-theme-standard th { border-color: #2A2A35; }
            .fc-theme-standard .fc-scrollgrid { border-color: #2A2A35; }
            .fc .fc-toolbar-title { color: #E8E8EC; font-size: 1.1rem; font-weight: 600; }
            .fc .fc-button-primary {
              background-color: #1E1E26;
              border-color: #2A2A35;
              color: #8A8A98;
            }
            .fc .fc-button-primary:hover {
              background-color: #2A2A35;
              border-color: #3A3A48;
              color: #E8E8EC;
            }
            .fc .fc-button-primary:not(:disabled).fc-button-active,
            .fc .fc-button-primary:not(:disabled):active {
              background-color: #00D4AA;
              border-color: #00D4AA;
              color: #0B0B0F;
            }
            .fc-daygrid-day-number { color: #8A8A98; }
            .fc-day-today { background-color: rgba(0, 212, 170, 0.08) !important; }
            .fc-daygrid-day-top { padding: 4px; position: relative; }
            .fc-event { font-size: 0.7rem; padding: 1px 4px; border-radius: 3px; }
            .fc-daygrid-event-harness { margin: 1px 0; }
            .fc-daygrid-day-frame { min-height: 80px; position: relative; }
          `}</style>
          <FullCalendar
            plugins={[dayGridPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            events={events}
            dateClick={(info) => setSelectedDate(info.dateStr)}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,dayGridWeek',
            }}
            height="auto"
            dayCellClassNames="hover:bg-surface/30 cursor-pointer"
            eventDisplay="block"
            dayCellDidMount={dayCellDidMount}
          />
        </div>
      </div>

      {/* Day detail sidebar */}
      <div className="w-80 bg-elevated border border-border rounded-lg p-5 flex flex-col h-full overflow-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted">
            {selectedDate ? (
              <span className="flex items-center gap-2">
                <CalendarIcon size={14} />
                {selectedDate}
              </span>
            ) : (
              'Select a day'
            )}
          </h3>
          {selectedDate && (
            <button
              onClick={() => setShowEventForm(true)}
              className="text-xs flex items-center gap-1 bg-accent/10 text-accent px-2 py-1 rounded hover:bg-accent/20 transition-colors"
            >
              <Plus size={12} /> Add Event
            </button>
          )}
        </div>

        {selectedDate ? (
          <>
            {/* Summary */}
            <div className="mb-4 grid grid-cols-2 gap-3">
              <div className="bg-surface border border-border rounded-md p-3">
                <div className="text-[10px] text-muted uppercase">Day P&L</div>
                <div className={`text-xl font-bold flex items-center gap-1 ${dayPnl >= 0 ? 'text-accent' : 'text-danger'}`}>
                  {dayPnl >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                  {dayPnl >= 0 ? '+' : ''}${dayPnl.toFixed(2)}
                </div>
              </div>
              <div className="bg-surface border border-border rounded-md p-3">
                <div className="text-[10px] text-muted uppercase">Trades</div>
                <div className="text-xl font-bold text-text">{dayTrades.length}</div>
                <div className="text-[10px] text-muted mt-1">
                  <span className="text-accent">{dayWins}W</span> / <span className="text-danger">{dayLosses}L</span>
                </div>
              </div>
            </div>

            {/* Manual events */}
            {dayEvents.length > 0 && (
              <div className="mb-4 space-y-2">
                <h4 className="text-[10px] uppercase tracking-wider text-muted flex items-center gap-1">
                  <AlertCircle size={10} /> Events
                </h4>
                {dayEvents.map((ev) => (
                  <div key={ev.id} className="bg-surface border border-border rounded-md p-2.5 flex items-start justify-between">
                    <div>
                      <div className="text-xs font-semibold text-warning">{ev.title || ev.event_type}</div>
                      {ev.description && <div className="text-[11px] text-muted mt-0.5">{ev.description}</div>}
                    </div>
                    <button
                      onClick={() => handleDeleteEvent(ev.id)}
                      className="text-muted hover:text-danger transition-colors"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Trades */}
            {dayTrades.length > 0 && (
              <div className="mb-4 space-y-2">
                <h4 className="text-[10px] uppercase tracking-wider text-muted">Trades</h4>
                {dayTrades.map((t) => (
                  <div key={t.id} className="bg-surface border border-border rounded-md p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-sm">Asset #{t.asset_id}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        t.direction === 'long' ? 'bg-accent/10 text-accent' : 'bg-danger/10 text-danger'
                      }`}>
                        {t.direction.toUpperCase()}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-muted">
                      Entry ${t.entry_price.toFixed(2)} → Exit ${t.exit_price?.toFixed(2) || '—'}
                    </div>
                    <div className={`text-sm font-mono font-semibold mt-1 ${(t.pnl ?? 0) >= 0 ? 'text-accent' : 'text-danger'}`}>
                      {(t.pnl ?? 0) >= 0 ? '+' : ''}${(t.pnl ?? 0).toFixed(2)}
                    </div>
                    {t.notes && (
                      <div className="mt-2 text-xs text-muted italic border-t border-border pt-2">{t.notes}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Journal entries */}
            {journalEntries.length > 0 && (
              <div className="mb-4 space-y-2">
                <h4 className="text-[10px] uppercase tracking-wider text-muted flex items-center gap-1">
                  <BookOpen size={10} /> Journal Entries
                </h4>
                {journalEntries.map((entry) => (
                  <div key={entry.id} className="bg-surface border border-border rounded-md p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-accent/10 text-accent font-semibold">
                        {entry.entry_type.replace('_', ' ')}
                      </span>
                      {entry.mood && <span className="text-[10px] text-muted">{entry.mood}</span>}
                    </div>
                    <div className="text-xs text-text leading-relaxed">{entry.content.slice(0, 120)}{entry.content.length > 120 ? '...' : ''}</div>
                  </div>
                ))}
              </div>
            )}

            {dayTrades.length === 0 && dayEvents.length === 0 && journalEntries.length === 0 && (
              <div className="text-center py-8">
                <Minus size={24} className="mx-auto mb-2 text-muted opacity-50" />
                <p className="text-sm text-muted">No activity on this date.</p>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-muted">Click a day on the calendar to see details.</p>
          </div>
        )}
      </div>

      {/* Add Event Modal */}
      {showEventForm && selectedDate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-surface border border-border rounded-xl w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h3 className="text-base font-semibold">Add Calendar Event</h3>
              <button onClick={() => setShowEventForm(false)} className="text-muted hover:text-text">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-3">
              <div className="text-xs text-muted mb-1">Date: {selectedDate}</div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Title</label>
                <input
                  value={eventTitle}
                  onChange={(e) => setEventTitle(e.target.value)}
                  placeholder="FOMC Meeting, Earnings Alert..."
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Type</label>
                <select
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value)}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm"
                >
                  <option value="economic_event">Economic Event</option>
                  <option value="earnings">Earnings</option>
                  <option value="note">Note</option>
                  <option value="holiday">Holiday / Market Closed</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted uppercase block mb-1">Description</label>
                <textarea
                  value={eventDesc}
                  onChange={(e) => setEventDesc(e.target.value)}
                  rows={3}
                  className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-border bg-surface/50">
              <button
                onClick={() => setShowEventForm(false)}
                className="px-3 py-2 rounded-md text-sm text-muted hover:text-text"
              >
                Cancel
              </button>
              <button
                onClick={handleAddEvent}
                className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light"
              >
                Add Event
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
