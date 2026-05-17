from typing import Any
import json

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from app.agents.tag_agent import TagResponse, create_tag_agent
from app.storage.chroma_store import search_items_by_semantic_query, store_item_vectors

load_dotenv()

app = FastAPI(title="SemantiTag Mock API", version="0.1.0")


class GeneratePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itemId: str
    type: str
    metadata: dict[str, Any]


class SemanticSearchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str = Field(..., min_length=1)
    n_results: int = Field(default=10, alias="nResults", ge=1, le=100)
    item_type: str | None = Field(default=None, alias="itemType")
    include_tag_vectors: bool = Field(default=False, alias="includeTagVectors")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
async def generate_semantic_tags(
    payload: GeneratePayload,
    tenant_id: str = Header(..., alias="tenantId"),
) -> dict[str, Any]:
    agent = create_tag_agent()

    template = (
        "Generate semantic indexing output for this item. "
        "Return tags and semantic_description. "
        "Metadata JSON: {metadata} Item ID: {itemId} Type: {type}"
    )

    response = await agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=template.format(
                        metadata=json.dumps(
                            payload.metadata, ensure_ascii=False),
                        itemId=payload.itemId,
                        type=payload.type
                    )
                )
            ]
        }
    )

    raw_structured = response.get("structured_response")
    if isinstance(raw_structured, TagResponse):
        structured = raw_structured
    else:
        structured = TagResponse.model_validate(raw_structured)

    try:
        vector_store_result = store_item_vectors(
            tenant_id=tenant_id,
            item_id=payload.itemId,
            item_type=payload.type,
            vector_text=structured.semantic_description,
            tags=structured.tags,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store vectors in ChromaDB: {exc}",
        ) from exc

    return {
        "message": "Mock response",
        "tenantId": tenant_id,
        "received": payload.model_dump(),
        "generated_tags": structured.tags,
        "vector_text": structured.semantic_description,
        "vector_store": vector_store_result,
    }


@app.post("/search")
def semantic_search(
    payload: SemanticSearchPayload,
    tenant_id: str = Header(..., alias="tenantId"),
) -> dict[str, Any]:
    try:
        search_result = search_items_by_semantic_query(
            tenant_id=tenant_id,
            query_text=payload.query,
            n_results=payload.n_results,
            item_type=payload.item_type,
            include_tag_vectors=payload.include_tag_vectors,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform semantic search in ChromaDB: {exc}",
        ) from exc

    return {
        "message": "Semantic search results",
        "tenantId": tenant_id,
        **search_result,
    }
