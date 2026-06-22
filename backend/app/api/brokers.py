from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.crypto import KeyVault
from app import models

router = APIRouter(prefix="/brokers", tags=["brokers"])


class BrokerConnectionCreate(BaseModel):
    broker_name: str
    user_label: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    is_paper: bool = True
    master_password: Optional[str] = None  # if provided, encrypt; else store plain with warning
    extra_json: Optional[dict] = None


class BrokerConnectionRead(BaseModel):
    id: int
    broker_name: str
    user_label: Optional[str] = None
    is_paper: bool
    is_active: bool
    created_at: Optional[str] = None


@router.post("/connections")
def create_connection(payload: BrokerConnectionCreate, db: Session = Depends(get_db)):
    api_key_enc = None
    api_secret_enc = None
    passphrase_enc = None

    if payload.api_key or payload.api_secret:
        if payload.master_password:
            vault = KeyVault(payload.master_password)
            api_key_enc = vault.encrypt(payload.api_key or "") if payload.api_key else None
            api_secret_enc = vault.encrypt(payload.api_secret or "") if payload.api_secret else None
            passphrase_enc = vault.encrypt(payload.passphrase or "") if payload.passphrase else None
        else:
            # Store plain text with a flag indicating no encryption
            api_key_enc = payload.api_key
            api_secret_enc = payload.api_secret
            passphrase_enc = payload.passphrase

    conn = models.BrokerConnection(
        broker_name=payload.broker_name,
        user_label=payload.user_label,
        api_key_encrypted=api_key_enc,
        api_secret_encrypted=api_secret_enc,
        passphrase_encrypted=passphrase_enc,
        is_paper=payload.is_paper,
        is_active=True,
        extra_json=payload.extra_json or {},
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {
        "id": conn.id,
        "broker_name": conn.broker_name,
        "user_label": conn.user_label,
        "is_paper": conn.is_paper,
        "is_active": conn.is_active,
        "encrypted": bool(payload.master_password),
        "created_at": conn.created_at.isoformat() if conn.created_at else None,
    }


@router.get("/connections", response_model=List[BrokerConnectionRead])
def list_connections(
    broker_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.BrokerConnection)
    if broker_name:
        q = q.filter(models.BrokerConnection.broker_name == broker_name)
    return q.order_by(models.BrokerConnection.created_at.desc()).all()


@router.patch("/connections/{conn_id}")
def update_connection(
    conn_id: int,
    payload: BrokerConnectionCreate,
    db: Session = Depends(get_db),
):
    conn = db.query(models.BrokerConnection).get(conn_id)
    if not conn:
        return {"error": "Connection not found"}

    if payload.is_paper is not None:
        conn.is_paper = payload.is_paper
    if payload.is_active is not None:
        conn.is_active = payload.is_active
    if payload.user_label is not None:
        conn.user_label = payload.user_label
    if payload.extra_json is not None:
        conn.extra_json = payload.extra_json

    if (payload.api_key or payload.api_secret) and payload.master_password:
        vault = KeyVault(payload.master_password)
        if payload.api_key:
            conn.api_key_encrypted = vault.encrypt(payload.api_key)
        if payload.api_secret:
            conn.api_secret_encrypted = vault.encrypt(payload.api_secret)
        if payload.passphrase:
            conn.passphrase_encrypted = vault.encrypt(payload.passphrase)

    db.commit()
    db.refresh(conn)
    return {"updated": True}


@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: int, db: Session = Depends(get_db)):
    conn = db.query(models.BrokerConnection).get(conn_id)
    if not conn:
        return {"error": "Connection not found"}
    db.delete(conn)
    db.commit()
    return {"deleted": True}


@router.post("/connections/{conn_id}/test")
def test_connection(conn_id: int, master_password: Optional[str] = None, db: Session = Depends(get_db)):
    conn = db.query(models.BrokerConnection).get(conn_id)
    if not conn:
        return {"error": "Connection not found"}

    # Decrypt if needed
    api_key = conn.api_key_encrypted or ""
    api_secret = conn.api_secret_encrypted or ""

    # Very naive heuristic: if the stored value looks like Fernet ciphertext (starts with gAAAA)
    if api_key.startswith("gAAAA") and master_password:
        try:
            vault = KeyVault(master_password)
            api_key = vault.decrypt(api_key)
            api_secret = vault.decrypt(api_secret) if api_secret.startswith("gAAAA") else api_secret
        except Exception:
            return {"error": "Failed to decrypt — wrong master password?"}

    if conn.broker_name == "alpaca":
        import httpx
        url = "https://paper-api.alpaca.markets/v2/account" if conn.is_paper else "https://api.alpaca.markets/v2/account"
        try:
            r = httpx.get(url, headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            }, timeout=10)
            if r.status_code == 200:
                return {"success": True, "broker": "alpaca", "account": r.json().get("status")}
            return {"success": False, "status_code": r.status_code, "detail": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Test not implemented for this broker"}


@router.get("/wizard-recommend")
def broker_wizard_recommend(
    location: str = Query(...),
    asset_class: str = Query(...),
    capital: str = Query(...),
    fee_sensitive: bool = Query(False),
):
    """Simple recommendation engine based on questionnaire answers."""
    recs = []
    if asset_class in ("stock", "etf"):
        if location in ("us", "ca"):
            recs.append({
                "broker": "alpaca",
                "name": "Alpaca Markets",
                "why": "Commission-free US stock/ETF trading. Excellent API. Paper trading free.",
                "url": "https://alpaca.markets",
                "paper": True,
            })
        recs.append({
            "broker": "ibkr",
            "name": "Interactive Brokers",
            "why": "Low commissions, global market access, professional-grade API.",
            "url": "https://www.interactivebrokers.com",
            "paper": True,
        })
    if asset_class == "crypto":
        recs.append({
            "broker": "binance",
            "name": "Binance",
            "why": "Deep liquidity, low fees, extensive API. Testnet available for free practice.",
            "url": "https://www.binance.com",
            "paper": True,
        })
        recs.append({
            "broker": "coinbase",
            "name": "Coinbase Advanced",
            "why": "US-regulated, insured custody, solid API for algo trading.",
            "url": "https://www.coinbase.com/advanced-trade",
            "paper": False,
        })
    if asset_class == "forex":
        recs.append({
            "broker": "oanda",
            "name": "OANDA",
            "why": "Tight spreads on major pairs, free demo account, robust REST API.",
            "url": "https://www.oanda.com",
            "paper": True,
        })

    if fee_sensitive:
        recs.sort(key=lambda x: 0 if x["paper"] else 1)

    return {"recommendations": recs[:3], "asset_class": asset_class, "location": location}
