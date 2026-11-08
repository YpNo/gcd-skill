"""A failed fetch must never delete a previously scraped page; only 404/410 may."""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from tests.helpers import load_script

scraper = load_script("scrape-gcd-docs")

BASE_URL = "https://docs.example.test"
ARTICLE = "Body text long enough to pass the minimum length check of the saver. " * 3


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(BASE_URL, code, "error", {}, io.BytesIO(b""))


def _ok_response(body: str) -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status = 200
    resp.geturl.return_value = BASE_URL + "/docs/a"
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__.return_value = resp
    return resp


def _page(title: str) -> str:
    return (
        f"<html><head><title>{title} | GCD</title></head><body>"
        f'<article class="devsite-article"><p>{ARTICLE}</p></article></body></html>'
    )


@mock.patch.object(scraper.time, "sleep", lambda _s: None)
class FetchHttpTests(unittest.TestCase):
    def _fetch_with(self, side_effect):
        with mock.patch.object(scraper.urllib.request, "urlopen", side_effect=side_effect) as m:
            result = scraper.fetch_http(BASE_URL, "/docs/a", {})
        return result, m.call_count

    def test_fetch_http_with_404_returns_gone(self):
        result, _ = self._fetch_with(_http_error(404))
        self.assertEqual(result, {"gone": 404})

    def test_fetch_http_with_410_returns_gone(self):
        result, _ = self._fetch_with(_http_error(410))
        self.assertEqual(result, {"gone": 410})

    def test_fetch_http_with_403_returns_none_without_retry(self):
        result, calls = self._fetch_with(_http_error(403))
        self.assertIsNone(result)
        self.assertEqual(calls, 1)

    def test_fetch_http_with_503_retries_then_returns_none(self):
        result, calls = self._fetch_with(_http_error(503))
        self.assertIsNone(result)
        self.assertEqual(calls, scraper.MAX_RETRIES)

    def test_fetch_http_with_timeout_returns_none(self):
        result, _ = self._fetch_with(TimeoutError("timed out"))
        self.assertIsNone(result)

    def test_fetch_http_with_200_returns_html(self):
        result, _ = self._fetch_with([_ok_response(_page("A"))])
        self.assertIn("html", result)


class CarryOverFailedPagesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        (self.out / "b.md").write_text("previous copy", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_carry_over_with_failed_page_on_disk_keeps_entry(self):
        prev = {"/docs/b": {"filename": "b.md"}}
        self.assertEqual(scraper.carry_over_failed_pages(prev, {"/docs/b"}, self.out), prev)

    def test_carry_over_with_missing_file_skips_entry(self):
        prev = {"/docs/x": {"filename": "x.md"}}
        self.assertEqual(scraper.carry_over_failed_pages(prev, {"/docs/x"}, self.out), {})

    def test_carry_over_with_page_not_failed_skips_entry(self):
        prev = {"/docs/b": {"filename": "b.md"}}
        self.assertEqual(scraper.carry_over_failed_pages(prev, set(), self.out), {})

    def test_carry_over_with_path_in_filename_rejects_entry(self):
        prev = {"/docs/b": {"filename": "../b.md"}}
        self.assertEqual(scraper.carry_over_failed_pages(prev, {"/docs/b"}, self.out), {})


class LoadPreviousManifestTests(unittest.TestCase):
    def test_load_previous_manifest_with_corrupt_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "_manifest.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(scraper.load_previous_manifest(Path(tmp)), {})


class CrawlCleanupTests(unittest.TestCase):
    """End to end: page a refreshes, page b fails (kept), page c is 404 (removed)."""

    def test_crawl_with_failed_and_gone_pages_keeps_only_failed_copy(self):
        responses = {
            "/docs/a": {"html": _page("A"), "final_url": BASE_URL + "/docs/a"},
            "/docs/b": None,
        }

        def fake_fetch(_base, path, _headers):
            return responses.get(path, {"gone": 404})

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "docs-raw"
            out.mkdir()
            prev = {
                p: {"title": p, "filename": f"{p[-1]}.md", "last_updated": "2026-01-01"}
                for p in ("/docs/a", "/docs/b", "/docs/c")
            }
            (out / "_manifest.json").write_text(json.dumps(prev), encoding="utf-8")
            for name in ("a.md", "b.md", "c.md"):
                (out / name).write_text("previous copy", encoding="utf-8")

            with mock.patch.object(scraper, "fetch_http", fake_fetch):
                manifest = scraper.crawl_and_scrape(out, "berlin", workers=2)

            self.assertEqual(sorted(manifest), ["/docs/a", "/docs/b"])
            self.assertIn("Body text", (out / "a.md").read_text(encoding="utf-8"))
            self.assertEqual((out / "b.md").read_text(encoding="utf-8"), "previous copy")
            self.assertFalse((out / "c.md").exists())


if __name__ == "__main__":
    unittest.main()
