from app.core.database import Base, engine, SessionLocal
from app import models


def test_consensus_signal_roundtrip():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        row = models.ConsensusSignal(
            asset_id=1, timestamp=__import__("datetime").datetime(2026, 1, 1),
            action="buy", price=42000.0, score=0.72,
            n_long=9, n_short=2, n_flat=3, votes={"voterA": 1, "voterB": -1},
        )
        db.add(row); db.commit(); db.refresh(row)
        assert row.id is not None
        assert row.votes["voterA"] == 1
    finally:
        db.close()
