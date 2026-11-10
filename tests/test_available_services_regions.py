"""A service is listed under "Both regions" only when both regions document it."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import load_script

sync = load_script("sync-skill")

BLOCK_START = "<!-- AUTO-SYNC:AVAILABLE-SERVICES:START -->"
BLOCK_END = "<!-- AUTO-SYNC:AVAILABLE-SERVICES:END -->"


def _product(slug: str, display: str, berlin: int, s3ns: int, category: str = "compute") -> dict:
    return {"slug": slug, "display": display, "berlin_pages": berlin, "s3ns_pages": s3ns, "category": category}


def _products(*items: dict) -> dict:
    return {p["slug"]: p for p in items}


def _render_block(products: dict) -> str:
    """Run sync_skill_md on a minimal SKILL.md and return its AVAILABLE-SERVICES block."""
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / "SKILL.md"
        skill.write_text(f"{BLOCK_START}\nold\n{BLOCK_END}\n", encoding="utf-8")
        with mock.patch.object(sync, "SKILL_FILE", skill):
            sync.sync_skill_md({}, products)
        text = skill.read_text(encoding="utf-8")
    return text.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]


def _line(block: str, prefix: str) -> str:
    return next((line for line in block.splitlines() if line.startswith(prefix)), "")


def _names(block: str, prefix: str) -> set[str]:
    """Return the service names listed on the line starting with prefix."""
    listed = _line(block, prefix).removeprefix(prefix).strip().removesuffix(".")
    return {name.strip() for name in listed.split(",") if name.strip()}


BOTH_GENERAL = "**Both regions (Compute, Data, Storage, Security & Ops):**"
BOTH_NETWORKING = "**Both regions (Networking):**"
BERLIN_ONLY = "**Berlin (`u-germany-northeast1`) only:**"
S3NS_ONLY = "**S3NS (`u-france-east1`) only:**"


class AvailableServicesBlockTest(unittest.TestCase):
    def test_syncSkillMd_serviceInBothRegions_listedUnderBoth(self):
        block = _render_block(_products(_product("bigquery", "BigQuery", 3, 2)))

        self.assertIn("BigQuery", _names(block, BOTH_GENERAL))

    def test_syncSkillMd_berlinOnlyService_listedAsBerlinOnly(self):
        block = _render_block(_products(_product("bigquery", "BigQuery", 3, 0)))

        self.assertNotIn("BigQuery", _names(block, BOTH_GENERAL))
        self.assertEqual(_line(block, BERLIN_ONLY), f"{BERLIN_ONLY} BigQuery.")

    def test_syncSkillMd_s3nsOnlyNetworkingService_listedAsS3nsOnly(self):
        block = _render_block(_products(_product("cdn", "Cloud CDN", 0, 4, category="networking")))

        self.assertNotIn("Cloud CDN", _names(block, BOTH_NETWORKING))
        self.assertEqual(_line(block, S3NS_ONLY), f"{S3NS_ONLY} Cloud CDN.")

    def test_syncSkillMd_serviceWithoutPages_listedNowhere(self):
        block = _render_block(_products(_product("spanner", "Spanner", 0, 0)))

        self.assertNotIn("Spanner", block)

    def test_syncSkillMd_noOneRegionService_omitsRegionOnlyLines(self):
        block = _render_block(_products(_product("bigquery", "BigQuery", 1, 1)))

        self.assertNotIn(BERLIN_ONLY, block)
        self.assertNotIn(S3NS_ONLY, block)

    def test_syncSkillMd_oneRegionServices_sortedCaseInsensitively(self):
        block = _render_block(
            _products(_product("b", "bigtable", 0, 1), _product("a", "Artifact Registry", 0, 2))
        )

        self.assertEqual(_line(block, S3NS_ONLY), f"{S3NS_ONLY} Artifact Registry, bigtable.")


if __name__ == "__main__":
    unittest.main()
