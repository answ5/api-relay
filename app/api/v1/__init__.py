"""OpenAI-compatible API v1 router."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    # TODO: implement
    return {"object": "list", "data": []}


@router.post("/chat/completions")
async def chat_completions():
    """Chat completions endpoint (OpenAI-compatible)."""
    # TODO: implement
    return {"error": {"message": "Not implemented", "type": "api_error", "code": "not_implemented"}}


@router.post("/embeddings")
async def embeddings():
    """Embeddings endpoint (OpenAI-compatible)."""
    # TODO: implement
    return {"error": {"message": "Not implemented", "type": "api_error", "code": "not_implemented"}}


@router.post("/images/generations")
async def image_generations():
    """Image generation endpoint (OpenAI-compatible)."""
    # TODO: implement
    return {"error": {"message": "Not implemented", "type": "api_error", "code": "not_implemented"}}
