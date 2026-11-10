"""Tests for how scraped page paths are mapped to saved filenames."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import load_script

scraper = load_script("scrape-gcd-docs")

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIRS = ("docs-raw", "docs-raw-s3ns")
BASE_URL = "https://docs.example.test"
ARTICLE = "Body text long enough to pass the minimum length check of the saver. " * 3


def _page(title: str, links: tuple[str, ...] = ()) -> str:
    anchors = "".join(f'<a href="{link}">{link}</a>' for link in links)
    return (
        f"<html><head><title>{title} | GCD</title></head><body>"
        f'<article class="devsite-article"><p>{title}: {ARTICLE}</p>{anchors}</article></body></html>'
    )


class AssignFilenamesTest(unittest.TestCase):
    def test_assignFilenames_withDocsAndProductLanding_keepsBothPages(self):
        names = scraper.assign_filenames(["/docs/storage", "/storage/docs"])

        self.assertEqual(names["/storage/docs"], "storage.md")
        self.assertEqual(names["/docs/storage"], "docs_storage.md")

    def test_assignFilenames_withNestedCollision_prefixesOnlyTheDocsPath(self):
        names = scraper.assign_filenames(["/docs/storage/a", "/storage/docs/a"])

        self.assertEqual(names["/storage/docs/a"], "storage_a.md")
        self.assertEqual(names["/docs/storage/a"], "docs_storage_a.md")

    def test_assignFilenames_withoutCollision_matchesPathToFilename(self):
        paths = ["/docs", "/docs/quotas/tpc-differences", "/compute/docs/disks", "/products"]

        names = scraper.assign_filenames(paths)

        self.assertEqual(names, {p: scraper.path_to_filename(p) for p in paths})

    def test_assignFilenames_isIndependentOfInputOrder(self):
        paths = ["/storage/docs", "/docs/storage", "/compute/docs"]

        self.assertEqual(scraper.assign_filenames(paths), scraper.assign_filenames(reversed(paths)))

    def test_assignFilenames_withUnresolvableCollision_raisesValueError(self):
        # Both are product paths, so neither can take the docs_ prefix.
        with self.assertRaises(ValueError) as ctx:
            scraper.assign_filenames(["/a/docs/b_c", "/a/docs/b/c"])

        self.assertIn("a_b_c.md", str(ctx.exception))

    def test_assignFilenames_whenPrefixedNameIsTaken_raisesValueError(self):
        with self.assertRaises(ValueError):
            scraper.assign_filenames(["/docs/storage", "/storage/docs", "/docs/docs/storage"])


class CommittedManifestsTest(unittest.TestCase):
    def test_assignFilenames_onCommittedManifests_isOneToOne(self):
        for region_dir in MANIFEST_DIRS:
            with self.subTest(region=region_dir):
                manifest = json.loads((REPO_ROOT / region_dir / "_manifest.json").read_text(encoding="utf-8"))

                names = scraper.assign_filenames(manifest)

                self.assertEqual(len(set(names.values())), len(manifest))


class CrawlSavesCollidingPagesTest(unittest.TestCase):
    def test_crawl_withDocsHubAndProductLanding_savesBothPages(self):
        pages = {
            "/docs": _page("Hub", links=("/docs/storage",)),
            "/docs/storage": _page("Storage category"),
            "/storage/docs": _page("Cloud Storage documentation"),
        }

        def fake_fetch(_base, path, _headers):
            if path not in pages:
                return None
            return {"html": pages[path], "final_url": BASE_URL + path}

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "docs-raw"
            with mock.patch.object(scraper, "fetch_http", fake_fetch), contextlib.redirect_stdout(io.StringIO()):
                manifest = scraper.crawl_and_scrape(out, "berlin", workers=2)

            self.assertEqual(manifest["/storage/docs"]["filename"], "storage.md")
            self.assertEqual(manifest["/docs/storage"]["filename"], "docs_storage.md")
            self.assertIn("Cloud Storage documentation:", (out / "storage.md").read_text(encoding="utf-8"))
            self.assertIn("Storage category:", (out / "docs_storage.md").read_text(encoding="utf-8"))

    def test_crawl_whenRivalPageMissingThisRun_keepsPreviousFilename(self):
        pages = {
            "/docs": _page("Hub", links=("/docs/storage",)),
            "/docs/storage": _page("Storage category"),
        }

        def fake_fetch(_base, path, _headers):
            if path not in pages:
                return None
            return {"html": pages[path], "final_url": BASE_URL + path}

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "docs-raw"
            out.mkdir()
            previous = {"/storage/docs": {"filename": "storage.md"}, "/docs/storage": {"filename": "docs_storage.md"}}
            (out / "_manifest.json").write_text(json.dumps(previous), encoding="utf-8")
            with mock.patch.object(scraper, "fetch_http", fake_fetch), contextlib.redirect_stdout(io.StringIO()):
                manifest = scraper.crawl_and_scrape(out, "berlin", workers=2)

            self.assertEqual(manifest["/docs/storage"]["filename"], "docs_storage.md")


class ReadManifestPathsTest(unittest.TestCase):
    def test_readManifestPaths_withCorruptFile_returnsEmptySet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "_manifest.json"
            path.write_text("{not json", encoding="utf-8")

            self.assertEqual(scraper.read_manifest_paths(path), set())

    def test_readManifestPaths_withMissingFile_returnsEmptySet(self):
        self.assertEqual(scraper.read_manifest_paths(Path("/nonexistent/_manifest.json")), set())


if __name__ == "__main__":
    unittest.main()
