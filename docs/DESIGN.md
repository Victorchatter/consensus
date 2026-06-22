---
name: EchoTrader
description: Professional local-first algorithmic trading platform with real-time charting, journal, and self-learning strategies.
colors:
  bg: "#0B0B0F"
  surface: "#141419"
  elevated: "#1E1E26"
  accent: "#00D4AA"
  accent-light: "#5FFFD4"
  danger: "#FF4757"
  warning: "#FFA502"
  info: "#1E90FF"
  text: "#E8E8EC"
  muted: "#8A8A98"
  dim: "#5A5A68"
  border: "#2A2A35"
  border-hover: "#3A3A48"
typography:
  display:
    fontFamily: "Inter, system-ui, sans-serif"
    fontWeight: 700
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontWeight: 600
    fontSize: "clamp(1.5rem, 3vw, 2.25rem)"
    lineHeight: 1.2
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontWeight: 600
    fontSize: "1.125rem"
    lineHeight: 1.3
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontWeight: 400
    fontSize: "0.9375rem"
    lineHeight: 1.5
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontWeight: 500
    fontSize: "0.6875rem"
    letterSpacing: "0.06em"
    textTransform: "uppercase"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontWeight: 500
    fontSize: "0.8125rem"
    lineHeight: 1.4
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.bg}"
    rounded: "{rounded.md}"
    padding: "10px 24px"
    fontWeight: 600
  button-primary-hover:
    backgroundColor: "{colors.accent-light}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    border: "1px solid {colors.border}"
    rounded: "{rounded.md}"
    padding: "10px 24px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "#fff"
    rounded: "{rounded.md}"
    padding: "10px 24px"
  card:
    backgroundColor: "{colors.elevated}"
    rounded: "{rounded.lg}"
    padding: "24px"
    border: "1px solid {colors.border}"
  sidebar:
    backgroundColor: "{colors.surface}"
    width: "240px"
    borderRight: "1px solid {colors.border}"
  chart-panel:
    backgroundColor: "{colors.bg}"
    border: "1px solid {colors.border}"
    rounded: "{rounded.lg}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    border: "1px solid {colors.border}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    focusBorder: "{colors.accent}"
  table-header:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    fontSize: "{typography.label.fontSize}"
    letterSpacing: "{typography.label.letterSpacing}"
    textTransform: "uppercase"
  positive:
    textColor: "{colors.accent}"
  negative:
    textColor: "{colors.danger}"
---

## UI Layout

```
+------------------------------------------+
|  Logo   Dashboard  Charts  Journal  ...   |  <- Top nav (48px)
+----------+-------------------------------+
|          |                               |
| Sidebar  |        Main Content           |
| (240px)  |        (expandable)           |
|          |                               |
| Assets   |    Chart / Journal / etc      |
| Watchlist|                               |
|          |                               |
+----------+-------------------------------+
```

## Pages

1. **Dashboard** — Portfolio overview, active strategies, P&L summary, recent trades
2. **ChartPage** — Expandable chart panel, asset selector, timeframe buttons, indicator toggles
3. **JournalPage** — Trade table, filters (date, strategy, asset, tag), P&L stats
4. **CalendarPage** — Monthly calendar with trade markers, day-detail sidebar
5. **StrategyPage** — Strategy list, configurator, backtest launcher, results viewer
6. **SettingsPage** — API keys, exchange connections, risk limits, theme toggle

## Chart Behavior

- Click asset in sidebar → chart panel populates with that symbol
- Chart is full-width, ~65vh height, resizable
- Toolbar: timeframe selector (1m/5m/15m/1H/4H/1D/1W), indicator toggles
- Live mode: WebSocket ticks update last bar in real time
- Historical: fetch bars on timeframe change or scroll

## Interactive States

- **Loading**: Skeleton screens (shimmer on dark surface)
- **Error**: Red toast notification, inline retry button
- **Success**: Green brief toast
- **Pending order**: Orange pulse indicator on position row
- **Live trading active**: Red "LIVE" badge in header with confirmation tooltip
