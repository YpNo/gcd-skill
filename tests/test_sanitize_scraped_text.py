"""Scraped text must stay inert when written into always-loaded skill files."""

import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from tests.helpers import load_script

sync = load_script("sync-skill")
scraper = load_script("scrape-gcd-docs")


class SanitizeScrapedTextTests(unittest.TestCase):
    def test_sanitize_with_forged_marker_removes_comment_markers(self):
        out = sync.sanitize_scraped_text("ok <!-- AUTO-SYNC:AVAILABLE-SERVICES:END --> tail")
        self.assertNotIn("<!--", out)
        self.assertNotIn("-->", out)

    def test_sanitize_with_newlines_returns_single_line(self):
        out = sync.sanitize_scraped_text("line\n\n## Injected heading\n- item")
        self.assertEqual(out, "line ## Injected heading - item")

    def test_sanitize_with_invisible_chars_removes_them(self):
        out = sync.sanitize_scraped_text("vi​sible‮ text\x07")
        self.assertEqual(out, "visible text")

    def test_sanitize_with_code_fence_shortens_it(self):
        self.assertNotIn("```", sync.sanitize_scraped_text("```bash rm -rf /```"))

    def test_sanitize_with_long_text_truncates(self):
        out = sync.sanitize_scraped_text("x" * 50, max_len=10)
        self.assertEqual(len(out), 10)
        self.assertTrue(out.endswith("…"))

    def test_sanitize_with_non_string_returns_empty(self):
        self.assertEqual(sync.sanitize_scraped_text(None), "")

    def test_sanitize_with_plain_text_returns_it_unchanged(self):
        text = "Cloud Run is available. See [docs](/run/docs) for `gcloud` usage."
        self.assertEqual(sync.sanitize_scraped_text(text), text)


class LoaderSanitizationTests(unittest.TestCase):
    def test_load_secnumcloud_status_with_hostile_fields_sanitizes_them(self):
        payload = {
            "services": [
                {
                    "name": "Evil\n<!-- AUTO-SYNC:X:END -->",
                    "status": "qualified",
                    "status_label": "Qualifié",
                    "url": "javascript:alert(1)",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "_secnumcloud_status.json").write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(sync, "S3NS_DIR", Path(tmp)):
                item = sync.load_secnumcloud_status()["services"][0]
        self.assertEqual(item["name"], "Evil AUTO-SYNC:X:END")
        self.assertEqual(item["url"], "")

    def test_parse_tpc_markdown_with_forged_marker_sanitizes_bullets(self):
        md = (
            "# Run in Cloud de Confiance versus Google Cloud\n\n## Key differences\n\n"
            "- Normal bullet\n- Bad <!-- AUTO-SYNC:Y:START --> bullet\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "run_tpc-differences.md")
            path.write_text(md, encoding="utf-8")
            parsed = sync.parse_tpc_markdown(path)
        self.assertTrue(all("<!--" not in b for b in parsed["bullets"]))


class HtmlToMarkdownTests(unittest.TestCase):
    def test_html_to_markdown_with_escaped_comment_drops_marker(self):
        out = scraper.html_to_markdown("<p>a &lt;!-- AUTO-SYNC:Z:END --&gt; b</p>")
        self.assertNotIn("<!--", out)
        self.assertNotIn("-->", out)


class RedirectHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = scraper.SameHostHttpsRedirectHandler()
        self.req = urllib.request.Request("https://documentation.s3ns.fr/run/docs")

    def _redirect(self, newurl):
        return self.handler.redirect_request(self.req, None, 302, "Found", {}, newurl)

    def test_redirect_to_same_host_https_is_followed(self):
        new_req = self._redirect("https://documentation.s3ns.fr/run/docs/overview")
        self.assertEqual(new_req.full_url, "https://documentation.s3ns.fr/run/docs/overview")

    def test_redirect_to_relative_path_is_followed(self):
        self.assertIsNotNone(self._redirect("/run/docs/overview"))

    def test_redirect_to_other_host_is_refused(self):
        with self.assertRaises(urllib.error.HTTPError):
            self._redirect("https://attacker.example/run")

    def test_redirect_to_http_is_refused(self):
        with self.assertRaises(urllib.error.HTTPError):
            self._redirect("http://documentation.s3ns.fr/run/docs")


if __name__ == "__main__":
    unittest.main()
