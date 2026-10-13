"""Private-inventory to untrusted-planner boundary."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from .contracts import safe_relative

CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _display(value: str) -> str:
    """Keep hostile filenames as data and prevent prompt/layout control characters."""
    value = CONTROL.sub("�", value)
    return "".join("�" if unicodedata.category(char).startswith("C") else char for char in value)[:240]


def _hierarchy_summary(documents: dict[str, Any], *, max_directories: int) -> list[dict[str, Any]]:
    direct_counts: dict[str, int] = {}
    for item in documents["files"]:
        parent = str(Path(item["path"]).parent)
        direct_counts[parent] = direct_counts.get(parent, 0) + 1
    directories = documents.get("directories") or sorted({str(Path(item["path"]).parent) for item in documents["files"]
                                                          if Path(item["path"]).parent != Path(".")})
    summary = []
    for directory in directories[:max_directories]:
        descendants = sum(1 for other in directories if other == directory or other.startswith(directory + "/"))
        summary.append({"path": _display(directory), "direct_file_count": direct_counts.get(directory, 0),
                        "subdirectory_count": descendants - 1})
    return summary


def planner_context(inventory: dict[str, Any], *, learning_hints: list[dict[str, Any]] | None = None,
                    max_directories: int = 500) -> dict[str, Any]:
    """No SHA values, document filenames or full document inventory crosses this boundary."""
    downloads = [{"source": _display(item["path"]), "size": item["size"], "extension": item["extension"]}
                 for item in inventory["downloads"]["files"]]
    document_root = Path(inventory["documents"]["root"])
    directories = inventory["documents"].get("directories") or sorted({str(Path(item["path"]).parent)
        for item in inventory["documents"]["files"] if Path(item["path"]).parent != Path(".")})
    return {"untrusted_downloads": downloads,
            "document_directories": [_display(directory) for directory in directories[:max_directories]],
            "document_file_count": len(inventory["documents"]["files"]),
            "directory_list_truncated": len(directories) > max_directories,
            "document_hierarchy": _hierarchy_summary(inventory["documents"], max_directories=max_directories),
            "learning_hints": learning_hints or []}


def organisation_review_from_proposal(proposal: Any) -> list[dict[str, Any]]:
    """Accept only short, display-safe, non-operative organisation suggestions."""
    if not isinstance(proposal, dict) or not isinstance(proposal.get("organization_review", []), list):
        return []
    review = []
    for item in proposal.get("organization_review", [])[:3]:
        if not isinstance(item, dict):
            continue
        title, recommendation = item.get("title"), item.get("recommendation")
        if not isinstance(title, str) or not isinstance(recommendation, str):
            continue
        title, recommendation = _display(title).strip(), _display(recommendation).strip()
        if title and recommendation:
            review.append({"title": title, "recommendation": recommendation})
    return review


def manifest_from_proposal(proposal: Any, inventory: dict[str, Any]) -> dict[str, Any]:
    """Join model-selected source/destination pairs to private scanner fingerprints."""
    if not isinstance(proposal, dict):
        raise ValueError("proposal is not an object")
    if "actions" not in proposal:
        raise ValueError("proposal is missing actions")
    if not isinstance(proposal["actions"], list):
        raise ValueError("proposal actions is not a list")
    # The LLM sometimes adds explanatory fields despite the prompt.  They are
    # deliberately discarded here: only source/destination can reach the
    # reconstructed strict v2 manifest, and both are still independently
    # validated against the host-private inventory below.
    available = {item["path"]: item["expected"] for item in inventory["downloads"]["files"]}
    actions, destinations = [], set()
    for index, raw in enumerate(proposal["actions"], 1):
        if not isinstance(raw, dict) or not {"source", "destination"}.issubset(raw):
            raise ValueError(f"proposal action {index} must contain source and destination")
        source = str(safe_relative(raw["source"], "source"))
        destination = str(safe_relative(raw["destination"], "destination"))
        if source not in available or destination in destinations:
            raise ValueError("proposal contains unknown source or duplicate destination")
        destinations.add(destination)
        actions.append({"source": source, "destination": destination, "expected": available[source]})
    if not actions:
        raise ValueError("proposal actions is empty")
    return {"version": 2, "actions": actions}
