from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import chromadb

_client: chromadb.PersistentClient | None = None
_collection = None
_db_path: str | None = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_writable_directory(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".semantitag_write_test")
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(test_file)
        return True
    except OSError:
        return False


def _resolve_chroma_db_path() -> str:
    configured = os.getenv("CHROMA_DB_PATH")
    if configured:
        if _is_writable_directory(configured):
            return configured
        raise PermissionError(
            f"Configured CHROMA_DB_PATH is not writable: {configured}"
        )

    project_default = str(Path(__file__).resolve().parents[2] / "chroma_db")
    temp_default = os.path.join(tempfile.gettempdir(), "semantitag_chroma_db")

    for candidate in [project_default, temp_default]:
        if _is_writable_directory(candidate):
            return candidate

    raise PermissionError(
        "No writable ChromaDB path available. Set CHROMA_DB_PATH to a writable directory."
    )


def _get_collection():
    global _client, _collection, _db_path

    if _collection is None:
        _db_path = _resolve_chroma_db_path()
        collection_name = os.getenv(
            "CHROMA_COLLECTION_NAME", "semantitag_items")

        _client = chromadb.PersistentClient(path=_db_path)
        _collection = _client.get_or_create_collection(name=collection_name)

    return _collection


def store_item_vectors(
    *,
    tenant_id: str,
    item_id: str,
    item_type: str,
    vector_text: str,
    tags: list[str],
) -> dict[str, Any]:
    collection = _get_collection()
    include_tag_vectors = _env_bool("SEMANTITAG_VECTORIZE_TAGS", default=True)

    base_metadata = {
        "tenantId": tenant_id,
        "itemId": item_id,
        "itemType": item_type,
        "tagsCsv": ", ".join(tags),
        "tagsCount": len(tags),
    }

    stored_ids: list[str] = []

    description_id = f"{tenant_id}:{item_type}:{item_id}:description"
    collection.upsert(
        ids=[description_id],
        documents=[vector_text],
        metadatas=[{**base_metadata, "vectorKind": "description"}],
    )
    stored_ids.append(description_id)

    if include_tag_vectors and tags:
        tags_id = f"{tenant_id}:{item_type}:{item_id}:tags"
        tags_document = (
            f"Tags for {item_type} item {item_id}: {', '.join(tags)}"
        )
        collection.upsert(
            ids=[tags_id],
            documents=[tags_document],
            metadatas=[{**base_metadata, "vectorKind": "tags"}],
        )
        stored_ids.append(tags_id)

    return {
        "collection": os.getenv("CHROMA_COLLECTION_NAME", "semantitag_items"),
        "db_path": _db_path,
        "stored_ids": stored_ids,
        "tag_vectors_enabled": include_tag_vectors,
    }


def search_items_by_semantic_query(
    *,
    tenant_id: str,
    query_text: str,
    n_results: int = 10,
    item_type: str | None = None,
    include_tag_vectors: bool = False,
) -> dict[str, Any]:
    collection = _get_collection()

    conditions: list[dict[str, Any]] = [
        {"tenantId": {"$eq": tenant_id}},
    ]
    if item_type:
        conditions.append({"itemType": {"$eq": item_type}})
    if not include_tag_vectors:
        conditions.append({"vectorKind": {"$eq": "description"}})

    where_filter: dict[str, Any] = {"$and": conditions}

    raw = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    ids = raw.get("ids", [[]])[0]
    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    items: list[dict[str, Any]] = []
    for index, result_id in enumerate(ids):
        items.append(
            {
                "id": result_id,
                "distance": distances[index] if index < len(distances) else None,
                "document": documents[index] if index < len(documents) else None,
                "metadata": metadatas[index] if index < len(metadatas) else None,
            }
        )

    return {
        "collection": os.getenv("CHROMA_COLLECTION_NAME", "semantitag_items"),
        "db_path": _db_path,
        "query": query_text,
        "count": len(items),
        "items": items,
    }
