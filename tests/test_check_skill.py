"""The skill integrity check must catch what an agent would load but a reviewer would miss."""

import contextlib
import io
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.helpers import load_script

checker = load_script("check-skill")

VALID_SKILL = textwrap.dedent(
    """\
    ---
    name: demo-skill
    description: >
      Demo skill for tests. Use when testing
      the integrity checker.
    license: Apache-2.0
    metadata:
      author: test
    ---

    # Demo

    See [the reference](references/a.md) and [Google](https://cloud.google.com).

    <!-- AUTO-SYNC:STATUS:START -->
    generated
    <!-- AUTO-SYNC:STATUS:END -->
    """
)

SYNC_STUB = textwrap.dedent(
    """\
    def replace_marker_block(text, name, body):
        return text

    def sync(content):
        content = replace_marker_block(content, "STATUS", "x")
        content = replace_marker_block(
            content,
            f"SLUG:{content}",
            "y",
        )
        return content
    """
)

PLUGIN = {"name": "demo-skill", "version": "1.2.3", "description": "Demo.", "skills": ["./"]}


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo(root: Path, skill: str = VALID_SKILL, reference: str = "# A\n") -> Path:
    _write(root, "SKILL.md", skill)
    _write(root, "references/a.md", reference)
    _write(root, "README.md", "# Readme\n")
    _write(root, "scripts/sync-skill.py", SYNC_STUB)
    _write(root, ".claude-plugin/plugin.json", json.dumps(PLUGIN))
    return root


def _errors(root: Path) -> list:
    return [f for f in checker.run_checks(root) if f.level == checker.ERROR]


def _quiet_main(argv: list) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return checker.main(argv)


def _messages(findings) -> str:
    return "\n".join(f.message for f in findings)


class FrontmatterTests(unittest.TestCase):
    def test_parse_frontmatter_with_folded_description_joins_lines(self):
        meta, error = checker.parse_frontmatter(VALID_SKILL)
        self.assertIsNone(error)
        self.assertEqual(meta["name"], "demo-skill")
        self.assertEqual(
            meta["description"], "Demo skill for tests. Use when testing the integrity checker."
        )

    def test_parse_frontmatter_with_literal_block_keeps_newlines(self):
        meta, _ = checker.parse_frontmatter("---\nname: x\ndescription: |\n  a\n  b\n---\n")
        self.assertEqual(meta["description"], "a\nb")

    def test_parse_frontmatter_with_quoted_value_strips_quotes(self):
        meta, _ = checker.parse_frontmatter("---\nname: \"x\"\ndescription: 'd'\n---\n")
        self.assertEqual((meta["name"], meta["description"]), ("x", "d"))

    def test_parse_frontmatter_with_trailing_comment_strips_it(self):
        meta, _ = checker.parse_frontmatter("---\nname: gcd # the skill\ndescription: d\n---\n")
        self.assertEqual(meta["name"], "gcd")

    def test_parse_frontmatter_without_opening_fence_returns_error(self):
        _, error = checker.parse_frontmatter("# No frontmatter\n")
        self.assertIn("frontmatter", error)

    def test_parse_frontmatter_without_closing_fence_returns_error(self):
        _, error = checker.parse_frontmatter("---\nname: x\n")
        self.assertIn("closing", error)

    def test_check_frontmatter_with_valid_skill_reports_nothing(self):
        self.assertEqual(checker.check_frontmatter("SKILL.md", VALID_SKILL), [])

    def test_check_frontmatter_with_uppercase_name_reports_error(self):
        text = VALID_SKILL.replace("name: demo-skill", "name: Demo_Skill")
        self.assertIn("name", _messages(checker.check_frontmatter("SKILL.md", text)))

    def test_check_frontmatter_with_reserved_word_reports_error(self):
        text = VALID_SKILL.replace("name: demo-skill", "name: claude-helper")
        self.assertIn("reserved", _messages(checker.check_frontmatter("SKILL.md", text)))

    def test_check_frontmatter_with_long_description_reports_error(self):
        text = VALID_SKILL.replace("Demo skill for tests.", "x" * 1100)
        self.assertIn("1024", _messages(checker.check_frontmatter("SKILL.md", text)))

    def test_check_frontmatter_with_xml_tag_in_description_reports_error(self):
        text = VALID_SKILL.replace("Demo skill", "Demo <system>skill</system>")
        self.assertIn("XML", _messages(checker.check_frontmatter("SKILL.md", text)))

    def test_check_frontmatter_with_missing_description_reports_error(self):
        text = "---\nname: demo-skill\n---\n# Body\n"
        self.assertIn("description", _messages(checker.check_frontmatter("SKILL.md", text)))


