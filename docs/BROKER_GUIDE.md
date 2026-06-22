# Broker & Exchange Connectivity Guide

## Overview

EchoTrader connects to exchanges via API keys (not wallet private keys). Your keys are stored in the local `.env` file and used only by the backend. They never travel to the frontend or any cloud service.

---

## Recommended Platforms by Asset Class

### US Stocks & ETFs

**Primary: Alpaca** ⭐
- URL: https://alpaca.markets
- Commission-free trading
- Free real-time market data WebSocket
- Excellent Python SDK (`alpaca-py`)
- Paper trading environment (free)
- Covers NYSE, NASDAQ, ETFs

**Setup:**
1. Sign up at alpaca.markets
2. Generate API key + secret from dashboard
3. Paper trading is enabled by default — perfect for testing
4. Add to `.env`:
   ```
   ALPACA_API_KEY=PKXXXXXXXXXXXXXXXX
   ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ALPACA_PAPER=true
   ```

### Cryptocurrency

**Primary: Binance** ⭐
- URL: https://binance.com
- Deepest liquidity globally
- Free real-time WebSocket streams
- CCXT unified support
- Testnet available for paper trading

**Alternative: Coinbase Advanced Trade**
- URL: https://www.coinbase.com/advanced-trade
- Regulated US exchange
- Good API, slightly higher fees

**Setup (Binance):**
1. Create account, enable API management
2. Generate API key with "Spot Trading" permission
3. For paper trading, use testnet: https://testnet.binance.vision/
4. Add to `.env`:
   ```
   BINANCE_API_KEY=xxxxxxxxxxxxxxxx
   BINANCE_SECRET_KEY=xxxxxxxxxxxxxxxx
   BINANCE_TESTNET=true
   ```

**Important:** For crypto trading, you deposit funds to the exchange wallet — the bot uses exchange API keys to trade on your behalf. Do NOT give the bot withdrawal permissions.

### Forex & CFDs

**Primary: OANDA**
- URL: https://www.oanda.com
- Regulated (FCA, CFTC)
- REST API v20
- Demo account available

**Alternative: IG**
- URL: https://www.ig.com
- Good API documentation
- Wide range of CFDs

### Global Multi-Asset (Advanced)

**Interactive Brokers (IBKR)**
- URL: https://www.interactivebrokers.com
- Stocks, options, futures, forex, bonds, funds worldwide
- TWS API (slightly complex but very complete)
- PaperTrader account available
- Best for traders who want everything in one account

---

## Unified Exchange Access via CCXT

EchoTrader uses the **CCXT** library as a unified abstraction layer. This means:

- One code interface for 100+ exchanges
- Standardized order types: market, limit, stop-loss
- Automatic rate limiting
- Built-in error handling for exchange-specific quirks

Supported exchanges include: Binance, Coinbase, Kraken, KuCoin, Bybit, Bitfinex, OKX, and many more.

---

## Security Checklist

- [ ] Create dedicated API keys for EchoTrader (do not reuse keys from other apps)
- [ ] Enable IP restrictions on exchange API keys if possible (restrict to your home IP)
- [ ] Never enable "Withdrawal" permission on API keys used for trading bots
- [ ] Use paper/testnet trading for at least 2 weeks before going live
- [ ] Store `.env` file in a secure location; it is gitignored by default
- [ ] Back up your `.env` file externally (password manager, encrypted storage)

---

## Going Live

EchoTrader defaults to **paper trading mode**. To switch to live trading:

1. Set `ALPACA_PAPER=false` (or `BINANCE_TESTNET=false`)
2. Restart the backend
3. In the frontend Settings page, toggle "Live Trading Mode"
4. Confirm the risk disclaimer dialog
5. The header will display a persistent red "LIVE" badge

**Paper trading simulates:**
- Real market prices
- Order fills with realistic slippage
- Virtual balance tracking
- Full journal logging

This lets you validate strategies with zero financial risk.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid API key" | Check keys in `.env`, restart backend |
| "Rate limit exceeded" | CCXT handles this automatically; wait a few seconds |
| "Market data delayed" | Free data feeds may have 15-min delay for some symbols. Upgrade to paid data if needed. |
| "Orders not filling in paper mode" | Paper trading fills are simulated instantly at market price. Check strategy signal logic. |
