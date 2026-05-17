from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

import os


class TagResponse(BaseModel):
    tags: list[str] = Field(...,
                            description="A list of generated semantic tags for the item.")
    semantic_description: str = Field(
        ...,
        description=(
            "A rich, self-contained natural-language item description optimized for "
            "vector search and semantic retrieval."
        ),
    )


def create_tag_agent() -> ToolStrategy:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    model_name = "openai/gpt-oss-120b"

    if not api_key:
        raise ValueError(
            "Missing API key. Set OPENROUTER_API_KEY (or OPENAI_API_KEY) in your environment."
        )

    model = ChatOpenAI(
        model=model_name,
        temperature=0,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
    )

    agent = create_agent(
        model=model,
        system_prompt=(
            "You generate structured metadata for semantic search indexing. "
            "Given item metadata, produce: "
            "1) concise high-signal tags, and "
            "2) a semantic_description paragraph suitable for vector embeddings. "
            "The semantic_description should be self-contained and include entity names, "
            "category/type, style/genre, themes, era/context, and likely user intents "
            "(for example: hit songs by eminem, professional shoes for men, popular tourist destinations in paris, trending tech gadgets for teenagers) without fabricating unknown facts."
        ),
        response_format=ToolStrategy(TagResponse)
    )
    return agent
