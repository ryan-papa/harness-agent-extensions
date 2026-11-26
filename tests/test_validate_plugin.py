"""Unit tests for scripts/validate_plugin.py."""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_plugin as vp  # noqa: E402


def _make_valid_repo(root: Path, version: str = "0.35.0") -> None:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "harness-agent-extensions", "plugins": [{"name": "rp-plugins"}]}, indent=2),
        encoding="utf-8",
    )
    (root / "rp-plugins" / ".claude-plugin").mkdir(parents=True)
    (root / "rp-plugins" / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "rp-plugins", "version": version, "description": "desc"}, indent=2),
        encoding="utf-8",
    )
    (root / "rp-plugins" / ".antigravity-plugin").mkdir(parents=True)
    (root / "rp-plugins" / ".antigravity-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://antigravity.google/schemas/v1/plugin.json",
                "name": "rp-plugins",
                "displayName": "RP Harness Extensions",
                "version": version,
                "description": "Multi-runtime harness extension skills.",
                "suggestedPrompts": ["Run deck", "Run post"],
                "author": {"name": "Rapa-Space"},
                "repository": "https://github.com/ryan-papa/harness-agent-extensions",
                "keywords": ["harness", "skills"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{version}] - 2026-11-26\n\n### Added\n- Initial\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# harness-agent-extensions\n\n현재 버전 `{version}` ([CHANGELOG](CHANGELOG.md)).\n",
        encoding="utf-8",
    )
    skill_dir = root / "rp-plugins" / "skills" / "rp-demo"
    (skill_dir / "reference").mkdir(parents=True)
    (skill_dir / "reference" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: rp-demo\n"
        "description: |\n"
        "  멀티라인 블록 스칼라 설명.\n"
        "  두 번째 줄 설명.\n"
        "allowed-tools:\n"
        "  - Bash\n"
        "  - Read\n"
        "---\n\n"
        "# rp-demo\n\n"
        "참고: [가이드](reference/guide.md#section)\n",
        encoding="utf-8",
    )


