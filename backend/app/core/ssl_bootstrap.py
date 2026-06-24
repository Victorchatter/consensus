"""Make HTTPS work behind a TLS-intercepting AV/proxy (e.g. Avast Web Shield,
Kaspersky, Zscaler) without weakening verification.

Two TLS stacks are in play:
  - OpenSSL-based libs (ccxt, requests) — verified via the OS trust store using
    `truststore`, which the interceptor's CA is installed into (that's why the
    browser works). This handles intercepting chains OpenSSL would otherwise
    reject as having a non-CA intermediate.
  - curl_cffi-based libs (yfinance) — read `CURL_CA_BUNDLE`, so we point it at a
    PEM exported from the Windows root store (see scripts/build_ca_bundle.ps1).

Both must be configured before the first network call. Import this module early
(it runs on import, is idempotent, and no-ops cleanly on machines without the
interceptor or without truststore installed)."""
from __future__ import annotations

import os
from pathlib import Path

# backend/win-ca-bundle.pem — machine-specific, gitignored.
_BUNDLE = Path(__file__).resolve().parents[2] / "win-ca-bundle.pem"


def _bootstrap() -> None:
    if _BUNDLE.exists():
        for var in ("CURL_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            os.environ.setdefault(var, str(_BUNDLE))
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        # truststore is optional; the CA-bundle env vars above still help, and a
        # machine with clean egress needs neither.
        pass


_bootstrap()
