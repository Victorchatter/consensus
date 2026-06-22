# Frontend Tests

Run the test suite with:

```bash
cd frontend
npm test -- --watchAll=false
```

## Structure

- `src/__tests__/components/` — UI component rendering
- `src/__tests__/pages/` — Page-level integration
- `src/__tests__/utils/` — Helper functions

## Notes

- Uses Vitest (bundled with Vite) and React Testing Library
- Mock API calls via `msw` or manual `fetch` mocks
