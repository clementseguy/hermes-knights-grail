"""A local-only broker.  It deliberately exposes structured plan operations, never a command runner."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from .store import PlanStore


class Broker:
    def __init__(self, store: PlanStore, executor: Path, runtime_dir: Path, *, plan_ttl_hours: int = 12) -> None:
        if not 1 <= plan_ttl_hours <= 12:
            raise ValueError("plan_ttl_hours must be between 1 and 12")
        self.store, self.executor, self.runtime_dir, self.plan_ttl_hours = store, executor, runtime_dir, plan_ttl_hours
        self.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def create_plan(self, owner: str, manifest: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
        return self.store.create(owner=owner, manifest=manifest, details=details, ttl_hours=self.plan_ttl_hours)

    def detail(self, owner: str, plan_id: str) -> dict[str, Any]:
        plan = self.store.get(plan_id)
        if plan is None:
            raise ValueError("unknown plan")
        if plan["owner"] != owner:
            raise PermissionError("plan owner mismatch")
        return plan

    def learning_status(self, owner: str) -> dict[str, Any]:
        if not owner:
            raise PermissionError("owner is required")
        return self.store.learning_status()

    def apply(self, owner: str, plan_id: str) -> dict[str, Any]:
        plan = self.store.claim(plan_id, owner)
        fd, manifest_name = tempfile.mkstemp(prefix=f"{plan_id}-", suffix=".json", dir=self.runtime_dir)
        manifest_path = Path(manifest_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(json.dumps(plan["manifest"], ensure_ascii=False, sort_keys=True).encode("utf-8"))
            completed = subprocess.run(
                [sys.executable, str(self.executor), "--manifest", str(manifest_path), "--apply", "--non-interactive"],
                check=False, capture_output=True, text=True, timeout=3600,
            )
            try:
                result = json.loads(completed.stdout)
            except json.JSONDecodeError:
                result = {"actions": [], "executor_error": "invalid executor output", "returncode": completed.returncode}
            result["returncode"] = completed.returncode
            self.store.finish(plan_id, result)
            return result
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = {"actions": [], "executor_error": str(exc)}
            self.store.finish(plan_id, result)
            return result
        finally:
            manifest_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Hermes file-control broker; no network interface.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--executor", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("detail", "apply"):
        command = sub.add_parser(name)
        command.add_argument("--owner", required=True)
        command.add_argument("--plan-id", required=True)
    command = sub.add_parser("create")
    command.add_argument("--owner", required=True)
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--details", type=Path, required=True)
    command = sub.add_parser("purge-plan-records")
    command.add_argument("--retention-days", type=int, default=30)
    args = parser.parse_args()
    broker = Broker(PlanStore(args.database), args.executor, args.runtime_dir)
    if args.operation == "create":
        response = broker.create_plan(args.owner, json.loads(args.manifest.read_text()), json.loads(args.details.read_text()))
    elif args.operation == "detail":
        response = broker.detail(args.owner, args.plan_id)
    elif args.operation == "apply":
        response = broker.apply(args.owner, args.plan_id)
    else:
        response = {"purged_plan_records": broker.store.purge_plan_records(args.retention_days)}
    print(json.dumps(response, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
