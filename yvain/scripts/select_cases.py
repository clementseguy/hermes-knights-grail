#!/usr/bin/env python3
"""Select Yvain verification cases from a NexTarget CHANGELOG diff."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

STORY = re.compile(r"\bNT-\d+\b")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enforce", action="store_true")
    parser.add_argument(
        "--story",
        action="append",
        default=[],
        help="Limit the run to a delivered NT-XXX story present in the diff.",
    )
    args = parser.parse_args()
    diff = subprocess.run(
        ["git", "-C", str(args.app_dir), "diff", "--unified=0",
         f"{args.base}...{args.head}", "--", "CHANGELOG.md"],
        check=True, capture_output=True, text=True,
    ).stdout
    stories = sorted({
        item for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
        for item in STORY.findall(line)
    })
    if args.story:
        requested = set(args.story)
        unavailable = sorted(requested - set(stories))
        if unavailable:
            parser.error("US demandée absente du diff : " + ", ".join(unavailable))
        stories = [story for story in stories if story in requested]
    entries = json.loads(args.manifest.read_text(encoding="utf-8")).get("stories", {})
    missing, excluded, cases = [], [], []
    for story in stories:
        entry = entries.get(story)
        if entry and entry.get("scope") == "server":
            excluded.append(story)
        elif entry and entry.get("status") == "ready" and entry.get("cases"):
            if any(case.get("kind") == "maestro" for case in entry["cases"]):
                cases.extend(entry["cases"])
            else:
                missing.append(story)
        else:
            missing.append(story)
    result = {"stories": stories, "excluded_server_stories": excluded,
              "cases": cases, "missing_coverage": missing}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if missing:
        print("Yvain: couverture manquante: " + ", ".join(missing), file=sys.stderr)
    return 1 if args.enforce and (missing or not stories) else 0


if __name__ == "__main__":
    raise SystemExit(main())
