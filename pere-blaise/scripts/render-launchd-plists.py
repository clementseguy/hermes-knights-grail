#!/usr/bin/env python3
"""Render the user LaunchAgents without installing or loading them."""
from __future__ import annotations

import argparse
import json
import plistlib
from pathlib import Path


def _service(label: str, args: list[str], project: Path, log_name: str, **extra: object) -> dict:
    return {
        "Label": label,
        "ProgramArguments": args,
        "EnvironmentVariables": {"PYTHONPATH": str(project / "src")},
        "ProcessType": "Background",
        "StandardOutPath": str(Path.home() / "Library/Logs" / f"{log_name}.log"),
        "StandardErrorPath": str(Path.home() / "Library/Logs" / f"{log_name}.err.log"),
        **extra,
    }


def _launch_python(project: Path) -> Path:
    """Use the project venv so launchd sees declared runtime dependencies.

    Calling ``Path.resolve`` here would replace the venv interpreter with its
    framework base Python, silently dropping ``websocket-client`` from Slack.
    macOS TCC must therefore be granted to this venv's Python.app when present.
    """
    venv_python = project / ".venv/bin/python"
    return venv_python


def render(project: Path, control: Path, *, include_weekly: bool = False) -> dict[str, dict]:
    config = json.loads((control / "broker.json").read_text(encoding="utf-8"))
    owners = list(map(str, config["telegram_allowed_user_ids"]))
    if len(owners) != 1:
        raise ValueError("broker.json must contain exactly one authorized Telegram user")
    python = str(_launch_python(project))
    broker = _service("com.local.pere-blaise", [python, "-m", "pere_blaise.service",
                      "--config", str(control / "broker.json")], project, "pere-blaise",
                      RunAtLoad=True, KeepAlive=True)
    telegram = _service("com.local.pere-blaise-telegram", [python, "-m", "pere_blaise.telegram_gateway",
                       "--broker-config", str(control / "broker.json"), "--telegram-env", str(control / "telegram.env"),
                       "--planner-env", str(control / "planner.env"), "--state", str(control / "telegram-offset")],
                        project, "pere-blaise-telegram", RunAtLoad=True, KeepAlive=True)
    weekly = _service("com.local.pere-blaise-weekly-analysis", [python, "-m", "pere_blaise.weekly_analysis",
                     "--broker-config", str(control / "broker.json"), "--telegram-env", str(control / "telegram.env"),
                     "--planner-env", str(control / "planner.env")], project, "pere-blaise-weekly-analysis",
                     StartCalendarInterval={"Weekday": 0, "Hour": 18, "Minute": 0})
    rendered = {broker["Label"]: broker, telegram["Label"]: telegram}
    if include_weekly:
        rendered[weekly["Label"]] = weekly
    # Do not install a repeatedly failing process before its dedicated credentials
    # and explicit allowlists exist.
    if (control / "slack.env").is_file():
        slack = _service("com.local.pere-blaise-slack", [python, "-m", "pere_blaise.slack_gateway",
                         "--broker-config", str(control / "broker.json"), "--slack-env", str(control / "slack.env"),
                         "--planner-env", str(control / "planner.env")], project, "pere-blaise-slack",
                         RunAtLoad=True, KeepAlive=True)
        rendered[slack["Label"]] = slack
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-weekly", action="store_true",
                        help="render the disabled-by-default weekly analysis LaunchAgent")
    args = parser.parse_args()
    args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    for label, payload in render(args.project.resolve(), args.control_dir.resolve(),
                                 include_weekly=args.include_weekly).items():
        target = args.output_dir / f"{label}.plist"
        with target.open("wb") as handle:
            plistlib.dump(payload, handle, sort_keys=True)
        target.chmod(0o600)
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
