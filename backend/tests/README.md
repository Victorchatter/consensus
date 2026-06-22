# EchoTrader Tests

Run the test suite with:

```bash
cd backend
python -m pytest tests/ -v
```

## Structure

- `tests/unit/` — isolated logic tests (indicators, strategies, utils)
- `tests/integration/` — API endpoint tests using TestClient
- `tests/security/` — crypto, auth, input-sanitization checks

## Coverage Targets

- Business logic: >= 80%
- API routes: >= 60%
- Security-critical paths: 100%
