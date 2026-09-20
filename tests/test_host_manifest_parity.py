"""The Claude Code and Codex host manifests must describe one shared skill body.

`skills/` is the single source of truth for behavior. Each host gets a thin
manifest over it; skill content is never forked per host. These tests fail when
the two manifests drift apart or when host-specific language leaks into the
shared skill.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "aio-agentic-sdlc"
CLAUDE_PLUGIN = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
CODEX_PLUGIN = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
SKILLS_DIR = PLUGIN_ROOT / "skills"
ROOT_MCP = REPO_ROOT / ".mcp.json"
PLUGIN_MCP = PLUGIN_ROOT / ".mcp.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestHostManifestsExist(unittest.TestCase):
    def test_both_host_plugin_manifests_are_present(self):
        self.assertTrue(CLAUDE_PLUGIN.is_file(), f"missing {CLAUDE_PLUGIN}")
        self.assertTrue(CODEX_PLUGIN.is_file(), f"missing {CODEX_PLUGIN}")

    def test_both_host_marketplaces_are_present(self):
        self.assertTrue(CLAUDE_MARKETPLACE.is_file(), f"missing {CLAUDE_MARKETPLACE}")
        self.assertTrue(CODEX_MARKETPLACE.is_file(), f"missing {CODEX_MARKETPLACE}")


class TestHostManifestParity(unittest.TestCase):
    def setUp(self):
        self.claude = _load(CLAUDE_PLUGIN)
        self.codex = _load(CODEX_PLUGIN)

    def test_plugin_identity_agrees(self):
        for field in ("name", "homepage", "repository", "license"):
            self.assertEqual(
                self.claude[field],
                self.codex[field],
                f"host manifests disagree on {field!r}",
            )

    def test_keywords_agree(self):
        self.assertEqual(
            sorted(self.claude["keywords"]), sorted(self.codex["keywords"])
        )

    def test_both_point_at_the_same_shared_skill_directory(self):
        self.assertEqual(self.claude["skills"], self.codex["skills"])
        resolved = (PLUGIN_ROOT / self.claude["skills"]).resolve()
        self.assertEqual(resolved, SKILLS_DIR.resolve())
        self.assertTrue(resolved.is_dir(), "shared skills directory does not exist")

    def test_both_point_at_the_same_mcp_configuration(self):
        self.assertEqual(self.claude["mcpServers"], self.codex["mcpServers"])

    def test_display_names_agree(self):
        self.assertEqual(
            self.claude["displayName"],
            self.codex["interface"]["displayName"],
            "Claude displayName and Codex interface.displayName must match",
        )


class TestMarketplaceEntries(unittest.TestCase):
    def test_claude_marketplace_points_at_the_plugin_directory(self):
        entry = _load(CLAUDE_MARKETPLACE)["plugins"][0]
        self.assertEqual(entry["name"], "aio-agentic-sdlc")
        resolved = (REPO_ROOT / entry["source"]).resolve()
        self.assertEqual(resolved, PLUGIN_ROOT.resolve())

    def test_both_marketplaces_resolve_to_the_same_plugin(self):
        claude_entry = _load(CLAUDE_MARKETPLACE)["plugins"][0]
        codex_entry = _load(CODEX_MARKETPLACE)["plugins"][0]
        claude_path = (REPO_ROOT / claude_entry["source"]).resolve()
        codex_path = (REPO_ROOT / codex_entry["source"]["path"]).resolve()
        self.assertEqual(claude_path, codex_path)

    def test_marketplace_version_matches_the_claude_plugin_manifest(self):
        entry = _load(CLAUDE_MARKETPLACE)["plugins"][0]
        self.assertEqual(entry["version"], _load(CLAUDE_PLUGIN)["version"])

    def test_both_host_manifests_declare_the_same_version(self):
        """Hosts ship one artifact, so they must not advertise different versions.

        The Codex manifest sat at 0.21.0 through twelve minor releases because
        nothing checked it, so installers were shown a version that was not the
        one they got.
        """

        claude = _load(CLAUDE_PLUGIN)["version"]
        codex = _load(CODEX_PLUGIN)["version"]
        self.assertEqual(
            claude.split("+", 1)[0],
            codex.split("+", 1)[0],
            "host manifests advertise different versions; "
            "update both when the package version changes",
        )


class TestSharedSkillIsHostNeutral(unittest.TestCase):
    def test_no_host_specific_language_in_the_shared_skill(self):
        offenders = []
        for path in sorted(SKILLS_DIR.rglob("*.md")):
            text = path.read_text(encoding="utf-8").lower()
            for host in ("codex", "claude", "antigravity"):
                if host in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} mentions {host!r}")
        self.assertEqual(
            offenders,
            [],
            "shared skill content must not name a host; "
            "host-specific wording belongs in the per-host manifest:\n"
            + "\n".join(offenders),
        )

    def test_shared_skill_has_a_skill_definition(self):
        self.assertTrue((SKILLS_DIR / "manage-sdlc" / "SKILL.md").is_file())


class TestMcpConfiguration(unittest.TestCase):
    def test_root_and_plugin_mcp_configs_agree(self):
        self.assertEqual(
            _load(ROOT_MCP),
            _load(PLUGIN_MCP),
            "the root .mcp.json that Claude Code auto-discovers must match the "
            "configuration the installed plugin ships",
        )

    def test_mcp_server_launches_the_stdio_entry_point(self):
        server = _load(ROOT_MCP)["mcpServers"]["aio-agentic-sdlc"]
        self.assertEqual(server["command"], "uvx")
        self.assertIn("aio-agentic-sdlc-mcp", server["args"])


if __name__ == "__main__":
    unittest.main()
