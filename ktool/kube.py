from __future__ import annotations

import json
import subprocess
from typing import Any


class KubectlError(RuntimeError):
    pass


def run_kubectl(args: list[str]) -> str:
    p = subprocess.run(
        ["kubectl", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if p.returncode != 0:
        raise KubectlError(p.stderr.strip())

    return p.stdout


def get_pods_json(namespace: str) -> dict[str, Any]:
    out = run_kubectl(
        ["get", "pods", "-n", namespace, "-o", "json"]
    )
    return json.loads(out)
