import logging
from fastapi import APIRouter, HTTPException
from app.provider_config import config_manager, PROVIDERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers")
def get_providers():
    return {"providers": config_manager.get_all_providers()}


@router.get("/provider")
def get_current_provider():
    return config_manager.get_provider_config()


@router.post("/provider")
def set_provider(data: dict):
    provider = data.get("provider", "")
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    config_manager.set_provider(provider)
    return config_manager.get_provider_config()


@router.post("/api-key")
def set_api_key(data: dict):
    provider = data.get("provider", "")
    api_key = data.get("api_key", "")
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    config_manager.set_api_key(provider, api_key)
    return {"success": True}


@router.post("/model")
def set_model(data: dict):
    provider = data.get("provider", "")
    model = data.get("model", "")
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    config_manager.set_model(provider, model)
    return {"success": True}


@router.get("/models/{provider}")
def get_models(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    p = PROVIDERS[provider]
    api_key = config_manager.get_provider_config()["api_key"]

    if p["has_models_api"] and api_key:
        import asyncio
        from app.clients.ai import fetch_models
        models = asyncio.run(fetch_models(provider, api_key))
        return {"models": models}

    return {"models": p["models"]}