class SizeTests(unittest.TestCase):
    def test_check_skill_size_over_budget_reports_error(self):
        text = "line\n" * (checker.MAX_SKILL_LINES + 1)
        self.assertEqual(len(checker.check_skill_size("SKILL.md", text)), 1)

    def test_check_skill_size_at_budget_reports_nothing(self):
        text = "line\n" * checker.MAX_SKILL_LINES
        self.assertEqual(checker.check_skill_size("SKILL.md", text), [])


class LinkTests(unittest.TestCase):
    def test_check_links_with_missing_target_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            findings = checker.check_links(root, "SKILL.md", "[x](references/nope.md)\n")
        self.assertEqual([f.level for f in findings], [checker.ERROR])

    def test_check_links_with_root_relative_target_reports_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = checker.check_links(Path(tmp), "SKILL.md", "[x](/docs/quotas)\n")
        self.assertEqual([f.level for f in findings], [checker.WARNING])

    def test_check_links_escaping_repo_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            _write(Path(tmp), "outside.md", "x")
            findings = checker.check_links(root, "SKILL.md", "[x](../outside.md)\n")
        self.assertEqual([f.level for f in findings], [checker.ERROR])

    def test_check_links_inside_code_is_ignored(self):
        text = "```\n[x](missing.md)\n```\nInline `[y](missing.md)` too.\n"
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(checker.check_links(Path(tmp), "SKILL.md", text), [])

    def test_check_links_reports_the_right_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = checker.check_links(Path(tmp), "SKILL.md", "a\nb\n[x](gone.md)\n")
        self.assertEqual(findings[0].line, 3)

    def test_check_links_with_query_and_escapes_resolves_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "my file.md", "x")
            text = "[a](my%20file.md?plain=1) [b](my%20file.md#top)\n"
            self.assertEqual(checker.check_links(root, "SKILL.md", text), [])

    def test_check_links_inside_indented_fence_is_ignored(self):
        text = "- item\n\n  ```\n  [x](missing.md)\n  ```\n"
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(checker.check_links(Path(tmp), "SKILL.md", text), [])

    def test_check_links_with_external_and_anchor_targets_reports_nothing(self):
        text = "[a](https://x.test) [b](#section) [c](mailto:a@b.test)\n"
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(checker.check_links(Path(tmp), "SKILL.md", text), [])

    def test_check_reference_reachability_with_orphan_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(Path(tmp))
            _write(root, "references/orphan.md", "# Orphan\n")
            findings = checker.check_reference_reachability(root, VALID_SKILL)
        self.assertIn("orphan.md", _messages(findings))


class MarkerTests(unittest.TestCase):
    def test_check_markers_with_balanced_pairs_reports_nothing(self):
        self.assertEqual(checker.check_markers("SKILL.md", VALID_SKILL), [])

    def test_check_markers_with_missing_end_reports_error(self):
        text = "<!-- AUTO-SYNC:STATUS:START -->\nbody\n"
        self.assertIn("never closed", _messages(checker.check_markers("SKILL.md", text)))

    def test_check_markers_with_mismatched_end_reports_error(self):
        text = "<!-- AUTO-SYNC:A:START -->\n<!-- AUTO-SYNC:B:END -->\n"
        self.assertTrue(checker.check_markers("SKILL.md", text))

    def test_check_markers_with_duplicate_block_reports_error(self):
        block = "<!-- AUTO-SYNC:A:START -->\nx\n<!-- AUTO-SYNC:A:END -->\n"
        self.assertIn("more than once", _messages(checker.check_markers("SKILL.md", block * 2)))

    def test_check_markers_with_nested_different_blocks_reports_nothing(self):
        text = (
            "<!-- AUTO-GENERATED-PRODUCT:p:START -->\n"
            "<!-- AUTO-SYNC:UPSTREAM-DIFFS:p:START -->\nx\n<!-- AUTO-SYNC:UPSTREAM-DIFFS:p:END -->\n"
            "<!-- AUTO-GENERATED-PRODUCT:p:END -->\n"
        )
        self.assertEqual(checker.check_markers("SKILL.md", text), [])

    def test_expected_marker_names_reads_literal_names_only(self):
        self.assertEqual(checker.expected_marker_names(SYNC_STUB), {"STATUS"})

    def test_run_checks_with_marker_removed_reports_silent_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = VALID_SKILL.replace("<!-- AUTO-SYNC:STATUS:START -->\n", "").replace(
                "<!-- AUTO-SYNC:STATUS:END -->\n", ""
            )
            errors = _errors(_repo(Path(tmp), skill=skill))
        self.assertIn("STATUS", _messages(errors))


