# Runs first on any `import app`, so every network entry point (ingest CLI, paper
# bot, feeders) gets working TLS behind an intercepting AV/proxy. See the module.
from app.core import ssl_bootstrap  # noqa: F401
