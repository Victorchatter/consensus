"""Quick diagnostic -- run this to verify backend starts."""
import sys
sys.path.insert(0, '.')

from app.core.config import settings
print(f"Database path: {settings.database_url}")

from app.core.database import engine, Base
Base.metadata.create_all(bind=engine)
print("Tables created OK.")

from app.data.seed import run_seed
run_seed()
print("Seed complete.")

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app import models

db = SessionLocal()
assets = db.query(models.Asset).all()
print(f"Assets in DB: {len(assets)}")
for a in assets[:5]:
    print(f"  {a.symbol} ({a.asset_class.value})")

db.close()
