"""Lecture publique HTTPS bornée, utilisée si web_extract Hermes ne sait pas extraire."""
from __future__ import annotations

import ipaddress
import http.client
import socket
import ssl
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

MAX_BYTES = 1_000_000
MAX_TEXT = 30_000


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.tag_stack = []
        self.current = []
        self.lines = []
        self.title = []

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        if tag in {"script", "style", "nav", "footer", "header", "aside", "form", "svg"}:
            self.skip += 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"} and not self.skip:
            self.current = []

    def handle_endtag(self, tag):
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"} and not self.skip:
            value = " ".join("".join(self.current).split())
            if value and (not self.lines or self.lines[-1] != value):
                self.lines.append(value)
            self.current = []
        if tag in {"script", "style", "nav", "footer", "header", "aside", "form", "svg"} and self.skip:
            self.skip -= 1
        if self.tag_stack:
            self.tag_stack.pop()

    def handle_data(self, data):
        if self.skip:
            return
        if "title" in self.tag_stack:
            self.title.append(data)
        if any(tag in self.tag_stack for tag in ("p", "h1", "h2", "h3", "li", "blockquote")):
            self.current.append(data)


def _public_https(value: str):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("URL HTTPS publique requise")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("hôte local interdit")
    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("résolution DNS impossible") from exc
    if not addresses or any(not item.is_global for item in addresses):
        raise ValueError("adresse non publique interdite")
    return parsed, str(sorted(addresses, key=str)[0])


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str):
        super().__init__(host, 443, timeout=12, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), timeout=12)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


def read_public_article(value: str) -> dict:
    """Aucun cookie ni authentification ; refuse les redirections privées et les gros corps."""
    current = value
    for _ in range(4):
        parsed, address = _public_https(current)
        connection = _PinnedHTTPS(parsed.hostname, address)
        try:
            target = parsed.path or "/"
            if parsed.query:
                target += "?" + parsed.query
            connection.request("GET", target, headers={"User-Agent": "LeodaganEditorial/1.0 (public article reader)",
                                                        "Accept": "text/html,text/plain", "Accept-Encoding": "identity"})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("redirection sans destination") from None
                current = urljoin(current, location)
                continue
            if response.status >= 400:
                return {"url": current, "access_status": "inaccessible", "http_status": response.status,
                        "accessed_at": datetime.now(timezone.utc).isoformat(), "error": f"HTTP {response.status}"}
            kind = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            if kind not in ("text/html", "text/plain"):
                raise ValueError("type de contenu non textuel refusé")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("article trop volumineux")
            content_type = response.getheader("Content-Type", "")
            charset = next((part.split("=", 1)[1].strip() for part in content_type.split(";")[1:]
                            if part.strip().lower().startswith("charset=")), "utf-8")
            decoded = body.decode(charset, errors="replace")
            if kind == "text/html":
                parser = _Text()
                parser.feed(decoded)
                title = " ".join("".join(parser.title).split())[:300]
                article = "\n\n".join(parser.lines)[:MAX_TEXT]
            else:
                title = ""
                article = decoded[:MAX_TEXT]
            return {"url": current, "access_status": "read" if len(article) >= 200 else "partial",
                    "http_status": response.status, "accessed_at": datetime.now(timezone.utc).isoformat(),
                    "title": title, "text": article, "truncated": len(article) >= MAX_TEXT}
        except (OSError, TimeoutError, ssl.SSLError, LookupError) as exc:
            return {"url": current, "access_status": "inaccessible", "http_status": None,
                    "accessed_at": datetime.now(timezone.utc).isoformat(), "error": type(exc).__name__}
        finally:
            connection.close()
    raise ValueError("trop de redirections")
