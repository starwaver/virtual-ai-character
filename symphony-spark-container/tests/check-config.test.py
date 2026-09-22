#!/usr/bin/env python3
"""Focused tests for safe source and installed configuration reports."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "symphony-spark-container/scripts/check-config.py"
ENTRYPOINT = ROOT / "symphony-spark-container/scripts/symphony-entrypoint.sh"


class CheckConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.installed = self.root / "installed"
        self.codex_home = self.root / "codex-home"
        for path in (
            self.source / "config/agents",
            self.installed / "config/agents",
            self.codex_home / "agents",
        ):
            path.mkdir(parents=True)
        self._write(self.source / "WORKFLOW.md", "workflow\n")
        self._write(self.source / "config/config.toml", "slots = 4\n")
        for filename in (
            "acceptance-reviewer.toml",
            "implementation-worker-qwen.toml",
            "implementation-worker.toml",
            "planner.toml",
            "progress-orchestrator.toml",
        ):
            self._write(self.source / "config/agents" / filename, f"name = '{filename[:-6]}'\n")
        self._write(self.source / "config/spark-qwen.config.toml", "model = 'qwen3.8-27b'\n")
        self._copy_targets()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write(self, path: Path, contents: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    def _copy_targets(self) -> None:
        shutil.copytree(self.source / "config", self.installed / "config", dirs_exist_ok=True)
        shutil.copy2(self.source / "WORKFLOW.md", self.installed / "WORKFLOW.md")
        shutil.copy2(self.source / "config/config.toml", self.codex_home / "config.toml")
        shutil.copytree(self.source / "config/agents", self.codex_home / "agents", dirs_exist_ok=True)
        shutil.copy2(self.source / "config/spark-qwen.config.toml", self.codex_home / "spark-qwen.config.toml")

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *arguments],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_source_and_matching_targets_pass_without_contents(self) -> None:
        result = self._run(
            "compare",
            "--workspace",
            str(self.source),
            "--installed-root",
            str(self.installed),
            "--codex-home",
            str(self.codex_home),
        )

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "matched")
        self.assertNotIn("gpt-6-astra", result.stdout)
        self.assertNotIn("workflow", result.stdout)

    def test_changed_target_reports_mismatch_without_raw_content(self) -> None:
        self._write(self.codex_home / "agents/planner.toml", "model = 'secret-sentinel'\n")

        result = self._run(
            "compare",
            "--workspace",
            str(self.source),
            "--installed-root",
            str(self.installed),
            "--codex-home",
            str(self.codex_home),
        )

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "mismatch")
        self.assertNotIn("secret-sentinel", result.stdout)

    def test_missing_target_is_unavailable(self) -> None:
        (self.codex_home / "agents/planner.toml").unlink()

        result = self._run(
            "compare",
            "--workspace",
            str(self.source),
            "--installed-root",
            str(self.installed),
            "--codex-home",
            str(self.codex_home),
        )

        self.assertEqual(result.returncode, 3)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["targets"]["codex_home"]["status"], "unavailable")

    def test_extra_agent_is_reported_as_drift(self) -> None:
        self._write(self.codex_home / "agents/stale-role.toml", "model = 'old'\n")

        result = self._run(
            "compare",
            "--workspace",
            str(self.source),
            "--installed-root",
            str(self.installed),
            "--codex-home",
            str(self.codex_home),
        )

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["targets"]["codex_home"]["status"], "mismatch")
        self.assertEqual(report["targets"]["codex_home"]["extra_files"], ["agents/stale-role.toml"])

    def test_missing_expected_source_file_is_unavailable(self) -> None:
        (self.source / "config/agents/planner.toml").unlink()

        result = self._run(
            "compare",
            "--workspace",
            str(self.source),
            "--installed-root",
            str(self.installed),
            "--codex-home",
            str(self.codex_home),
        )

        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")

    def test_configuration_parent_symlink_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        linked_agents = self.root / "linked-agents"
        linked_agents.symlink_to(outside, target_is_directory=True)
        (self.source / "config/agents").rename(self.source / "config/agents-real")
        (self.source / "config/agents").symlink_to(linked_agents, target_is_directory=True)

        result = self._run("source", "--workspace", str(self.source))

        self.assertEqual(result.returncode, 3)
        self.assertIn("CONFIG_SYMLINK", result.stderr)

    def test_source_path_symlink_is_rejected(self) -> None:
        (self.source / "WORKFLOW.md").unlink()
        (self.source / "WORKFLOW.md").symlink_to(self.root / "outside.txt")
        (self.root / "outside.txt").write_text("outside\n", encoding="utf-8")

        result = self._run("source", "--workspace", str(self.source))

        self.assertEqual(result.returncode, 3)
        self.assertIn("CONFIG_SYMLINK", result.stderr)

    def test_external_workflow_parent_symlink_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        self._write(outside / "WORKFLOW.md", "workflow\n")
        linked_parent = self.root / "linked-workflow"
        linked_parent.symlink_to(outside, target_is_directory=True)

        result = self._run(
            "source",
            "--workspace",
            str(self.source),
            "--workflow",
            str(linked_parent / "WORKFLOW.md"),
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("CONFIG_SYMLINK", result.stderr)

    # https://github.com/moeru-ai/airi/issues/3
    def test_documented_source_command_accepts_parent_workflow_path(self) -> None:
        self._write(self.root / "WORKFLOW.md", "workflow\n")

        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "source",
                "--workspace",
                ".",
                "--workflow",
                "../WORKFLOW.md",
            ],
            cwd=self.source,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "matched")

    def test_repository_routes_match_required_configuration(self) -> None:
        result = self._run(
            "validate",
            "--workspace",
            str(ROOT / "symphony-spark-container"),
            "--workflow",
            str(ROOT / "WORKFLOW.md"),
        )

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "matched")

    def test_repository_source_layout_accepts_workflow_outside_deployment_directory(self) -> None:
        result = self._run(
            "source",
            "--workspace",
            str(ROOT / "symphony-spark-container"),
            "--workflow",
            str(ROOT / "WORKFLOW.md"),
        )

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "matched")

    def test_repository_route_check_rejects_wrong_default_route(self) -> None:
        deployment = self.root / "deployment"
        shutil.copytree(ROOT / "symphony-spark-container", deployment)
        workflow = self.root / "WORKFLOW.md"
        shutil.copy2(ROOT / "WORKFLOW.md", workflow)
        self._write(
            deployment / "config/config.toml",
            (deployment / "config/config.toml").read_text(encoding="utf-8").replace(
                'default_subagent_reasoning_effort = "xhigh"',
                'default_subagent_reasoning_effort = "low"',
            ),
        )

        result = self._run(
            "validate",
            "--workspace",
            str(deployment),
            "--workflow",
            str(workflow),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID_AGENT_CAPACITY", result.stdout)

    def test_repository_route_check_rejects_wrong_qwen_profile(self) -> None:
        deployment = self.root / "deployment"
        shutil.copytree(ROOT / "symphony-spark-container", deployment)
        workflow = self.root / "WORKFLOW.md"
        shutil.copy2(ROOT / "WORKFLOW.md", workflow)
        self._write(
            deployment / "config/spark-qwen.config.toml",
            (deployment / "config/spark-qwen.config.toml").read_text(encoding="utf-8").replace(
                'model = "qwen3.8-27b"',
                'model = "wrong-model"',
            ),
        )

        result = self._run(
            "validate",
            "--workspace",
            str(deployment),
            "--workflow",
            str(workflow),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID_QWEN_PROFILE", result.stdout)

    def test_entrypoint_checks_the_selected_workflow_path(self) -> None:
        entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

        self.assertIn('  --workflow "$workflow_path" \\\n', entrypoint)

    def test_entrypoint_checks_existing_targets_before_synchronization(self) -> None:
        entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

        self.assertLess(
            entrypoint.index('if [[ -e "$config_install_dir/WORKFLOW.md"'),
            entrypoint.index('install -d -m 0700 "$CODEX_HOME"'),
        )

    def test_wrong_primary_command_is_rejected_even_when_route_tokens_exist_elsewhere(self) -> None:
        workflow = self.root / "WORKFLOW.md"
        workflow.write_text(
            "---\n"
            "codex:\n"
            "  command: codex --config model=gpt-5.6-luna app-server\n"
            "---\n"
            "The text mentions model_reasoning_effort=xhigh.\n",
            encoding="utf-8",
        )

        result = self._run(
            "validate",
            "--workspace",
            str(self.source),
            "--workflow",
            str(workflow),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID_WORKFLOW_ROUTE", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_Issue_3_rejects_an_exact_command_in_a_non_primary_section(self) -> None:
        workflow = self.root / "WORKFLOW.md"
        workflow.write_text(
            "---\n"
            "other:\n"
            "  command: codex --config shell_environment_policy.inherit=all --config 'model=\"gpt-5.6-luna\"' --config model_reasoning_effort=xhigh app-server\n"
            "codex:\n"
            "  command: codex --config model=gpt-5.6-luna app-server\n"
            "---\n",
            encoding="utf-8",
        )

        result = self._run(
            "validate",
            "--workspace",
            str(ROOT / "symphony-spark-container"),
            "--workflow",
            str(workflow),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("INVALID_WORKFLOW_ROUTE", result.stdout)


if __name__ == "__main__":
    unittest.main()
