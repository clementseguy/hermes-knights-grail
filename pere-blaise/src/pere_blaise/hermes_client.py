"""Narrow client for the operator-owned, internal Hermes API endpoint."""
from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


def planner_request(endpoint: str, api_key: str, model: str, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
    body = {"model": model, "stream": False, "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False, sort_keys=True)},
    ]}
    request = Request(endpoint.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
                      headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=120) as response:  # nosec: operator-provided loopback URL only
        payload = json.load(response)
    try:
        proposal = json.loads(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("planner did not return one JSON proposal") from exc
    if not isinstance(proposal, dict):
        raise ValueError("planner proposal must be a JSON object")
    return proposal
