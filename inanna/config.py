from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    model_url: str
    model_name: str
    api_key: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            model_url=os.getenv("INANNA_MODEL_URL", "http://localhost:1234/v1").strip(),
            model_name=os.getenv("INANNA_MODEL_NAME", "qwen2.5-7b-instruct-1m").strip(),
            api_key=os.getenv("INANNA_API_KEY", "").strip(),
        )
