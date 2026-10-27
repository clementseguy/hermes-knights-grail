import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("reader", Path(__file__).parents[1] / "plugins/leodagan-editorial/reader.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReaderTests(unittest.TestCase):
    def test_rejects_non_public_targets_and_ports(self):
        for target in ("http://example.org/", "https://localhost/a", "https://127.0.0.1/a",
                       "https://10.0.0.1/a", "https://example.org:8443/a", "https://user:pass@example.org/a"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                reader._public_https(target)

    def test_rejects_dns_with_private_answer(self):
        with patch.object(reader.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.215.14", 443)),
                                                                     (2, 1, 6, "", ("192.168.1.2", 443))]):
            with self.assertRaises(ValueError):
                reader._public_https("https://example.org/a")

    def test_extracts_article_without_scripts_or_navigation(self):
        parser = reader._Text()
        parser.feed("<html><head><title>Une thèse</title><script>secret()</script></head>"
                    "<body><nav><p>Menu</p></nav><article><h1>Titre</h1>"
                    "<p>Preuve <b>vérifiée</b>.</p><p>Limite.</p></article></body></html>")
        self.assertEqual(" ".join(parser.title), "Une thèse")
        self.assertEqual(parser.lines, ["Titre", "Preuve vérifiée.", "Limite."])

    def test_reports_403_and_429_without_article_text(self):
        for status in (403, 429):
            with self.subTest(status=status):
                response = unittest.mock.MagicMock()
                response.status = status
                connection = unittest.mock.MagicMock()
                connection.getresponse.return_value = response
                with patch.object(reader, "_public_https", return_value=(reader.urlparse("https://example.org/article"), "93.184.215.14")), \
                     patch.object(reader, "_PinnedHTTPS", return_value=connection):
                    result = reader.read_public_article("https://example.org/article")
                self.assertEqual(result["access_status"], "inaccessible")
                self.assertEqual(result["http_status"], status)
                self.assertNotIn("text", result)
                self.assertEqual(result["reason"], f"HTTP {status}")

    def test_oversize_body_keeps_bounded_partial_text(self):
        response = unittest.mock.MagicMock()
        response.status = 200
        response.getheader.side_effect = lambda key, default="": "text/plain; charset=utf-8" if key == "Content-Type" else default
        response.read.return_value = b"A" * (reader.MAX_BYTES + 1)
        connection = unittest.mock.MagicMock()
        connection.getresponse.return_value = response
        with patch.object(reader, "_public_https", return_value=(reader.urlparse("https://example.org/a"), "93.184.215.14")), \
             patch.object(reader, "_PinnedHTTPS", return_value=connection):
            result = reader.read_public_article("https://example.org/a")
        self.assertEqual(result["access_status"], "partial")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["text"]), reader.MAX_TEXT)
        self.assertEqual(result["url"], "https://example.org/a")

    def test_revalidates_redirect_target(self):
        response = unittest.mock.MagicMock()
        response.status = 302
        response.getheader.return_value = "https://127.0.0.1/private"
        connection = unittest.mock.MagicMock()
        connection.getresponse.return_value = response
        def resolve(host, _port, **_kwargs):
            address = "127.0.0.1" if host == "127.0.0.1" else "93.184.215.14"
            return [(2, 1, 6, "", (address, 443))]
        with patch.object(reader, "_PinnedHTTPS", return_value=connection), \
             patch.object(reader.socket, "getaddrinfo", side_effect=resolve):
            with self.assertRaises(ValueError):
                reader.read_public_article("https://example.org/article")
        self.assertTrue(connection.close.called)


if __name__ == "__main__":
    unittest.main()
