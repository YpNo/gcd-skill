"""Root-relative links copied from scraped docs must point at the docs site, not github.com."""

import re
import tempfile
import unittest
from pathlib import Path

from tests.helpers import load_script

sync = load_script("sync-skill")
scraper = load_script("scrape-gcd-docs")

S3NS_BASE = "https://documentation.s3ns.fr"
BERLIN_BASE = "https://berlin.devsitetest.how"
ROOT_RELATIVE_LINK_RE = re.compile(r"\]\(\s*<?/(?!/)")

TPC_PAGE = """# Example in Cloud de Confiance versus Google Cloud

## Key differences

- Set up the [gcloud CLI](/docs/get-started-tpc/setup-gcloud) first.
- Unchanged: [external](https://example.com/a), [same page](#top), [protocol](//cloud.google.com/x).

### Features

| **Quota increase** | Follow the steps to [request](/docs/quotas/help/request_increase "Request"). |
"""


def _write_page(root: Path, region_dir: str) -> Path:
    page = root / region_dir / "example_tpc-differences.md"
    page.parent.mkdir()
    page.write_text(TPC_PAGE, encoding="utf-8")
    return page


class AbsolutizeDocLinksTests(unittest.TestCase):
    def test_absolutizeDocLinks_rootRelativeLink_prefixesBaseUrl(self):
        self.assertEqual(
            sync.absolutize_doc_links("See [setup](/docs/setup#cli).", S3NS_BASE),
            f"See [setup]({S3NS_BASE}/docs/setup#cli).",
        )

    def test_absolutizeDocLinks_linkWithTitleOrAngleBrackets_prefixesBaseUrl(self):
        self.assertEqual(
            sync.absolutize_doc_links('[a](/x "T") [b](</y>)', S3NS_BASE),
            f'[a]({S3NS_BASE}/x "T") [b](<{S3NS_BASE}/y>)',
        )

    def test_absolutizeDocLinks_nonRootRelativeTargets_leftUnchanged(self):
        text = "[a](https://e.com/x) [b](//cloud.google.com/x) [c](#top) [d](services.md) (/not-a-link)"
        self.assertEqual(sync.absolutize_doc_links(text, S3NS_BASE), text)


class DocsBaseUrlTests(unittest.TestCase):
    def test_docsBaseUrlFor_eachScraperRegion_matchesScraperBaseUrl(self):
        for region in scraper.REGIONS.values():
            page = Path(region["default_output_dir"]) / "x.md"
            self.assertEqual(sync.docs_base_url_for(page), region["base_url"])

    def test_docsBaseUrlFor_unknownDirectory_returnsNone(self):
        self.assertIsNone(sync.docs_base_url_for(Path("elsewhere") / "x.md"))


class ParseTpcMarkdownLinkTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_parseTpcMarkdown_s3nsPage_linksResolveToS3nsDocs(self):
        parsed = sync.parse_tpc_markdown(_write_page(self.root, "docs-raw-s3ns"))
        self.assertIn(f"]({S3NS_BASE}/docs/get-started-tpc/setup-gcloud)", parsed["bullets"][0])
        (_, rows), = parsed["sections"]
        self.assertIn(f"]({S3NS_BASE}/docs/quotas/help/request_increase", rows[0][1])

    def test_parseTpcMarkdown_berlinPage_linksResolveToBerlinDocs(self):
        parsed = sync.parse_tpc_markdown(_write_page(self.root, "docs-raw"))
        self.assertIn(f"]({BERLIN_BASE}/docs/get-started-tpc/setup-gcloud)", parsed["bullets"][0])

    def test_parseTpcMarkdown_otherLinks_leftUnchanged(self):
        parsed = sync.parse_tpc_markdown(_write_page(self.root, "docs-raw-s3ns"))
        self.assertIn("[protocol](//cloud.google.com/x)", parsed["bullets"][1])
        self.assertIn("[same page](#top)", parsed["bullets"][1])

    def test_parseTpcMarkdown_unknownDirectory_leavesLinksAsScraped(self):
        parsed = sync.parse_tpc_markdown(_write_page(self.root, "elsewhere"))
        self.assertIn("](/docs/get-started-tpc/setup-gcloud)", parsed["bullets"][0])

    def test_parseTpcMarkdown_digest_ignoresRegionHost(self):
        # The digest tracks upstream content: rewriting links must not change it,
        # or every curated product with a link would get a spurious UPSTREAM-DIFFS block.
        s3ns = sync.parse_tpc_markdown(_write_page(self.root, "docs-raw-s3ns"))
        berlin = sync.parse_tpc_markdown(_write_page(self.root, "docs-raw"))
        self.assertNotEqual(s3ns["bullets"], berlin["bullets"])
        self.assertEqual(s3ns["digest"], berlin["digest"])


class CommittedSkillFilesTests(unittest.TestCase):
    def test_generatedFiles_containNoRootRelativeLinks(self):
        for path in [sync.SKILL_FILE, *sorted((sync.BASE_DIR / "references").glob("*.md"))]:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(ROOT_RELATIVE_LINK_RE.search(text))


if __name__ == "__main__":
    unittest.main()
