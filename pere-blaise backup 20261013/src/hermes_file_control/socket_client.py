"""Narrow client for the local broker's Unix socket protocol."""
from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any


def request(socket_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Send one framed request; the caller never supplies executable text."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3700)
        client.connect(str(socket_path))
        client.sendall(encoded)
        response = bytearray()
        while not response.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk:
                raise ValueError("broker closed its response early")
            response.extend(chunk)
            if len(response) > 1024 * 1024:
                raise ValueError("broker response is too large")
    parsed = json.loads(response)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("ok"), bool):
        raise ValueError("invalid broker response")
    if not parsed["ok"]:
        raise ValueError(str(parsed.get("error", "broker rejected request")))
    result = parsed.get("result")
    if not isinstance(result, dict):
        raise ValueError("invalid broker result")
    return result
