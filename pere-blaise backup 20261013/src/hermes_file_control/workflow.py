"""Host-side analysis workflow; the planner is deliberately an injected pure boundary."""
from __future__ import annotations

import stat
import unicodedata
from pathlib import Path
from typing import Any, Callable

from .broker import Broker
from .planning import manifest_from_proposal, organisation_review_from_proposal, planner_context
from .scanner import scan_library

Planner = Callable[[dict[str, Any]], dict[str, Any]]


def _normalised_component(value: str) -> str:
    """Compare a user-facing directory name without trusting its spelling variant."""
    decomposed = unicodedata.normalize("NFD", value).casefold()
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _destination_reason(destination: Path, documents_root: Path) -> str | None:
    """Return a safe, deterministic rejection reason before a plan is persisted.

    The executor repeats these checks at application time.  This preflight exists so the
    user never receives a plan that is already known to collide or traverse a symlink.
    """
    candidate = documents_root / destination
    if candidate.exists() or candidate.is_symlink():
        return "destination_already_exists"
    current = documents_root
    try:
        root_info = current.lstat()
    except OSError:
        return "documents_root_unavailable"
    if not stat.S_ISDIR(root_info.st_mode) or current.is_symlink():
        return "documents_root_is_not_a_real_directory"
    for part in destination.parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            # All remaining ancestors will be created by the fixed executor.
            return None
        except OSError:
            return "destination_parent_unavailable"
        if current.is_symlink():
            return "destination_parent_is_symlink"
        if not stat.S_ISDIR(info.st_mode):
            return "destination_parent_is_not_a_directory"
    return None


def _preflight(manifest: dict[str, Any], documents_root: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    allowed, excluded = [], []
    for action in manifest["actions"]:
        destination = Path(action["destination"])
        reason = _destination_reason(destination, documents_root)
        if reason:
            excluded.append({"source": action["source"], "destination": action["destination"], "reason": reason})
        else:
            allowed.append(action)
    if not allowed:
        raise ValueError("no proposed action passed destination preflight")
    return {"version": 2, "actions": allowed}, excluded


def _details(manifest: dict[str, Any], excluded: list[dict[str, str]]) -> dict[str, Any]:
    actions = [{"source": item["source"], "destination": item["destination"]} for item in manifest["actions"]]
    confidence = "low" if any(
        _normalised_component(Path(item["destination"]).parts[0]) == "a_trier" for item in actions
    ) else "medium"
    ambiguities = [
        {"source": item["source"], "destination": item["destination"], "reason": "sent_to_a_trier"}
        for item in actions
        if _normalised_component(Path(item["destination"]).parts[0]) == "a_trier"
    ]
    return {"confidence": confidence, "actions": actions, "ambiguities": ambiguities, "excluded": excluded,
            "organization_review": [], "learning": {"learned": 0, "missing": []}}


def analyse(owner: str, home: Path, broker: Broker, planner: Planner, sha256_max_bytes: int) -> dict[str, Any]:
    """Create a proposed plan only.  This function has no apply path."""
    inventory = scan_library(home, sha256_max_bytes)
    reconciliation = broker.store.reconcile_a_trier(inventory["documents"], home / "Documents", sha256_max_bytes)
    if not inventory["downloads"]["files"]:
        raise ValueError("no eligible downloads visible to this process")
    context = planner_context(inventory, learning_hints=broker.store.learning_hints(inventory["downloads"]["files"]))
    last_error: ValueError | None = None
    manifest = None
    proposal: dict[str, Any] | None = None
    # One retry absorbs an occasional conversational/non-conforming model reply.
    # Both attempts remain pure planning calls: no plan exists and no file changes
    # until a strict manifest has passed validation.
    for attempt in range(2):
        try:
            attempt_context = context if attempt == 0 else {
                **context,
                "planner_retry_requirement": "The previous response had no usable actions. Return at least one action when untrusted_downloads is non-empty; use a_trier for uncertain files.",
            }
            proposal = planner(attempt_context)
            manifest = manifest_from_proposal(proposal, inventory)
            break
        except ValueError as exc:
            last_error = exc
    if manifest is None:
        assert last_error is not None
        raise last_error
    manifest, excluded = _preflight(manifest, home / "Documents")
    excluded.extend(
        {"source": item["path"], "reason": item["reason"]}
        for item in inventory["downloads"]["excluded"]
    )
    details = _details(manifest, excluded)
    details["organization_review"] = organisation_review_from_proposal(proposal)
    details["learning"] = reconciliation
    return broker.create_plan(owner, manifest, details)
