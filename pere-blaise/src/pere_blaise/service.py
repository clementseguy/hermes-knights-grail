"""Local Unix-socket service for the future deterministic Telegram router.

It has no TCP listener, shell endpoint, file-path endpoint, or model endpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import socketserver
from pathlib import Path
from typing import Any

from .broker import Broker
from .store import PlanStore

MAX_REQUEST_BYTES = 1024 * 1024


class LocalService:
    def __init__(self, broker: Broker, allowed_owners: set[str], retention_days: int = 30) -> None:
        if retention_days < 1:
            raise ValueError("retention_days must be positive")
        self.broker, self.allowed_owners, self.retention_days = broker, allowed_owners, retention_days

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        self.broker.store.purge_plan_records(self.retention_days)
        operation, owner = request.get("operation"), request.get("owner")
        if not isinstance(owner, str) or owner not in self.allowed_owners:
            raise PermissionError("owner is not authorized")
        if operation == "create":
            manifest, details = request.get("manifest"), request.get("details")
            if not isinstance(manifest, dict) or not isinstance(details, dict):
                raise ValueError("create requires object manifest and details")
            return self.broker.create_plan(owner, manifest, details)
        if operation == "detail":
            return self.broker.detail(owner, _plan_id(request))
        if operation == "learning":
            return self.broker.learning_status(owner)
        if operation == "apply":
            return self.broker.apply(owner, _plan_id(request))
        raise ValueError("unknown operation")


def _plan_id(request: dict[str, Any]) -> str:
    value = request.get("plan_id")
    if not isinstance(value, str):
        raise ValueError("plan_id is required")
    return value


def make_handler(service: LocalService):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
            try:
                if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
                    raise ValueError("invalid request framing")
                request = json.loads(raw)
                if not isinstance(request, dict):
                    raise ValueError("request must be an object")
                response = {"ok": True, "result": service.dispatch(request)}
            except (ValueError, PermissionError, json.JSONDecodeError) as exc:
                response = {"ok": False, "error": str(exc)}
            self.wfile.write(json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    socket_path = Path(config["socket"])
    socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    store = PlanStore(Path(config["database"]), sha256_max_bytes=int(config["sha256_max_bytes"]))
    owner_ids = set(map(str, config["telegram_allowed_user_ids"]))
    owner_ids.update(map(str, config.get("slack_allowed_user_ids", [])))
    if not owner_ids:
        raise ValueError("at least one authorized owner is required")
    service = LocalService(Broker(store, Path(config["executor"]), Path(config["runtime_dir"]),
                                  plan_ttl_hours=int(config["plan_ttl_hours"])), owner_ids,
                           retention_days=int(config["retention_days"]))
    with socketserver.UnixStreamServer(str(socket_path), make_handler(service)) as server:
        os.chmod(socket_path, 0o600)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
