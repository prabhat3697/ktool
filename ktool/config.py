from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

CONFIG_PATH = Path.home() / ".ktool" / "config.yaml"

@dataclass
class KToolConfig:
    default_namespace: str
    contexts: dict[str, str]
    services: dict[str, str]

def load_config() -> KToolConfig:
    if not CONFIG_PATH.exists():
        # sensible defaults if user hasn't created config yet
        return KToolConfig(
            default_namespace="default",
            contexts={},
            services={},
        )

    data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    return KToolConfig(
        default_namespace=data.get("default_namespace", "default"),
        contexts=data.get("contexts", {}) or {},
        services=data.get("services", {}) or {},
    )
