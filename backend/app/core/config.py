from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator

ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = ROOT / "database"
DATABASE_DIR.mkdir(exist_ok=True)

_DEFAULT_DB = f"sqlite:///{(DATABASE_DIR / 'echotrader.db').resolve().as_posix()}"


class Settings(BaseSettings):
    # App
    app_name: str = "EchoTrader"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = _DEFAULT_DB

    # Alpaca (Stocks/ETFs)
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True

    # Binance (Crypto)
    binance_api_key: str = ""
    binance_secret_key: str = ""
    binance_testnet: bool = True

    # Risk
    max_daily_loss_pct: float = 2.0
    max_position_size_pct: float = 10.0
    max_drawdown_halt_pct: float = 15.0

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_path(cls, v: str) -> str:
        """Ensure SQLite path is absolute and uses forward slashes.
        Fixes Windows relative-path issues when .env overrides the default."""
        if v and v.startswith("sqlite:///"):
            path_part = v.replace("sqlite:///", "")
            p = Path(path_part)
            if not p.is_absolute():
                # Resolve relative paths against project root
                p = (ROOT / path_part).resolve()
            return f"sqlite:///{p.as_posix()}"
        return v

    class Config:
        env_file = str(ROOT / "backend" / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
