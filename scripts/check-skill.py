#!/usr/bin/env python3
"""Check the integrity of the skill an agent loads: metadata, links, sync markers, hidden text.

``sync-skill.py --check`` proves the generated blocks match the scraped docs. This script
covers what that check cannot see:

- SKILL.md frontmatter that an agent would reject (name and description rules).
- SKILL.md growing past the size budget. It is loaded in full on every activation.
- Broken relative links, and reference files that SKILL.md never points to.
- AUTO-SYNC markers that are unbalanced, duplicated, or missing. ``replace_marker_block``
  silently skips a missing marker, so that section would stop updating with no error.
- Invisible Unicode and HTML comments: text an agent reads but a reviewer does not see.

Usage (from anywhere):
    python3 scripts/check-skill.py [--root PATH]

Exit status: 0 when no errors were found (warnings are allowed), 1 otherwise.
Inside GitHub Actions, findings are printed as workflow annotations.
"""

import argparse
import ast
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILE = "SKILL.md"
README_FILE = "README.md"
REFERENCES_DIR = "references"
PLUGIN_FILE = ".claude-plugin/plugin.json"
SYNC_SCRIPT = "scripts/sync-skill.py"
SYNC_MARKER_FUNCTION = "replace_marker_block"

ERROR = "error"
WARNING = "warning"

# Agent Skills limits: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
RESERVED_NAME_WORDS = ("anthropic", "claude")
# Agent Skills best practice: keep the SKILL.md body under 500 lines.
MAX_SKILL_LINES = 500

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
XML_TAG_RE = re.compile(r"</?[A-Za-z][\w:-]*(?:\s[^<>]*)?/?>")
FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
BLOCK_SCALAR_RE = re.compile(r"^[>|][+-]?$")
LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
MARKER_RE = re.compile(r"<!-- (AUTO-SYNC|AUTO-GENERATED-PRODUCT):(\S+?):(START|END) -->")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[^\n]*$", re.S | re.M)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
# Invisible characters that can reorder or smuggle text: bidi controls and tag characters.
# Other format characters (zero-width space, joiner, BOM, soft hyphen) are common artifacts
# in scraped pages and emoji sequences, so they are reported as warnings.
DANGEROUS_FORMAT_CHARS = frozenset(
    [0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)]
)
TAG_CHARS = range(0xE0000, 0xE0080)


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    line: int
    message: str


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _blank_out(match: re.Match) -> str:
    """Replace a match with spaces, keeping newlines so line numbers stay correct."""
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_code(text: str) -> str:
    return INLINE_CODE_RE.sub(_blank_out, FENCE_RE.sub(_blank_out, text))


# --- Frontmatter -------------------------------------------------------------------------


