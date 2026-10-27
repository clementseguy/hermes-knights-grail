"""Registre métier privé, sans dépendance au cœur Hermes."""
from __future__ import annotations

import json
import hashlib
import ipaddress
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


WORDS_A = ("café", "chêne", "étoile", "rivage", "silex", "nuage", "forêt", "aurore")
WORDS_B = ("géant", "lucide", "discret", "solide", "vigilant", "bleu", "doré", "franc")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.strip().casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", value)


def valid_id(value: str) -> bool:
    return bool(re.fullmatch(r"[^\W\d_]+-[^\W\d_]+", unicodedata.normalize("NFC", value), re.UNICODE))


def url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL HTTPS publique requise")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("hôte local interdit")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("adresse non publique interdite")
    return value


def length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("LEODAGAN_DB", "/opt/data/editorial.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=30000")
        self.migrate()

    def migrate(self):
        self.db.executescript("""
        BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS drafts(
          id TEXT PRIMARY KEY, id_key TEXT NOT NULL UNIQUE,
          intent TEXT NOT NULL, origin_platform TEXT NOT NULL, origin_thread TEXT NOT NULL,
          message_key TEXT UNIQUE, status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS requested_sources(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          url TEXT NOT NULL, PRIMARY KEY(draft_id,url));
        CREATE TABLE IF NOT EXISTS source_events(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          url TEXT NOT NULL, added_at TEXT NOT NULL,
          PRIMARY KEY(draft_id,url));
        CREATE TABLE IF NOT EXISTS versions(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          version INTEGER NOT NULL, post_text TEXT NOT NULL, char_count INTEGER NOT NULL,
          image_prompt TEXT NOT NULL, reasoning_note TEXT NOT NULL, sources_json TEXT NOT NULL,
          created_at TEXT NOT NULL, PRIMARY KEY(draft_id, version));
        CREATE TABLE IF NOT EXISTS publications(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          version INTEGER NOT NULL, linkedin_url TEXT, final_text TEXT NOT NULL,
          origin TEXT NOT NULL, comparison TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(draft_id, version));
        CREATE TABLE IF NOT EXISTS metrics(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          metric_type TEXT NOT NULL, value INTEGER NOT NULL,
          origin TEXT NOT NULL, observed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS rules(
          id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL,
          origin_draft TEXT REFERENCES drafts(id) ON DELETE SET NULL,
          created_at TEXT NOT NULL, revoked_at TEXT);
        CREATE TABLE IF NOT EXISTS deliveries(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          version INTEGER NOT NULL, platform TEXT NOT NULL, thread TEXT NOT NULL,
          state TEXT NOT NULL, attempted_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS editorial_reviews(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          base_version INTEGER NOT NULL,
          post_text TEXT NOT NULL, image_prompt TEXT NOT NULL,
          reasoning_note TEXT NOT NULL, sources_json TEXT NOT NULL,
          candidate_hash TEXT NOT NULL,
          status TEXT NOT NULL, report_json TEXT,
          provider TEXT, model TEXT,
          created_at TEXT NOT NULL, reviewed_at TEXT);
        CREATE TABLE IF NOT EXISTS review_version_links(
          draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          version INTEGER NOT NULL, review_id INTEGER NOT NULL UNIQUE
            REFERENCES editorial_reviews(id),
          PRIMARY KEY(draft_id,version));
        INSERT OR IGNORE INTO source_events(draft_id,url,added_at)
          SELECT s.draft_id,s.url,d.created_at FROM requested_sources s
          JOIN drafts d ON d.id=s.draft_id;
        PRAGMA user_version=2;
        COMMIT;
        """)

    def _resolve(self, identifier: str) -> str:
        row = self.db.execute("SELECT id FROM drafts WHERE id_key=?", (key(identifier),)).fetchone()
        if not row:
            raise KeyError("brouillon introuvable")
        return row["id"]

    def create(self, intent: str, urls: list[str], platform: str, thread: str, message_key: str = "", identifier: str = "") -> dict:
        if not intent.strip() or not urls:
            raise ValueError("intention et au moins un lien requis")
        for item in urls:
            url(item)
        if platform not in ("slack", "telegram") or not thread or not message_key:
            raise ValueError("origine Slack/Telegram, fil et identifiant de message requis")
        message_key = f"{platform}:{thread}:{message_key}"
        with self.db:
            if message_key:
                row = self.db.execute("SELECT id FROM drafts WHERE message_key=?", (message_key,)).fetchone()
                if row:
                    return {"id": row["id"], "replayed": True}
            if identifier:
                identifier = unicodedata.normalize("NFC", identifier)
                if not valid_id(identifier):
                    raise ValueError("identifiant : deux mots français reliés par un tiret")
            else:
                from secrets import randbelow
                for _ in range(128):
                    candidate = f"{WORDS_A[randbelow(len(WORDS_A))]}-{WORDS_B[randbelow(len(WORDS_B))]}"
                    if not self.db.execute("SELECT 1 FROM drafts WHERE id_key=?", (key(candidate),)).fetchone():
                        identifier = candidate
                        break
                else:
                    raise RuntimeError("espace d'identifiants épuisé")
            self.db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?)",
                (identifier, key(identifier), intent.strip(), platform, thread, message_key or None, "RESEARCH", now()))
            for item in urls:
                self.db.execute("INSERT INTO requested_sources VALUES(?,?)", (identifier, item))
                self.db.execute("INSERT INTO source_events VALUES(?,?,?)", (identifier, item, now()))
        return {"id": identifier, "status": "RESEARCH", "urls": urls}

    def add_source(self, identifier: str, source_url: str) -> dict:
        url(source_url)
        with self.db:
            draft_id = self._resolve(identifier)
            result = self.db.execute("INSERT OR IGNORE INTO requested_sources VALUES(?,?)", (draft_id, source_url))
            if result.rowcount:
                self.db.execute("INSERT INTO source_events VALUES(?,?,?)", (draft_id, source_url, now()))
        return {"id": draft_id, "url": source_url, "added": bool(result.rowcount)}

    def _validate_candidate(self, identifier: str, post: str, image_prompt: str,
                            reasoning: str, sources: list[dict]) -> tuple[str, int]:
        count = length(post)
        if not post.strip() or count > 3000:
            raise ValueError(f"post invalide : {count} unités UTF-16 (maximum 3000)")
        if not image_prompt.strip() or "16:9" not in image_prompt:
            raise ValueError("prompt image 16:9 requis")
        if not sources or not all(isinstance(s, dict) and all(k in s for k in ("url", "access_status", "accessed_at", "critical_review")) for s in sources):
            raise ValueError("sources et lecture critique par article requises")
        seen = set()
        for source in sources:
            url(source["url"])
            if source["url"] in seen:
                raise ValueError("source répétée")
            seen.add(source["url"])
            if source.get("final_url"):
                url(source["final_url"])
            if source["access_status"] not in ("read", "partial", "inaccessible", "user"):
                raise ValueError("état d'accès à la source invalide")
            try:
                accessed = datetime.fromisoformat(source["accessed_at"])
                if accessed.tzinfo is None:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError("date de consultation horodatée requise") from None
            review = source["critical_review"]
            if not isinstance(review, dict) or not all(review.get(k) for k in ("thesis", "evidence", "limits", "cto_objection", "executive_impact")):
                raise ValueError("note critique incomplète")
        draft_id = self._resolve(identifier)
        requested = {r[0] for r in self.db.execute("SELECT url FROM requested_sources WHERE draft_id=?", (draft_id,))}
        if requested != seen:
            raise ValueError("chaque article demandé doit avoir une note de source ; ajouter les nouveaux liens avec editorial_add_source")
        return draft_id, count

    def prepare_review(self, identifier: str, post: str, image_prompt: str,
                       reasoning: str, sources: list[dict]) -> dict:
        draft_id, count = self._validate_candidate(identifier, post, image_prompt, reasoning, sources)
        payload = json.dumps({"post": post, "image_prompt": image_prompt, "reasoning": reasoning,
                              "sources": sources}, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self.db:
            current = self.db.execute("SELECT COALESCE(MAX(version),0) FROM versions WHERE draft_id=?", (draft_id,)).fetchone()[0]
            cursor = self.db.execute("INSERT INTO editorial_reviews(draft_id,base_version,post_text,image_prompt,reasoning_note,sources_json,candidate_hash,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (draft_id, current, post, image_prompt, reasoning, json.dumps(sources, ensure_ascii=False), digest, "PENDING", now()))
        return {"review_id": cursor.lastrowid, "id": draft_id, "candidate_hash": digest,
                "char_count": count, "base_version": current}

    def complete_review(self, review_id: int, report: dict, provider: str, model: str) -> dict:
        roles = ("dsi", "cto", "rssi", "ceo")
        if report.get("verdict") not in ("approve", "revise") or not all(
            isinstance(report.get(role), dict) and report[role].get("finding") and
            report[role].get("severity") in ("ok", "minor", "blocking") for role in (*roles, "source_check", "voice_check")
        ) or not isinstance(report.get("required_changes"), list) or not all(
            isinstance(item, str) and item.strip() for item in report["required_changes"]
        ):
            raise ValueError("rapport de relecture incomplet")
        approved = (report["verdict"] == "approve" and
                    not report["required_changes"] and
                    all(report[role]["severity"] != "blocking" for role in (*roles, "source_check", "voice_check")))
        status = "APPROVED" if approved else "CHANGES_REQUIRED"
        with self.db:
            result = self.db.execute("UPDATE editorial_reviews SET status=?,report_json=?,provider=?,model=?,reviewed_at=? WHERE id=? AND status='PENDING'",
                (status, json.dumps(report, ensure_ascii=False), provider, model, now(), review_id))
            if not result.rowcount:
                raise ValueError("relecture absente ou déjà terminée")
        return {"review_id": review_id, "status": status, "report": report,
                "provider": provider, "model": model}

    def fail_review(self, review_id: int, reason: str) -> None:
        with self.db:
            self.db.execute("UPDATE editorial_reviews SET status='ERROR',report_json=?,reviewed_at=? WHERE id=? AND status='PENDING'",
                            (json.dumps({"reason": reason}), now(), review_id))

    def save(self, identifier: str, review_id: int) -> dict:
        with self.db:
            draft_id = self._resolve(identifier)
            row = self.db.execute("SELECT * FROM editorial_reviews WHERE id=? AND draft_id=? AND status='APPROVED'", (review_id, draft_id)).fetchone()
            if row is None:
                raise ValueError("relecture indépendante approuvée requise")
            if self.db.execute("SELECT 1 FROM review_version_links WHERE review_id=?", (review_id,)).fetchone():
                raise ValueError("relecture déjà utilisée")
            post, image_prompt, reasoning = row["post_text"], row["image_prompt"], row["reasoning_note"]
            sources = json.loads(row["sources_json"])
            _, count = self._validate_candidate(identifier, post, image_prompt, reasoning, sources)
            current = self.db.execute("SELECT COALESCE(MAX(version),0) FROM versions WHERE draft_id=?", (draft_id,)).fetchone()[0]
            if current != row["base_version"]:
                raise ValueError("relecture périmée : une autre version a été enregistrée")
            version = current + 1
            self.db.execute("INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)",
                (draft_id, version, post, count, image_prompt, reasoning, json.dumps(sources, ensure_ascii=False), now()))
            self.db.execute("INSERT INTO review_version_links VALUES(?,?,?)", (draft_id, version, review_id))
            self.db.execute("UPDATE drafts SET status='SAVED' WHERE id=?", (draft_id,))
        return {"id": draft_id, "version": version, "char_count": count, "status": "SAVED",
                "review_id": review_id, "candidate_hash": row["candidate_hash"]}

    def get(self, identifier: str) -> dict:
        draft_id = self._resolve(identifier)
        draft = dict(self.db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone())
        versions = [dict(r) for r in self.db.execute("SELECT * FROM versions WHERE draft_id=? ORDER BY version", (draft_id,))]
        for row in versions:
            row["sources"] = json.loads(row.pop("sources_json"))
        draft["versions"] = versions
        draft["requested_urls"] = [r[0] for r in self.db.execute("SELECT url FROM requested_sources WHERE draft_id=? ORDER BY url", (draft_id,))]
        draft["source_events"] = [dict(r) for r in self.db.execute("SELECT url,added_at FROM source_events WHERE draft_id=? ORDER BY added_at,url", (draft_id,))]
        draft["reviews"] = [dict(r) for r in self.db.execute("SELECT r.id,r.base_version,r.candidate_hash,r.status,r.report_json,r.provider,r.model,r.created_at,r.reviewed_at,l.version FROM editorial_reviews r LEFT JOIN review_version_links l ON l.review_id=r.id WHERE r.draft_id=? ORDER BY r.id", (draft_id,))]
        for row in draft["reviews"]:
            row["report"] = json.loads(row.pop("report_json")) if row["report_json"] else None
        draft["publications"] = [dict(r) for r in self.db.execute("SELECT * FROM publications WHERE draft_id=? ORDER BY version", (draft_id,))]
        draft["metrics"] = [dict(r) for r in self.db.execute("SELECT * FROM metrics WHERE draft_id=? ORDER BY observed_at", (draft_id,))]
        return draft

    def feedback(self, identifier: str, final_text: str, origin: str, comparison: str,
                 explicit_rule: str = "", linkedin_url: str = "", metrics: list[dict] | None = None) -> dict:
        if origin not in ("official_api", "public_page", "user") or not final_text.strip() or not comparison.strip():
            raise ValueError("texte final, origine et comparaison requis")
        if linkedin_url:
            url(linkedin_url)
        metrics = metrics or []
        for metric in metrics:
            if metric.get("type") not in ("IMPRESSION", "REACTION", "LIKE_MANUAL") or type(metric.get("value")) is not int or metric["value"] < 0 or not metric.get("origin"):
                raise ValueError("métrique invalide")
        with self.db:
            draft_id = self._resolve(identifier)
            version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM publications WHERE draft_id=?", (draft_id,)).fetchone()[0]
            self.db.execute("INSERT INTO publications VALUES(?,?,?,?,?,?,?)", (draft_id, version, linkedin_url or None, final_text, origin, comparison, now()))
            for metric in metrics:
                self.db.execute("INSERT INTO metrics VALUES(?,?,?,?,?)", (draft_id, metric["type"], metric["value"], metric["origin"], now()))
            if explicit_rule.strip():
                self.db.execute("INSERT INTO rules(text,origin_draft,created_at) VALUES(?,?,?)", (explicit_rule.strip(), draft_id, now()))
        return {"id": draft_id, "publication_version": version, "rule_recorded": bool(explicit_rule.strip())}

    def rules(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT id,text,origin_draft,created_at FROM rules WHERE revoked_at IS NULL ORDER BY id")]

    def revoke_rule(self, rule_id: int) -> bool:
        with self.db:
            return bool(self.db.execute("UPDATE rules SET revoked_at=? WHERE id=? AND revoked_at IS NULL", (now(), rule_id)).rowcount)

    def update_rule(self, rule_id: int, text: str) -> bool:
        if not text.strip():
            raise ValueError("texte de règle requis")
        with self.db:
            return bool(self.db.execute("UPDATE rules SET text=? WHERE id=? AND revoked_at IS NULL", (text.strip(), rule_id)).rowcount)

    def delivery(self, identifier: str, version: int, platform: str, thread: str, state: str) -> None:
        if state not in ("SENT", "FAILED", "PARTIAL"):
            raise ValueError("état de livraison invalide")
        with self.db:
            self.db.execute("INSERT INTO deliveries VALUES(?,?,?,?,?,?)", (self._resolve(identifier), version, platform, thread, state, now()))
