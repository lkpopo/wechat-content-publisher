import json
import os
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "config.json"

DEFAULT_CONFIG = {
    "ai_provider": "opencode",
    "opencode_api_key": "",
    "opencode_model": "muse-spark-1.2-contributor",
    "opencode_base_url": "https://opencode.ai/zen/go/v1",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "deepseek_base_url": "https://api.deepseek.com/v1",
}

PROVIDERS = {
    "opencode": {
        "name": "OpenCode Go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "endpoint": "/responses",
        "models": [
            {"id": "muse-spark-1.2-contributor", "name": "Muse Spark 1.2"},
            {"id": "longcat-2.0", "name": "LongCat 2.0"},
            {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash"},
            {"id": "qwen3.8-flash", "name": "Qwen 3.8 Flash"},
        ],
        "has_models_api": True,
        "api_key_env": "opencode_api_key",
        "model_key": "opencode_model",
        "base_url_key": "opencode_base_url",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "endpoint": "/chat/completions",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner"},
        ],
        "has_models_api": True,
        "api_key_env": "deepseek_api_key",
        "model_key": "deepseek_model",
        "base_url_key": "deepseek_base_url",
    },
}


class ConfigManager:
    def __init__(self):
        self._config = {}
        self._load()

    def _load(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = DEFAULT_CONFIG.copy()
            # Try to load from .env
            from app.config import settings
            self._config["opencode_api_key"] = settings.opencode_api_key
            self._config["opencode_model"] = settings.opencode_model
            self._config["opencode_base_url"] = settings.opencode_base_url
            self._save()

    def _save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value):
        self._config[key] = value
        self._save()

    def get_provider(self) -> str:
        return self._config.get("ai_provider", "opencode")

    def get_models(self, provider: str) -> list:
        if provider in PROVIDERS:
            cached = self._config.get(f"{provider}_cached_models")
            if cached and isinstance(cached, list) and len(cached) > 0:
                return cached
            return PROVIDERS[provider]["models"]
        return []

    def set_cached_models(self, provider: str, models: list):
        if provider in PROVIDERS and models:
            self._config[f"{provider}_cached_models"] = models
            PROVIDERS[provider]["models"] = models
            self._save()

    def get_provider_config(self) -> dict:
        provider = self.get_provider()
        p = PROVIDERS.get(provider, PROVIDERS["opencode"])
        current_models = self.get_models(provider)
        fallback_model = current_models[0]["id"] if current_models else ""
        return {
            "provider": provider,
            "name": p["name"],
            "base_url": self._config.get(p["base_url_key"], p["base_url"]),
            "model": self._config.get(p["model_key"], fallback_model),
            "api_key": self._config.get(p["api_key_env"], ""),
            "models": current_models,
            "has_models_api": p["has_models_api"],
            "endpoint": p["endpoint"],
        }

    def set_provider(self, provider: str):
        if provider in PROVIDERS:
            self._config["ai_provider"] = provider
            self._save()

    def set_api_key(self, provider: str, api_key: str):
        if provider in PROVIDERS:
            key = PROVIDERS[provider]["api_key_env"]
            self._config[key] = api_key
            self._save()

    def set_model(self, provider: str, model: str):
        if provider in PROVIDERS:
            key = PROVIDERS[provider]["model_key"]
            self._config[key] = model
            self._save()

    def get_all_providers(self) -> list:
        result = []
        for pid, p in PROVIDERS.items():
            result.append({
                "id": pid,
                "name": p["name"],
                "has_models_api": p["has_models_api"],
                "models": self.get_models(pid),
                "api_configured": bool(self._config.get(p["api_key_env"], "")),
            })
        return result



config_manager = ConfigManager()
