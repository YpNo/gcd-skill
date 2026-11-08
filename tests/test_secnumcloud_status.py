"""The PREMI3NS status parser must never invent a SecNumCloud qualification."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import load_script

scraper = load_script("scrape-gcd-docs")

CARD_COUNT = 20
IN_PROGRESS_EVERY = 4


def _card(i: int, badge_class: str) -> str:
    badge = ""
    if i % IN_PROGRESS_EVERY == 0:
        badge = f'<div class="{badge_class}"><span>Qualification en cours</span></div>'
    return (
        '<div class="relative flex flex-col items-center rounded-[10px] p-4">'
        f'{badge}<a href="https://example.test/s{i}"><h3>Service {i}</h3>'
        f"<p>Description {i}</p></a></div>"
    )


def _page(badge_class: str = "absolute right-3 z-10 top-3") -> str:
    cards = "".join(_card(i, badge_class) for i in range(CARD_COUNT))
    return f"<html><body><h2>Liste des services</h2>{cards}</body></html>"


def _response(body: str) -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__.return_value = resp
    return resp


class ClassifyBadgeTests(unittest.TestCase):
    def test_classify_with_empty_badge_returns_qualified(self):
        self.assertEqual(scraper._classify_secnumcloud_badge("")[0], "qualified")

    def test_classify_with_in_progress_badge_returns_in_progress(self):
        self.assertEqual(
            scraper._classify_secnumcloud_badge("Qualification en cours")[0], "in_progress"
        )

    def test_classify_with_upcoming_badge_returns_upcoming(self):
        self.assertEqual(scraper._classify_secnumcloud_badge("À venir")[0], "upcoming")

    def test_classify_with_non_qualifie_badge_returns_other(self):
        self.assertEqual(
            scraper._classify_secnumcloud_badge("Non qualifié"), ("other", "Non qualifié")
        )

    def test_classify_with_unknown_badge_returns_other(self):
        self.assertEqual(scraper._classify_secnumcloud_badge("Bêta")[0], "other")


class BadgeMarkupDriftTests(unittest.TestCase):
    def test_drift_with_parsed_in_progress_badge_returns_false(self):
        services = [{"status": "qualified"}, {"status": "in_progress"}]
        self.assertFalse(scraper.badge_markup_drifted(services, "Qualification en cours"))

    def test_drift_with_labels_on_page_but_none_parsed_returns_true(self):
        services = [{"status": "qualified"}, {"status": "qualified"}]
        self.assertTrue(scraper.badge_markup_drifted(services, "<span>À venir</span>"))

    def test_drift_with_no_labels_on_page_returns_false(self):
        self.assertFalse(scraper.badge_markup_drifted([{"status": "qualified"}], "<p>ok</p>"))


class ScrapeStatusTests(unittest.TestCase):
    def _scrape(self, page: str, previous: dict | None) -> tuple[dict | None, dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            status = out / "_secnumcloud_status.json"
            if previous is not None:
                status.write_text(json.dumps(previous), encoding="utf-8")
            with mock.patch.object(
                scraper.urllib.request, "urlopen", return_value=_response(page)
            ):
                result = scraper.scrape_s3ns_secnumcloud_status(out)
            saved = json.loads(status.read_text(encoding="utf-8")) if status.exists() else None
        return result, saved

    def test_scrape_with_current_markup_saves_statuses(self):
        result, saved = self._scrape(_page(), previous=None)
        in_progress = CARD_COUNT // IN_PROGRESS_EVERY
        self.assertEqual(result["summary"]["in_progress"], in_progress)
        self.assertEqual(saved["summary"]["qualified"], CARD_COUNT - in_progress)

    def test_scrape_with_changed_badge_markup_preserves_previous_file(self):
        previous = {"summary": {"qualified": 1}, "services": [], "marker": "previous"}
        result, saved = self._scrape(_page(badge_class="badge-v2"), previous=previous)
        self.assertEqual(saved, previous)
        self.assertEqual(result, previous)


if __name__ == "__main__":
    unittest.main()
