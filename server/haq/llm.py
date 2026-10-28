"""The Meta Model API client: the OpenAI Python SDK pointed at api.meta.ai."""

from __future__ import annotations

import os

from openai import OpenAI

from . import config


class MissingKeyError(RuntimeError):
    pass


def make_client() -> OpenAI:
    key = os.environ.get("MODEL_API_KEY", "")
    if not key:
        raise MissingKeyError("MODEL_API_KEY is not set: add it to server/.env")
    return OpenAI(api_key=key, base_url=config.base_url(), max_retries=4, timeout=180)


def plain(value):
    """SDK objects as plain JSON-ready data, so messages can be saved and resent."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value
