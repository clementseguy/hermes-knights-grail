"""Strict, data-only manifest validation shared by broker and executor."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

# Legacy IDs remain usable until their records expire.  New IDs use two French
# words: much easier to type on a phone while the owner-bound broker still
# prevents another Telegram account from using a guessed identifier.
PLAN_ID = re.compile(r"P-(?:[A-Z2-7]{6}|[A-Z2-7]{10})")
PLAN_ADJECTIVES = (
    "agile", "aimable", "ancien", "ardent", "argenté", "azuré", "béni", "brillant", "calme", "célèbre",
    "chantant", "charmant", "clair", "côtier", "crémeux", "curieux", "délicat", "discret", "doré", "doux",
    "drôle", "élégant", "étonnant", "fier", "fragile", "frais", "géant", "givré", "gracieux", "grand",
    "heureux", "humble", "joyeux", "léger", "libre", "lumineux", "magique", "marin", "minuscule", "moderne",
    "naïf", "noble", "paisible", "patient", "précieux", "prêt", "profond", "prudent", "rapide", "rare",
    "rêveur", "riche", "robuste", "royal", "sage", "salé", "secret", "serein", "solaire", "solide",
    "sombre", "tranquille", "vaste", "vif", "zélé",
)
PLAN_NOUNS = (
    "abricot", "aigle", "ancre", "arbre", "atlas", "avion", "baleine", "bateau", "bibliothèque", "bison",
    "brise", "cabane", "café", "carotte", "château", "chemin", "chèvre", "ciel", "citron", "clé",
    "colline", "comète", "corail", "forêt", "frère", "framboise", "fusée", "gâteau", "gazelle", "girafe",
    "grue", "héron", "hiver", "île", "jardin", "koala", "lac", "loutre", "lumière", "lune",
    "maison", "montagne", "nuage", "océan", "orchidée", "ours", "papillon", "pêche", "péridot", "phare",
    "planète", "poésie", "pont", "rivière", "rosée", "sapin", "soleil", "théière", "tigre", "tour",
    "vallée", "vélo", "volcan", "zèbre",
)
SHA256 = re.compile(r"[0-9a-f]{64}")


def canonical_plan_id(value: Any) -> str:
    """Validate an old token or normalize a two-word French plan identifier."""
    if not isinstance(value, str):
        raise ValueError("invalid plan id")
    if PLAN_ID.fullmatch(value.upper()):
        return value.upper()
    normalized = unicodedata.normalize("NFC", value).casefold()
    parts = normalized.split("-")
    if len(parts) == 2 and parts[0] in PLAN_ADJECTIVES and parts[1] in PLAN_NOUNS:
        return normalized
    raise ValueError("invalid plan id")


def safe_relative(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty relative path")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError(f"{field} contains control or invisible formatting characters")
    candidate = PurePath(value)
    if candidate.is_absolute() or "." in candidate.parts or ".." in candidate.parts:
        raise ValueError(f"{field} must remain below its allowed root")
    if any(part.startswith(".") for part in candidate.parts):
        raise ValueError(f"{field} must not reference hidden files or directories")
    return Path(candidate)


@dataclass(frozen=True)
class ExpectedFile:
    device: int
    inode: int
    size: int
    mtime_ns: int
    sha256: str

    @classmethod
    def parse(cls, raw: Any, field: str) -> "ExpectedFile":
        if not isinstance(raw, dict) or set(raw) != {"device", "inode", "size", "mtime_ns", "sha256"}:
            raise ValueError(f"{field} must contain exactly device, inode, size, mtime_ns and sha256")
        values = {key: raw[key] for key in ("device", "inode", "size", "mtime_ns")}
        if any(not isinstance(value, int) or value < 0 for value in values.values()):
            raise ValueError(f"{field} numeric values must be non-negative integers")
        digest = raw["sha256"]
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError(f"{field}.sha256 must be a lowercase SHA-256 digest")
        return cls(**values, sha256=digest)

    def as_dict(self) -> dict[str, Any]:
        return {"device": self.device, "inode": self.inode, "size": self.size,
                "mtime_ns": self.mtime_ns, "sha256": self.sha256}


@dataclass(frozen=True)
class Action:
    source: Path
    destination: Path
    expected: ExpectedFile


def parse_manifest(raw: Any) -> list[Action]:
    if not isinstance(raw, dict) or set(raw) != {"version", "actions"} or raw["version"] != 2:
        raise ValueError("manifest must contain exactly version: 2 and actions")
    actions = raw["actions"]
    if not isinstance(actions, list) or not actions:
        raise ValueError("manifest actions must be a non-empty list")
    parsed: list[Action] = []
    destinations: set[Path] = set()
    sources: set[Path] = set()
    for index, item in enumerate(actions, 1):
        if not isinstance(item, dict) or set(item) != {"source", "destination", "expected"}:
            raise ValueError(f"actions[{index}] has unexpected fields")
        source = safe_relative(item["source"], f"actions[{index}].source")
        destination = safe_relative(item["destination"], f"actions[{index}].destination")
        if source in sources or destination in destinations:
            raise ValueError("a source or destination is duplicated")
        sources.add(source)
        destinations.add(destination)
        parsed.append(Action(source, destination, ExpectedFile.parse(item["expected"], f"actions[{index}].expected")))
    return parsed


def canonical_manifest(raw: Any) -> dict[str, Any]:
    actions = parse_manifest(raw)
    return {"version": 2, "actions": [
        {"source": str(action.source), "destination": str(action.destination), "expected": action.expected.as_dict()}
        for action in actions
    ]}


def manifest_bytes(raw: Any) -> bytes:
    return json.dumps(canonical_manifest(raw), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_digest(raw: Any) -> str:
    return hashlib.sha256(manifest_bytes(raw)).hexdigest()


def fingerprint(path: Path) -> ExpectedFile:
    info = path.lstat()
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return ExpectedFile(info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, digest.hexdigest())