def _split_frontmatter(text: str):
    """Return (frontmatter lines, error). Only the leading ``---`` block counts."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "SKILL.md must start with a '---' YAML frontmatter block"
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:index], None
    return None, "frontmatter has no closing '---'"


def _read_block(lines: list, start: int) -> tuple:
    """Collect the indented lines that follow a key; return (dedented lines, next index)."""
    block = []
    index = start
    while index < len(lines) and (not lines[index].strip() or lines[index][:1] in " \t"):
        block.append(lines[index].strip())
        index += 1
    while block and not block[-1]:
        block.pop()
    return block, index


def _fold(block: list) -> str:
    """YAML folded scalar: single newlines become spaces, blank lines become newlines."""
    paragraphs, current = [], []
    for line in block:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n".join(paragraphs)


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def parse_frontmatter(text: str) -> tuple:
    """Parse the top-level keys of a SKILL.md frontmatter.

    Supports plain and quoted scalars, folded (``>``) and literal (``|``) block scalars, and
    nested mappings (kept as raw text). Returns (dict, error message or None).
    """
    lines, error = _split_frontmatter(text)
    if error:
        return {}, error
    meta, index = {}, 0
    while index < len(lines):
        match = FRONTMATTER_KEY_RE.match(lines[index])
        if not match:
            if lines[index].strip() and not lines[index].lstrip().startswith("#"):
                return meta, f"unparseable frontmatter line: {lines[index]!r}"
            index += 1
            continue
        key, value = match.group(1), match.group(2).strip()
        block, index = _read_block(lines, index + 1)
        if BLOCK_SCALAR_RE.match(value):
            meta[key] = "\n".join(block) if value[0] == "|" else _fold(block)
        else:
            meta[key] = _scalar(value) if value else "\n".join(block)
    return meta, None


def _name_errors(name: str) -> list:
    errors = []
    if not NAME_RE.match(name) or len(name) > MAX_NAME_LEN:
        errors.append(
            f"name {name!r} must be 1-{MAX_NAME_LEN} lowercase letters, digits and single hyphens"
        )
    reserved = [word for word in RESERVED_NAME_WORDS if word in name]
    if reserved:
        errors.append(f"name {name!r} contains the reserved word {reserved[0]!r}")
    return errors


def _description_errors(description: str) -> list:
    if not description.strip():
        return ["description is missing or empty: agents use it to decide when to load the skill"]
    errors = []
    if len(description) > MAX_DESCRIPTION_LEN:
        errors.append(
            f"description is {len(description)} characters; the limit is {MAX_DESCRIPTION_LEN}"
        )
    if XML_TAG_RE.search(description):
        errors.append("description must not contain XML tags")
    return errors


def check_frontmatter(path: str, text: str) -> list:
    """Validate the name and description an agent reads before loading the skill."""
    meta, error = parse_frontmatter(text)
    if error:
        return [Finding(ERROR, path, 1, error)]
    messages = _name_errors(meta.get("name", "")) + _description_errors(meta.get("description", ""))
    return [Finding(ERROR, path, 1, message) for message in messages]


def check_skill_size(path: str, text: str) -> list:
    lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    if lines <= MAX_SKILL_LINES:
        return []
    return [
        Finding(
            ERROR,
            path,
            MAX_SKILL_LINES + 1,
            f"SKILL.md has {lines} lines; the budget is {MAX_SKILL_LINES}. It is loaded in full "
            "on every activation, so move detail into references/",
        )
    ]


# --- Links -------------------------------------------------------------------------------


def _link_finding(root: Path, path: str, target: str, line: int):
    if target.startswith("/"):
        return Finding(
            WARNING,
            path,
            line,
            f"root-relative link {target!r} resolves against github.com, not the docs site",
        )
    local = unquote(re.split(r"[?#]", target, maxsplit=1)[0])
    resolved = ((root / path).parent / local).resolve()
    if not resolved.is_relative_to(root.resolve()):
        return Finding(ERROR, path, line, f"link {target!r} points outside the repository")
    if not resolved.exists():
        return Finding(ERROR, path, line, f"link target {target!r} does not exist")
    return None


def check_links(root: Path, path: str, text: str) -> list:
    """Report relative links that do not resolve to a file in the repository."""
    findings = []
    for match in LINK_RE.finditer(_strip_code(text)):
        target = match.group(1)
        if target.startswith("#") or SCHEME_RE.match(target):
            continue
        finding = _link_finding(root, path, target, _line_of(text, match.start()))
        if finding:
            findings.append(finding)
    return findings


def check_reference_reachability(root: Path, skill_text: str) -> list:
    """Every reference file must be linked from SKILL.md, or no agent will ever load it."""
    linked = {
        (root / unquote(re.split(r"[?#]", match.group(1), maxsplit=1)[0])).resolve()
        for match in LINK_RE.finditer(_strip_code(skill_text))
    }
    orphans = [
        ref.relative_to(root).as_posix()
        for ref in sorted((root / REFERENCES_DIR).glob("*.md"))
        if ref.resolve() not in linked
    ]
    return [Finding(ERROR, rel, 1, f"{rel} is not linked from SKILL.md") for rel in orphans]


# --- AUTO-SYNC markers -------------------------------------------------------------------


def _marker_event(path: str, text: str, match: re.Match, open_stack: list, seen: set):
    """Apply one marker to the open-block stack; return a Finding when it is out of place."""
    key, edge, line = (
        f"{match.group(1)}:{match.group(2)}",
        match.group(3),
        _line_of(text, match.start()),
    )
    if edge == "START":
        if key in seen:
            return Finding(
                ERROR,
                path,
                line,
                f"block {key} appears more than once; sync updates only the first",
            )
        seen.add(key)
        open_stack.append((key, line))
        return None
    if not open_stack or open_stack[-1][0] != key:
        expected = open_stack[-1][0] if open_stack else "no open block"
        return Finding(
            ERROR, path, line, f"END of {key} does not match the open block ({expected})"
        )
    open_stack.pop()
    return None


def check_markers(path: str, text: str) -> list:
    """Markers must pair up, nest properly and appear once, or sync rewrites the wrong text."""
    findings, open_stack, seen = [], [], set()
    for match in MARKER_RE.finditer(text):
        finding = _marker_event(path, text, match, open_stack, seen)
        if finding:
            findings.append(finding)
    findings.extend(
        Finding(ERROR, path, line, f"block {key} is never closed") for key, line in open_stack
    )
    return findings


def expected_marker_names(sync_source: str) -> set:
    """Marker names that sync-skill.py writes with a literal name (f-string names are skipped)."""
    names = set()
    for node in ast.walk(ast.parse(sync_source)):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == SYNC_MARKER_FUNCTION
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            names.add(node.args[1].value)
    return names


def check_expected_markers(root: Path, texts: dict) -> list:
    sync_path = root / SYNC_SCRIPT
    if not sync_path.exists():
        return []
    present = {m.group(2) for text in texts.values() for m in MARKER_RE.finditer(text)}
    return [
        Finding(
            ERROR,
            SYNC_SCRIPT,
            1,
            f"sync writes block {name} but no file has its markers; "
            "the section would silently stop updating",
        )
        for name in sorted(expected_marker_names(sync_path.read_text(encoding="utf-8")) - present)
    ]


# --- Hidden text -------------------------------------------------------------------------


def _format_char_level(char: str) -> str:
    code = ord(char)
    return ERROR if code in DANGEROUS_FORMAT_CHARS or code in TAG_CHARS else WARNING


def check_hidden_text(path: str, text: str, forbid_comments: bool) -> list:
    """Report invisible format characters, and HTML comments other than sync markers."""
    findings = [
        Finding(
            _format_char_level(char),
            path,
            _line_of(text, offset),
            f"invisible character U+{ord(char):04X} ({unicodedata.name(char, 'unnamed')})",
        )
        for offset, char in enumerate(text)
        if unicodedata.category(char) == "Cf"
    ]
    if forbid_comments:
        findings.extend(
            Finding(
                ERROR,
                path,
                _line_of(text, match.start()),
                "HTML comment: an agent reads it but the rendered page hides it",
            )
            for match in COMMENT_RE.finditer(_strip_code(text))
            if not MARKER_RE.fullmatch(match.group(0))
        )
    return findings


# --- Plugin manifest ---------------------------------------------------------------------


def _plugin_field_errors(manifest: dict, root: Path) -> list:
    errors = [
        f"plugin.json needs a non-empty {key!r}"
        for key in ("name", "description")
        if not isinstance(manifest.get(key), str) or not manifest[key].strip()
    ]
    if not SEMVER_RE.match(str(manifest.get("version", ""))):
        errors.append(f"plugin.json version {manifest.get('version')!r} is not semantic versioning")
    skills = manifest.get("skills", [])
    for skill_dir in [skills] if isinstance(skills, str) else skills:
        if not (root / skill_dir / SKILL_FILE).is_file():
            errors.append(f"plugin.json skill path {skill_dir!r} has no {SKILL_FILE}")
    return errors


def check_plugin(root: Path) -> list:
    path = root / PLUGIN_FILE
    if not path.exists():
        return []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            Finding(ERROR, PLUGIN_FILE, exc.lineno, f"plugin.json is not valid JSON: {exc.msg}")
        ]
    if not isinstance(manifest, dict):
        return [Finding(ERROR, PLUGIN_FILE, 1, "plugin.json must be a JSON object")]
    return [
        Finding(ERROR, PLUGIN_FILE, 1, message) for message in _plugin_field_errors(manifest, root)
    ]


# --- Driver ------------------------------------------------------------------------------


def _content_files(root: Path) -> dict:
    """Return {repo-relative path: text} for the files an agent or a reader loads."""
    paths = [root / SKILL_FILE, root / README_FILE, *sorted((root / REFERENCES_DIR).glob("*.md"))]
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in paths if p.is_file()
    }


def run_checks(root: Path) -> list:
    """Run every check against the repository at ``root``."""
    texts = _content_files(root)
    skill = texts.get(SKILL_FILE)
    if skill is None:
        return [Finding(ERROR, SKILL_FILE, 1, "SKILL.md is missing")]
    findings = check_frontmatter(SKILL_FILE, skill) + check_skill_size(SKILL_FILE, skill)
    findings += check_reference_reachability(root, skill) + check_plugin(root)
    findings += check_expected_markers(root, texts)
    for path, text in texts.items():
        findings += check_links(root, path, text) + check_markers(path, text)
        findings += check_hidden_text(path, text, forbid_comments=path != README_FILE)
    return findings


def format_finding(finding: Finding, github: bool) -> str:
    if github:
        return f"::{finding.level} file={finding.path},line={finding.line}::{finding.message}"
    return f"{finding.path}:{finding.line}: {finding.level}: {finding.message}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args(argv)
    findings = run_checks(args.root)
    github = os.environ.get("GITHUB_ACTIONS") == "true"
    for finding in findings:
        print(format_finding(finding, github))
    errors = sum(1 for f in findings if f.level == ERROR)
    print(f"check-skill: {errors} error(s), {len(findings) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