class ValidatePluginTest(unittest.TestCase):
    def test_valid_fixture_passes_fast(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            started = time.monotonic()
            res = vp.validate_repo(root)
            elapsed = time.monotonic() - started
            self.assertTrue(res.ok, res.errors)
            self.assertEqual(res.warnings, [])
            self.assertEqual(res.skill_count, 1)
            self.assertLess(elapsed, 2.0)

    def test_empty_skills_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            skill_dir = root / "rp-plugins" / "skills" / "rp-demo"
            for child in sorted(skill_dir.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                else:
                    child.rmdir()
            skill_dir.rmdir()
            res = vp.validate_repo(root)
            self.assertFalse(res.ok)
            self.assertTrue(any("no skills found" in e for e in res.errors), res.errors)

    def test_invalid_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            (root / ".claude-plugin" / "marketplace.json").write_text("{broken", encoding="utf-8")
            res = vp.validate_repo(root)
            self.assertFalse(res.ok)
            self.assertTrue(any("invalid JSON" in e for e in res.errors), res.errors)

    def test_antigravity_manifest_schema_rules(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            path = root / "rp-plugins" / ".antigravity-plugin" / "plugin.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["unknownExtraKey"] = True
            data["displayName"] = "Antigravity RP Plugins"
            data["suggestedPrompts"] = ["a", "b", "c", "d"]
            data["repository"] = "http://insecure.example.com/repo"
            data["author"] = {"name": "Org", "extraField": "bad"}
            path.write_text(json.dumps(data), encoding="utf-8")

            res = vp.validate_repo(root)
            self.assertFalse(res.ok)
            joined = "\n".join(res.errors)
            self.assertIn("additionalProperties=false", joined)
            self.assertIn("must not start with 'antigravity'", joined)
            self.assertIn("must not end with 'plugins'", joined)
            self.assertIn("suggestedPrompts", joined)
            self.assertIn("'repository' must be an https:// URL", joined)
            self.assertIn("'author' has disallowed keys", joined)

    def test_four_way_version_mismatch_detected(self) -> None:
        for target_file in (
            "rp-plugins/.claude-plugin/plugin.json",
            "rp-plugins/.antigravity-plugin/plugin.json",
            "CHANGELOG.md",
            "README.md",
        ):
            with self.subTest(target=target_file), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                _make_valid_repo(root, version="0.35.0")
                p = root / target_file
                p.write_text(p.read_text(encoding="utf-8").replace("0.35.0", "0.34.0"), encoding="utf-8")
                res = vp.validate_repo(root)
                self.assertFalse(res.ok)
                self.assertTrue(any("version mismatch" in e for e in res.errors), res.errors)

    def test_multiline_frontmatter_and_name_validation(self) -> None:
        text = (
            "---\n"
            "name: sample-skill\n"
            "description: >-\n"
            "  First line\n"
            "  second line\n"
            "---\n\n"
            "Body\n"
        )
        meta, body = vp.parse_frontmatter(text)
        self.assertEqual(meta["name"], "sample-skill")
        self.assertEqual(meta["description"], "First line second line")
        self.assertEqual(body, "Body\n")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            skill_md = root / "rp-plugins" / "skills" / "rp-demo" / "SKILL.md"
            skill_md.write_text(
                "---\nname: wrong-name\ndescription: |\n\n---\n\n# Body\n",
                encoding="utf-8",
            )
            res = vp.validate_repo(root)
            self.assertFalse(res.ok)
            joined = "\n".join(res.errors)
            self.assertIn("frontmatter name 'wrong-name' != directory 'rp-demo'", joined)
            self.assertIn("missing non-empty 'description'", joined)

    def test_body_byte_boundaries(self) -> None:
        header = "---\nname: rp-demo\ndescription: boundary check\n---\n\n"
        for size, expect_ok, expect_warn in (
            (22_000, True, False),
            (22_001, True, True),
            (24_000, True, True),
            (24_001, False, False),
        ):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                _make_valid_repo(root)
                skill_md = root / "rp-plugins" / "skills" / "rp-demo" / "SKILL.md"
                skill_md.write_text(header + ("a" * size), encoding="utf-8")
                res = vp.validate_repo(root)
                self.assertEqual(res.ok, expect_ok, res.errors)
                self.assertEqual(bool(res.warnings), expect_warn, res.warnings)

    def test_relative_links_escape_and_code_fence_handling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            skill_md = root / "rp-plugins" / "skills" / "rp-demo" / "SKILL.md"
            skill_md.write_text(
                "---\nname: rp-demo\ndescription: link test\n---\n\n"
                "```markdown\n[ignored](nonexistent.md)\n[ignored2](../../../README.md)\n```\n\n"
                "인라인 `[ignored3](missing.md)` 무시.\n"
                "[ok](reference/guide.md)\n",
                encoding="utf-8",
            )
            res = vp.validate_repo(root)
            self.assertTrue(res.ok, res.errors)

            # Broken link inside reference/*.md
            ref_md = root / "rp-plugins" / "skills" / "rp-demo" / "reference" / "guide.md"
            ref_md.write_text("[broken](missing.md)\n", encoding="utf-8")
            res_broken = vp.validate_repo(root)
            self.assertFalse(res_broken.ok)
            self.assertTrue(any("broken relative link" in e for e in res_broken.errors))

            # Path traversal escaping rp-plugins root
            ref_md.write_text("[escape](../../../../README.md)\n", encoding="utf-8")
            res_escape = vp.validate_repo(root)
            self.assertFalse(res_escape.ok)
            self.assertTrue(any("escapes plugin root" in e for e in res_escape.errors))

    def test_public_artifact_security_scan_and_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            # docs/prd/ should be excluded from public scan
            (root / "docs" / "prd").mkdir(parents=True)
            fake_local = "/" + "Users/alice/workspace"
            fake_ghp = "ghp_" + ("A" * 24)
            fake_sk = "sk-" + ("B" * 20)
            fake_age = "age1" + ("a" * 54)
            (root / "docs" / "prd" / "sample.md").write_text(
                f"{fake_local}\n{fake_ghp}\n{fake_sk}\n{fake_age}\n",
                encoding="utf-8",
            )
            # Benign hyphenated words must not trigger sk- false positives
            ref_md = root / "rp-plugins" / "skills" / "rp-demo" / "reference" / "guide.md"
            ref_md.write_text("task-12345678901234567890 disk-abcdefghijklmnop\n", encoding="utf-8")
            res_clean = vp.validate_repo(root)
            self.assertTrue(res_clean.ok, res_clean.errors)

            # Public artifact with local path + tokens must fail
            ref_md.write_text(f"{fake_local}\n{fake_ghp}\n{fake_sk}\n{fake_age}\n", encoding="utf-8")
            res_dirty = vp.validate_repo(root)
            self.assertFalse(res_dirty.ok)
            joined = "\n".join(res_dirty.errors)
            self.assertIn("local absolute path", joined)
            self.assertIn("GitHub classic token", joined)
            self.assertIn("API secret key", joined)
            self.assertIn("age public/secret recipient key", joined)


if __name__ == "__main__":
    unittest.main()
