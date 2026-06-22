export interface Asset {
  id: number
  symbol: string
  name?: string
  asset_class: string
  exchange?: string
  data_source?: string
  is_active: boolean
  created_at?: string
}

export interface PriceBar {
  timestamp: string
  timeframe: string
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface Quote {
  timestamp: string
  bid?: number
  ask?: number
  last_price: number
  volume?: number
}

export interface Trade {
  id: number
  asset_id: number
  strategy_id?: number
  direction: 'long' | 'short'
  order_type: string
  entry_time: string
  exit_time?: string
  entry_price: number
  exit_price?: number
  size: number
  pnl?: number
  pnl_pct?: number
  commission: number
  slippage: number
  status: 'open' | 'closed' | 'cancelled'
  regime?: string
  notes?: string
  tags?: string[]
  is_paper: boolean
  external_order_id?: string
  created_at?: string
  updated_at?: string
}

export interface JournalEntry {
  id: number
  trade_id?: number
  entry_type: string
  content: string
  mood?: string
  mistakes?: string[]
  lessons?: string[]
  image_urls?: string[]
  created_at?: string
}

export interface Strategy {
  id: number
  name: string
  class_path: string
  params_schema?: Record<string, unknown>
  description?: string
  is_active: boolean
  is_builtin: boolean
  created_at?: string
}

export interface PerformanceSummary {
  total_trades: number
  win_count: number
  loss_count: number
  win_rate: number
  profit_factor: number
  sharpe_ratio?: number
  max_drawdown: number
  total_pnl: number
  avg_trade_pnl: number
  best_trade?: number
  worst_trade?: number
}

export interface CalendarEvent {
  id: number
  date: string
  event_type: string
  title?: string
  description?: string
  trade_ids?: number[]
  pnl_summary?: number
}
