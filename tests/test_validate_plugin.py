"""Unit tests for scripts/validate_plugin.py and scripts/plugin_frontmatter.py."""

from __future__ import annotations

import contextlib
import io
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
                "suggestedPrompts": ["Run deck", "Run post", "Run youtube deck"],
                "author": {"name": "Rapa-Space", "url": "https://github.com/ryan-papa"},
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

    def test_invalid_json_reported_once_without_duplicate_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            (root / "rp-plugins" / ".claude-plugin" / "plugin.json").write_text("{broken", encoding="utf-8")
            res = vp.validate_repo(root)
            self.assertFalse(res.ok)
            json_errs = [e for e in res.errors if "invalid JSON" in e]
            self.assertEqual(len(json_errs), 1, res.errors)
            self.assertFalse(any("missing string 'version'" in e for e in res.errors), res.errors)

    def test_antigravity_manifest_schema_rules(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            path = root / "rp-plugins" / ".antigravity-plugin" / "plugin.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["unknownExtraKey"] = True
            data["displayName"] = "AntigravityHelper MyPlugin"
            data["suggestedPrompts"] = []
            data["repository"] = "http://insecure.example.com/repo"
            data["author"] = {
                "name": "Org",
                "email": 12345,
                "url": "http://insecure.example.com",
                "extraField": "bad",
            }
            path.write_text(json.dumps(data), encoding="utf-8")

            res = vp.validate_repo(root)
            self.assertFalse(res.ok)
            joined = "\n".join(res.errors)
            self.assertIn("additionalProperties=false", joined)
            self.assertIn("must not start with 'antigravity'", joined)
            self.assertIn("must not end with 'plugin'", joined)
            self.assertIn("suggestedPrompts", joined)
            self.assertIn("'repository' must be an https:// URL", joined)
            self.assertIn("'author' has disallowed keys", joined)
            self.assertIn("'author.email' must be a non-empty string", joined)
            self.assertIn("'author.url' must start with https://", joined)

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

    def test_frontmatter_edge_cases_and_length_boundaries(self) -> None:
        # Folded scalar + 0-indent YAML sequence
        text = (
            "---\n"
            "name: sample-skill\n"
            "description: >-\n"
            "  First line\n"
            "  second line\n"
            "allowed-tools:\n"
            "- Bash\n"
            "- Read\n"
            "---\n\n"
            "Body\n"
        )
        meta, body = vp.parse_frontmatter(text)
        self.assertEqual(meta["name"], "sample-skill")
        self.assertEqual(meta["description"], "First line second line")
        self.assertEqual(meta["allowed-tools"], ["Bash", "Read"])
        self.assertEqual(body, "Body\n")

        # Trailing spaces on closing '---' + markdown HR in body must NOT bypass 24KB limit
        bypass_attempt = (
            "---\nname: rp-demo\ndescription: hr bypass check\n---   \n\n"
            + ("a" * 25_000)
            + "\n---\nshort tail\n"
        )
        _, parsed_body = vp.parse_frontmatter(bypass_attempt)
        self.assertGreater(len(parsed_body.encode("utf-8")), 24_000)

        # Empty frontmatter parses cleanly and fails required fields
        empty_meta, empty_body = vp.parse_frontmatter("---\n---\nHello\n")
        self.assertEqual(empty_meta, {})
        self.assertEqual(empty_body, "Hello\n")

        # Name (64 vs 65) and description (1024 vs 1025) boundaries + unreadable UTF-8
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            long_name_ok = "a" * 64
            (root / "rp-plugins" / "skills" / long_name_ok).mkdir()
            (root / "rp-plugins" / "skills" / long_name_ok / "SKILL.md").write_text(
                f"---\nname: {long_name_ok}\ndescription: {'d' * 1024}\n---\n\n# ok\n",
                encoding="utf-8",
            )
            res_ok = vp.validate_repo(root)
            self.assertTrue(res_ok.ok, res_ok.errors)

            long_name_bad = "b" * 65
            (root / "rp-plugins" / "skills" / long_name_bad).mkdir()
            (root / "rp-plugins" / "skills" / long_name_bad / "SKILL.md").write_text(
                f"---\nname: {long_name_bad}\ndescription: {'d' * 1025}\n---\n\n# bad\n",
                encoding="utf-8",
            )
            res_bad = vp.validate_repo(root)
            self.assertFalse(res_bad.ok)
            joined = "\n".join(res_bad.errors)
            self.assertIn("1..64 char kebab-case", joined)
            self.assertIn("exceeds 1024 chars", joined)

            # Corrupt UTF-8 file produces validation error instead of crashing
            (root / "rp-plugins" / "skills" / long_name_bad / "SKILL.md").write_bytes(b"\xff\xfe\x00")
            res_corrupt = vp.validate_repo(root)
            self.assertFalse(res_corrupt.ok)
            self.assertTrue(any("unreadable UTF-8 text" in e for e in res_corrupt.errors), res_corrupt.errors)

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

    def test_relative_links_nested_fences_and_escape_handling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            skill_md = root / "rp-plugins" / "skills" / "rp-demo" / "SKILL.md"
            skill_md.write_text(
                "---\nname: rp-demo\ndescription: link test\n---\n\n"
                "````markdown\n"
                "```text\n"
                "[nested-ignored](missing-nested.md)\n"
                "```\n"
                "[still-inside-4-fence](missing-nested-2.md)\n"
                "````\n\n"
                "인라인 `[ignored3](missing.md)` 무시.\n"
                "[ok](reference/guide.md)\n",
                encoding="utf-8",
            )
            res = vp.validate_repo(root)
            self.assertTrue(res.ok, res.errors)

            ref_md = root / "rp-plugins" / "skills" / "rp-demo" / "reference" / "guide.md"
            ref_md.write_text("[broken](missing.md)\n", encoding="utf-8")
            res_broken = vp.validate_repo(root)
            self.assertFalse(res_broken.ok)
            self.assertTrue(any("broken relative link" in e for e in res_broken.errors))

            ref_md.write_text("[escape](../../../../README.md)\n", encoding="utf-8")
            res_escape = vp.validate_repo(root)
            self.assertFalse(res_escape.ok)
            self.assertTrue(any("escapes plugin root" in e for e in res_escape.errors))

    def test_public_artifact_security_scan_and_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_valid_repo(root)
            (root / "docs" / "prd").mkdir(parents=True)
            fake_mac = "/" + "Users/alice/workspace"
            fake_linux = "/" + "home/bob/project"
            fake_ghp = "ghp_" + ("A" * 24)
            fake_pat = "github_pat_" + ("C" * 24)
            fake_sk = "sk-" + ("B" * 20)
            fake_age_pub = "age1" + ("a" * 54)
            fake_age_sec = "AGE-SECRET-KEY-1" + ("X" * 54)
            (root / "docs" / "prd" / "sample.md").write_text(
                "\n".join((fake_mac, fake_linux, fake_ghp, fake_pat, fake_sk, fake_age_pub, fake_age_sec)),
                encoding="utf-8",
            )
            ref_md = root / "rp-plugins" / "skills" / "rp-demo" / "reference" / "guide.md"
            ref_md.write_text("task-12345678901234567890 disk-abcdefghijklmnop\n", encoding="utf-8")
            res_clean = vp.validate_repo(root)
            self.assertTrue(res_clean.ok, res_clean.errors)

            ref_md.write_text(
                "\n".join((fake_mac, fake_linux, fake_ghp, fake_pat, fake_sk, fake_age_pub, fake_age_sec)),
                encoding="utf-8",
            )
            res_dirty = vp.validate_repo(root)
            self.assertFalse(res_dirty.ok)
            joined = "\n".join(res_dirty.errors)
            self.assertEqual(joined.count("local absolute path"), 2, joined)
            self.assertIn("GitHub classic token", joined)
            self.assertIn("GitHub fine-grained token", joined)
            self.assertIn("API secret key", joined)
            self.assertIn("age public recipient key", joined)
            self.assertIn("age secret key", joined)

    def test_rp_deck_split_and_youtube_deck_cross_references(self) -> None:
        deck_skill = REPO_ROOT / "rp-plugins" / "skills" / "rp-deck" / "SKILL.md"
        deck_ops = REPO_ROOT / "rp-plugins" / "skills" / "rp-deck" / "reference" / "operations.md"
        yt_deck_skill = REPO_ROOT / "rp-plugins" / "skills" / "rp-youtube-deck" / "SKILL.md"

        self.assertTrue(deck_ops.is_file())
        _, body = vp.parse_frontmatter(deck_skill.read_text(encoding="utf-8"))
        self.assertLessEqual(len(body.encode("utf-8")), 21_000)

        ops_text = deck_ops.read_text(encoding="utf-8")
        for heading in (
            "## 타깃 레포",
            "## 홈 버튼",
            "## 옵시디언 지식베이스 적재",
            "## 보강 vs 신규",
            "## 삭제 모드",
        ):
            self.assertIn(heading, ops_text)

        self.assertIn("reference/operations.md", deck_skill.read_text(encoding="utf-8"))
        self.assertIn("../rp-deck/reference/operations.md", yt_deck_skill.read_text(encoding="utf-8"))

        res = vp.ValidationResult()
        vp.validate_skills(REPO_ROOT, res)
        self.assertTrue(res.ok, res.errors)
        self.assertEqual(res.warnings, [])

    def test_three_runtime_adapters_and_fallbacks(self) -> None:
        skills_dir = REPO_ROOT / "rp-plugins" / "skills"
        for review_rel in ("rp-deck/reference/review.md", "rp-post/reference/review.md"):
            text = (skills_dir / review_rel).read_text(encoding="utf-8")
            for token in ("Antigravity", "invoke_subagent", 'TypeName: "self"', "send_message", "swarm"):
                self.assertIn(token, text, f"{review_rel} missing {token}")

        post_skill = (skills_dir / "rp-post" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Antigravity", post_skill)
        self.assertIn("search_web", post_skill)

        yt_deck = (skills_dir / "rp-youtube-deck" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("search_web", yt_deck)

        deck_skill = (skills_dir / "rp-deck" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("search_web", deck_skill)
        self.assertIn("GEMINI.md", deck_skill)

        recap_meta, recap_body = vp.parse_frontmatter(
            (skills_dir / "rp-codebase-recap" / "SKILL.md").read_text(encoding="utf-8")
        )
        self.assertNotIn("Agent", recap_meta.get("allowed-tools", []))
        self.assertIn("/tmp", recap_body)

    def test_actual_repo_passes_validation_and_cli_io(self) -> None:
        res = vp.validate_repo(REPO_ROOT)
        self.assertTrue(res.ok, res.errors)
        self.assertEqual(res.warnings, [], res.warnings)
        self.assertEqual(res.skill_count, 6)

        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = vp.main(["--repo-root", str(REPO_ROOT)])
        self.assertEqual(rc, 0)
        self.assertIn("OK: validated 6 skills", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_cli_returns_nonzero_and_writes_stderr_on_invalid_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = vp.main(["--repo-root", td])
            self.assertEqual(rc, 1)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("ERROR:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
