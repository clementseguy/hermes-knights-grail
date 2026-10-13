"""Host CLI for safe analysis.  It intentionally has no command that applies a plan."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .broker import Broker
from .hermes_client import planner_request
from .store import PlanStore
from .workflow import analyse


def _env_value(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1]
    raise ValueError("missing " + key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-config", type=Path, required=True)
    parser.add_argument("--planner-env", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("analyse", nargs="?")
    args = parser.parse_args()
    if args.analyse != "analyse":
        parser.error("the only supported action is analyse")
    config = json.loads(args.broker_config.read_text(encoding="utf-8"))
    project = Path(__file__).resolve().parents[2]
    prompt = (project / "prompts" / "organizer-planner.md").read_text(encoding="utf-8")
    api_key = _env_value(args.planner_env, "PERE_BLAISE_API_KEY")
    broker = Broker(PlanStore(Path(config["database"]), sha256_max_bytes=int(config["sha256_max_bytes"])),
                    Path(config["executor"]), Path(config["runtime_dir"]))
    plan = analyse(args.owner, Path.home(), broker,
                   lambda context: planner_request("http://127.0.0.1:8643", api_key, "hermes-agent", prompt, context),
                   int(config["sha256_max_bytes"]))
    details = plan["details"]
    print(json.dumps({"plan_id": plan["id"], "expires_at": plan["expires_at"],
                      "confidence": details["confidence"], "actions": details["actions"],
                      "ambiguities": details["ambiguities"], "excluded": details["excluded"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
