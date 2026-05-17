# SemantiTag

FastAPI service for generating semantic metadata (tags + vector text), storing it in ChromaDB, and searching per tenant.

## Quick Start

1. Install dependencies:

```bash
uv sync
```

2. Run API server:

```bash
uv run uvicorn app.main:app --reload
```

3. Open API docs:

- Swagger UI: http://127.0.0.1:8000/docs

## Environment Variables

- OPENROUTER_API_KEY or OPENAI_API_KEY: Required for LLM generation.
- CHROMA_DB_PATH: Local Chroma persistence path. Default: ./chroma_db
- CHROMA_COLLECTION_NAME: Collection name. Default: semantitag_items
- SEMANTITAG_VECTORIZE_TAGS: Whether to also store a separate tags vector document. Default: true

## API Endpoints

- GET /health
  - Health check.

- POST /generate
  - Header: tenantId (required)
  - Body:

```json
{
  "itemId": "1",
  "type": "song",
  "metadata": {
    "artist": "eminem",
    "genre": "rap",
    "title": "lose yourself"
  }
}
```

  - Behavior:
  - Generates structured tags and a semantic description suitable for vector search.
  - Stores vectors/documents in ChromaDB partitioned by tenantId.
  - Returns stored ids and vector metadata.

- POST /search
  - Header: tenantId (required)
  - Body:

```json
{
  "query": "hit songs by eminem",
  "nResults": 10,
  "itemType": "song",
  "includeTagVectors": false
}
```

  - Notes:
  - Search is tenant-partitioned using tenantId.
  - By default, results are limited to description vectors.
  - Set includeTagVectors=true to include tag-vector entries.

## Example cURL

Generate and index:

```bash
curl -X POST http://localhost:8000/generate \
  -H "tenantId: 1234" \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "1",
    "type": "song",
    "metadata": {
      "artist": "eminem",
      "genre": "rap",
      "title": "lose yourself"
    }
  }'
```

Semantic search:

```bash
curl -X POST http://localhost:8000/search \
  -H "tenantId: 1234" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "songs by eminem"
  }'
```

## Storage Model

- Description vector id format:
  - tenantId:itemType:itemId:description
- Tag vector id format (when enabled):
  - tenantId:itemType:itemId:tags
- Stored metadata includes:
  - tenantId, itemId, itemType, tagsCsv, tagsCount, vectorKind
