"""Alpaca exchange connector."""
from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Any

from app.exchange.base import ExchangeConnector, AccountInfo, OrderResult, PositionInfo


class AlpacaConnector(ExchangeConnector):
    """Live or paper trading via Alpaca Markets REST API."""

    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        super().__init__(name="alpaca", paper=paper)
        self._api_key = api_key
        self._api_secret = api_secret
        self._base = (
            "https://paper-api.alpaca.markets/v2"
            if paper
            else "https://api.alpaca.markets/v2"
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        import httpx
        url = f"{self._base}{path}"
        try:
            if method == "GET":
                r = httpx.get(url, headers=self._headers(), timeout=15)
            elif method == "POST":
                r = httpx.post(url, headers=self._headers(), json=json, timeout=15)
            elif method == "DELETE":
                r = httpx.delete(url, headers=self._headers(), timeout=15)
            else:
                return {"error": f"Unsupported method {method}"}
            if r.status_code >= 400:
                return {"error": r.text, "status_code": r.status_code}
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_account(self) -> AccountInfo:
        data = self._request("GET", "/account")
        if "error" in data:
            return AccountInfo(balance=0.0, buying_power=0.0, equity=0.0, extra=data)
        return AccountInfo(
            balance=float(data.get("cash", 0.0)),
            buying_power=float(data.get("buying_power", 0.0)),
            equity=float(data.get("equity", 0.0)),
            currency=data.get("currency", "USD"),
            extra=data,
        )

    def place_order(
        self,
        asset_id: int,
        symbol: str,
        action: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> OrderResult:
        side = "buy" if action == "buy" else "sell"
        body = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "qty": str(size),
            "time_in_force": "day",
        }
        if order_type in ("limit", "stop_limit") and price is not None:
            body["limit_price"] = str(price)
        if order_type in ("stop", "stop_limit") and price is not None:
            body["stop_price"] = str(price)

        data = self._request("POST", "/orders", json=body)
        if "error" in data:
            return OrderResult(
                order_id="",
                status="rejected",
                symbol=symbol,
                side=side,
                size=size,
                extra=data,
            )

        return OrderResult(
            order_id=data.get("id", ""),
            status=data.get("status", "pending"),
            symbol=symbol,
            side=side,
            size=size,
            filled_size=float(data.get("filled_qty", 0.0)),
            fill_price=float(data.get("filled_avg_price", 0.0)) if data.get("filled_avg_price") else None,
            commission=0.0,
            created_at=dt.datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00")) if data.get("submitted_at") else None,
            extra=data,
        )

    def get_order_status(self, order_id: str) -> OrderResult:
        data = self._request("GET", f"/orders/{order_id}")
        if "error" in data:
            return OrderResult(
                order_id=order_id,
                status="not_found",
                symbol="",
                side="",
                size=0.0,
                extra=data,
            )
        return OrderResult(
            order_id=data.get("id", order_id),
            status=data.get("status", "unknown"),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            size=float(data.get("qty", 0.0)),
            filled_size=float(data.get("filled_qty", 0.0)),
            fill_price=float(data.get("filled_avg_price", 0.0)) if data.get("filled_avg_price") else None,
            commission=0.0,
            extra=data,
        )

    def cancel_order(self, order_id: str) -> bool:
        data = self._request("DELETE", f"/orders/{order_id}")
        return "error" not in data

    def get_positions(self) -> List[PositionInfo]:
        data = self._request("GET", "/positions")
        if "error" in data:
            return []
        if isinstance(data, dict):
            # Single position returned as dict (edge case)
            data = [data]
        positions = []
        for p in data:
            qty = float(p.get("qty", 0.0))
            side = float(p.get("side", qty))
            positions.append(
                PositionInfo(
                    asset_id=0,  # Alpaca doesn't expose our internal asset_id
                    symbol=p.get("symbol", ""),
                    direction="long" if qty >= 0 else "short",
                    size=abs(qty),
                    avg_entry_price=float(p.get("avg_entry_price", 0.0)),
                    market_price=float(p.get("current_price", 0.0)) if p.get("current_price") else None,
                    unrealized_pnl=float(p.get("unrealized_pl", 0.0)),
                    extra=p,
                )
            )
        return positions

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        data = self._request("GET", f"/assets/{symbol}/quotes/latest")
        if "error" in data:
            return data
        quote = data.get("quote", {})
        return {
            "bid": float(quote.get("bp", 0.0)),
            "ask": float(quote.get("ap", 0.0)),
            "last": float(quote.get("p", 0.0)),
            "size": float(quote.get("s", 0.0)),
        }

    def health_check(self) -> Dict[str, Any]:
        data = self._request("GET", "/account")
        ok = "error" not in data and "status" in data
        return {
            "ok": ok,
            "name": self.name,
            "paper": self.paper,
            "account_status": data.get("status") if ok else None,
            "error": data.get("error") if not ok else None,
        }
