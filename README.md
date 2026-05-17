# SemantiTag (FastAPI + uv)

This folder is scaffolded as a `uv` Python project with a minimal FastAPI app.

## Quick start

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Run the API server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
3. Open docs:
   - Swagger UI: http://127.0.0.1:8000/docs

## Endpoints

- `GET /health`
  - Basic health check.
- `POST /mock`
  - Accepts any JSON object in the request body and echoes it back.

### Example request

```bash
curl -X POST http://127.0.0.1:8000/mock \
  -H "Content-Type: application/json" \
  -d '{"title":"test","tags":["demo"],"score":42}'
```

### Example response

```json
{
  "message": "Mock response",
  "received": {
    "title": "test",
    "tags": ["demo"],
    "score": 42
  }
}
```
# SematiTag