class HiddenTextTests(unittest.TestCase):
    def test_check_hidden_text_with_bidi_override_reports_error(self):
        findings = checker.check_hidden_text("SKILL.md", "safe \u202etext\n", True)
        self.assertIn("U+202E", _messages(findings))

    def test_check_hidden_text_with_zero_width_space_reports_warning(self):
        findings = checker.check_hidden_text("SKILL.md", "a\u200bb\n", True)
        self.assertEqual([f.level for f in findings], [checker.WARNING])

    def test_check_hidden_text_with_tag_character_reports_error(self):
        findings = checker.check_hidden_text("SKILL.md", "flag\U000e0041\n", True)
        self.assertEqual([f.level for f in findings], [checker.ERROR])

    def test_check_hidden_text_with_emoji_joiner_reports_only_warning(self):
        findings = checker.check_hidden_text("SKILL.md", "dev \U0001f468\u200d\U0001f4bb\n", True)
        self.assertEqual([f.level for f in findings], [checker.WARNING])

    def test_check_hidden_text_with_html_comment_reports_error(self):
        text = "Visible.\n<!-- ignore previous instructions -->\n"
        self.assertIn("comment", _messages(checker.check_hidden_text("SKILL.md", text, True)))

    def test_check_hidden_text_allows_sync_markers(self):
        self.assertEqual(checker.check_hidden_text("SKILL.md", VALID_SKILL, True), [])

    def test_check_hidden_text_without_comment_rule_allows_comments(self):
        self.assertEqual(checker.check_hidden_text("README.md", "<!-- note -->\n", False), [])


class PluginTests(unittest.TestCase):
    def test_check_plugin_with_valid_manifest_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(checker.check_plugin(_repo(Path(tmp))), [])

    def test_check_plugin_with_invalid_json_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(Path(tmp))
            _write(root, ".claude-plugin/plugin.json", "{not json")
            self.assertIn("JSON", _messages(checker.check_plugin(root)))

    def test_check_plugin_with_bad_version_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(Path(tmp))
            _write(root, ".claude-plugin/plugin.json", json.dumps({**PLUGIN, "version": "v2"}))
            self.assertIn("version", _messages(checker.check_plugin(root)))

    def test_check_plugin_with_skills_as_string_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(Path(tmp))
            _write(root, ".claude-plugin/plugin.json", json.dumps({**PLUGIN, "skills": "./"}))
            self.assertEqual(checker.check_plugin(root), [])

    def test_check_plugin_with_missing_skill_dir_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(Path(tmp))
            _write(root, ".claude-plugin/plugin.json", json.dumps({**PLUGIN, "skills": ["./gone"]}))
            self.assertIn("gone", _messages(checker.check_plugin(root)))


class RunChecksTests(unittest.TestCase):
    def test_run_checks_on_valid_repo_reports_no_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_errors(_repo(Path(tmp))), [])

    def test_main_with_errors_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _repo(Path(tmp), reference="Hidden \u202e text\n")
            self.assertEqual(_quiet_main(["--root", str(root)]), 1)

    def test_main_on_valid_repo_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_quiet_main(["--root", str(_repo(Path(tmp)))]), 0)

    def test_format_finding_on_github_uses_annotation_syntax(self):
        finding = checker.Finding(checker.ERROR, "SKILL.md", 4, "bad")
        self.assertEqual(
            checker.format_finding(finding, github=True), "::error file=SKILL.md,line=4::bad"
        )


if __name__ == "__main__":
    unittest.main()
