"""The committed scrape data must still drive product discovery.

This is the smoke test the daily workflow runs inline before scraping, kept here so that
pull requests run it too.
"""

import json
import unittest
from pathlib import Path

from tests.helpers import load_script

scraper = load_script("scrape-gcd-docs")

STATUS_FILE = Path(__file__).resolve().parent.parent / "docs-raw-s3ns" / "_secnumcloud_status.json"
MIN_PRODUCTS = 20
MIN_PROBES = 10


class CommittedDataTests(unittest.TestCase):
    def test_discover_products_from_committed_status_finds_products_and_probes(self):
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        products, probes = scraper.discover_products_from_secnumcloud(data)
        self.assertGreater(len(products), MIN_PRODUCTS)
        self.assertGreater(len(probes), MIN_PROBES)


if __name__ == "__main__":
    unittest.main()
