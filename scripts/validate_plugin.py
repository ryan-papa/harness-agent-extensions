#!/usr/bin/env python3
"""Static validator for rp-plugins multi-provider repository (Claude Code + Antigravity)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from plugin_frontmatter import extract_relative_links, parse_frontmatter
except ImportError:
    try:
        from scripts.plugin_frontmatter import extract_relative_links, parse_frontmatter
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from plugin_frontmatter import extract_relative_links, parse_frontmatter

_JSON_LOAD_ERROR = object()

BODY_HARD_LIMIT_BYTES = 24_000
BODY_WARN_LIMIT_BYTES = 22_000
MAX_SKILL_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1_024
MAX_SUGGESTED_PROMPTS = 3

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG_VERSION_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
README_VERSION_RE = re.compile(r"현재 버전 `(\d+\.\d+\.\d+)`")

ANTIGRAVITY_ALLOWED_KEYS = frozenset({
    "$schema",
    "name",
    "displayName",
    "description",
    "version",
    "disabled",
    "logo",
    "suggestedPrompts",
    "skills",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
})
AUTHOR_ALLOWED_KEYS = frozenset({"name", "email", "url"})
FORBIDDEN_DISPLAY_PREFIXES = ("antigravity", "gemini", "claude", "cursor")
FORBIDDEN_DISPLAY_SUFFIXES = ("plugin", "plugins", "mcp")

LOCAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[^\s\"'`<>)]+")
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GitHub classic token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("API secret key", re.compile(r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{16,}\b")),
    ("age public recipient key", re.compile(r"\bage1[a-z0-9]{50,}\b")),
    ("age secret key", re.compile(r"\bAGE-SECRET-KEY-1[A-Z0-9]{50,}\b")),
)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skill_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read_utf8(path: Path, root: Path, result: ValidationResult) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result.errors.append(f"{_rel(path, root)}: unreadable UTF-8 text ({exc})")
        return None


def _load_json(
    path: Path,
    root: Path,
    result: ValidationResult,
    cache: dict[Path, Any] | None = None,
) -> Any:
    resolved = path.resolve()
    if cache is not None and resolved in cache:
        return cache[resolved]
    if not path.exists():
        result.errors.append(f"{_rel(path, root)}: file not found")
        if cache is not None:
            cache[resolved] = _JSON_LOAD_ERROR
        return _JSON_LOAD_ERROR
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result.errors.append(f"{_rel(path, root)}: invalid JSON ({exc})")
        parsed = _JSON_LOAD_ERROR
    if cache is not None:
        cache[resolved] = parsed
    return parsed


def validate_json_files(root: Path, result: ValidationResult) -> dict[Path, Any]:
    cache: dict[Path, Any] = {}
    for path in sorted(root.rglob("*.json")):
        rel_parts = path.relative_to(root).parts
        if "worktrees" in rel_parts or ".git" in rel_parts:
            continue
        _load_json(path, root, result, cache=cache)
    return cache


def _check_display_name(display_name: Any, rel_path: str, result: ValidationResult) -> None:
    if not isinstance(display_name, str) or not display_name.strip():
        result.errors.append(f"{rel_path}: 'displayName' must be a non-empty string")
        return
    tokens = re.findall(r"[A-Za-z0-9]+", display_name.lower())
    if not tokens:
        return
    for prefix in FORBIDDEN_DISPLAY_PREFIXES:
        if tokens[0].startswith(prefix):
            result.errors.append(f"{rel_path}: 'displayName' must not start with '{prefix}'")
            break
    for suffix in FORBIDDEN_DISPLAY_SUFFIXES:
        if tokens[-1].endswith(suffix):
            result.errors.append(f"{rel_path}: 'displayName' must not end with '{suffix}'")
            break


def _check_author(author: Any, rel_path: str, result: ValidationResult) -> None:
    if isinstance(author, str):
        if not author.strip():
            result.errors.append(f"{rel_path}: 'author' must not be empty")
        return
    if not isinstance(author, dict):
        result.errors.append(f"{rel_path}: 'author' must be a string or object")
        return
    extra = sorted(set(author.keys()) - AUTHOR_ALLOWED_KEYS)
    if extra:
        result.errors.append(f"{rel_path}: 'author' has disallowed keys: {', '.join(extra)}")
    if not isinstance(author.get("name"), str) or not author["name"].strip():
        result.errors.append(f"{rel_path}: 'author.name' must be a non-empty string")
    if "email" in author:
        email = author["email"]
        if not isinstance(email, str) or not email.strip():
            result.errors.append(f"{rel_path}: 'author.email' must be a non-empty string")
    url = author.get("url")
    if url is not None and (not isinstance(url, str) or not url.startswith("https://")):
        result.errors.append(f"{rel_path}: 'author.url' must start with https://")


def _check_manifest_optional_fields(
    data: dict[str, Any], rel_path: str, result: ValidationResult
) -> None:
    if "suggestedPrompts" in data:
        prompts = data["suggestedPrompts"]
        if not isinstance(prompts, list) or not (1 <= len(prompts) <= MAX_SUGGESTED_PROMPTS):
            result.errors.append(
                f"{rel_path}: 'suggestedPrompts' must be a list of 1..{MAX_SUGGESTED_PROMPTS} strings"
            )
        elif any(not isinstance(p, str) or not p.strip() for p in prompts):
            result.errors.append(
                f"{rel_path}: every entry in 'suggestedPrompts' must be a non-empty string"
            )
    for url_key in ("repository", "homepage"):
        if url_key in data:
            url = data[url_key]
            if not isinstance(url, str) or not url.startswith("https://"):
                result.errors.append(f"{rel_path}: '{url_key}' must be an https:// URL")
    if "author" in data:
        _check_author(data["author"], rel_path, result)
    if "keywords" in data:
        kws = data["keywords"]
        if not isinstance(kws, list) or any(not isinstance(k, str) or not k.strip() for k in kws):
            result.errors.append(f"{rel_path}: 'keywords' must be a list of non-empty strings")


def validate_antigravity_manifest(
    manifest_path: Path,
    root: Path,
    result: ValidationResult,
    cache: dict[Path, Any] | None = None,
) -> dict[str, Any] | None:
    data = _load_json(manifest_path, root, result, cache=cache)
    if data is _JSON_LOAD_ERROR:
        return None
    if not isinstance(data, dict):
        result.errors.append(f"{_rel(manifest_path, root)}: root must be a JSON object")
        return None

    rel_path = _rel(manifest_path, root)
    extra = sorted(set(data.keys()) - ANTIGRAVITY_ALLOWED_KEYS)
    if extra:
        result.errors.append(
            f"{rel_path}: disallowed keys (additionalProperties=false): {', '.join(extra)}"
        )
    name = data.get("name")
    if not isinstance(name, str) or not KEBAB_RE.match(name):
        result.errors.append(f"{rel_path}: 'name' must be lowercase kebab-case")
    if "displayName" in data:
        _check_display_name(data["displayName"], rel_path, result)
    for key in ("version", "description"):
        val = data.get(key)
        if not isinstance(val, str) or not val.strip():
            result.errors.append(f"{rel_path}: '{key}' must be a non-empty string")
    if isinstance(data.get("version"), str) and not SEMVER_RE.match(data["version"]):
        result.errors.append(f"{rel_path}: 'version' must match MAJOR.MINOR.PATCH")
    _check_manifest_optional_fields(data, rel_path, result)
    return data


def _extract_doc_version(
    path: Path,
    pattern: re.Pattern[str],
    missing_msg: str,
    root: Path,
    result: ValidationResult,
) -> str | None:
    if not path.exists():
        result.errors.append(f"{_rel(path, root)}: file not found")
        return None
    text = _read_utf8(path, root, result)
    if text is None:
        return None
    match = pattern.search(text)
    if not match:
        result.errors.append(f"{_rel(path, root)}: {missing_msg}")
        return None
    return match.group(1)


def validate_version_sync(
    root: Path,
    agy_manifest: dict[str, Any] | None,
    result: ValidationResult,
    cache: dict[Path, Any] | None = None,
) -> None:
    versions: dict[str, str] = {}

    claude_path = root / "rp-plugins" / ".claude-plugin" / "plugin.json"
    claude_data = _load_json(claude_path, root, result, cache=cache)
    if claude_data is not _JSON_LOAD_ERROR:
        if isinstance(claude_data, dict) and isinstance(claude_data.get("version"), str):
            versions[_rel(claude_path, root)] = claude_data["version"]
        else:
            result.errors.append(f"{_rel(claude_path, root)}: missing string 'version'")

    if agy_manifest and isinstance(agy_manifest.get("version"), str):
        versions["rp-plugins/.antigravity-plugin/plugin.json"] = agy_manifest["version"]

    cl_ver = _extract_doc_version(
        root / "CHANGELOG.md",
        CHANGELOG_VERSION_RE,
        "missing '## [X.Y.Z]' release heading",
        root,
        result,
    )
    if cl_ver:
        versions["CHANGELOG.md"] = cl_ver

    rm_ver = _extract_doc_version(
        root / "README.md",
        README_VERSION_RE,
        "missing '현재 버전 `X.Y.Z`' marker",
        root,
        result,
    )
    if rm_ver:
        versions["README.md"] = rm_ver

    if len(set(versions.values())) > 1:
        summary = ", ".join(f"{src}={ver}" for src, ver in versions.items())
        result.errors.append(f"version mismatch across 4 sources: {summary}")


def validate_markdown_links(
    md_path: Path, plugin_root: Path, root: Path, result: ValidationResult
) -> None:
    text = _read_utf8(md_path, root, result)
    if text is None:
        return
    resolved_plugin = plugin_root.resolve()
    rel_md = _rel(md_path, root)
    for target in extract_relative_links(text):
        resolved = (md_path.parent / target).resolve()
        if not resolved.is_relative_to(resolved_plugin):
            result.errors.append(
                f"{rel_md}: link '{target}' escapes plugin root '{_rel(plugin_root, root)}'"
            )
            continue
        if not resolved.exists():
            result.errors.append(f"{rel_md}: broken relative link '{target}'")


def _validate_single_skill(
    skill_dir: Path, plugin_root: Path, root: Path, result: ValidationResult
) -> None:
    skill_md = skill_dir / "SKILL.md"
    rel_skill = _rel(skill_md, root)
    if not skill_md.is_file():
        result.errors.append(f"{_rel(skill_dir, root)}: missing SKILL.md")
        return

    text = _read_utf8(skill_md, root, result)
    if text is None:
        return
    try:
        meta, body = parse_frontmatter(text)
    except ValueError as exc:
        result.errors.append(f"{rel_skill}: {exc}")
        return

    name = meta.get("name")
    if not isinstance(name, str) or not name:
        result.errors.append(f"{rel_skill}: missing 'name' in frontmatter")
    else:
        if not (1 <= len(name) <= MAX_SKILL_NAME_LEN) or not KEBAB_RE.match(name):
            result.errors.append(
                f"{rel_skill}: 'name' must be 1..{MAX_SKILL_NAME_LEN} char kebab-case"
            )
        if name != skill_dir.name:
            result.errors.append(
                f"{rel_skill}: frontmatter name '{name}' != directory '{skill_dir.name}'"
            )

    desc = meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        result.errors.append(f"{rel_skill}: missing non-empty 'description' in frontmatter")
    elif len(desc) > MAX_DESCRIPTION_LEN:
        result.errors.append(
            f"{rel_skill}: 'description' length {len(desc)} exceeds {MAX_DESCRIPTION_LEN} chars"
        )

    body_bytes = len(body.encode("utf-8"))
    if body_bytes > BODY_HARD_LIMIT_BYTES:
        result.errors.append(
            f"{rel_skill}: body is {body_bytes} bytes (limit: {BODY_HARD_LIMIT_BYTES} bytes)"
        )
    elif body_bytes > BODY_WARN_LIMIT_BYTES:
        result.warnings.append(
            f"{rel_skill}: body is {body_bytes} bytes (approaching {BODY_HARD_LIMIT_BYTES}-byte limit)"
        )

    validate_markdown_links(skill_md, plugin_root, root, result)
    ref_dir = skill_dir / "reference"
    if ref_dir.is_dir():
        for ref_md in sorted(ref_dir.rglob("*.md")):
            validate_markdown_links(ref_md, plugin_root, root, result)


def validate_skills(root: Path, result: ValidationResult) -> None:
    plugin_root = root / "rp-plugins"
    skills_dir = plugin_root / "skills"
    if not skills_dir.is_dir():
        result.errors.append("rp-plugins/skills: directory not found")
        return

    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not skill_dirs:
        result.errors.append("rp-plugins/skills: no skills found")
        return

    result.skill_count = len(skill_dirs)
    for skill_dir in skill_dirs:
        _validate_single_skill(skill_dir, plugin_root, root, result)


def _iter_public_artifacts(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel_dir in ("rp-plugins", ".claude-plugin"):
        base = root / rel_dir
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    files.append(path)
    for rel_file in ("README.md", "CHANGELOG.md"):
        path = root / rel_file
        if path.is_file():
            files.append(path)
    return files


def validate_public_artifacts_security(root: Path, result: ValidationResult) -> None:
    for path in _iter_public_artifacts(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel_path = _rel(path, root)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if LOCAL_PATH_RE.search(line):
                result.errors.append(
                    f"{rel_path}:{lineno}: local absolute path detected in public artifact"
                )
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    result.errors.append(
                        f"{rel_path}:{lineno}: potential secret ({label}) detected"
                    )


def validate_repo(repo_root: Path) -> ValidationResult:
    root = repo_root.resolve()
    result = ValidationResult()
    json_cache = validate_json_files(root, result)
    agy_path = root / "rp-plugins" / ".antigravity-plugin" / "plugin.json"
    agy_manifest = validate_antigravity_manifest(agy_path, root, result, cache=json_cache)
    validate_version_sync(root, agy_manifest, result, cache=json_cache)
    validate_skills(root, result)
    validate_public_artifacts_security(root, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root directory to validate (default: script parent)",
    )
    args = parser.parse_args(argv)
    result = validate_repo(args.repo_root)

    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    if not result.ok:
        for err in result.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    print(f"OK: validated {result.skill_count} skills (warnings: {len(result.warnings)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
