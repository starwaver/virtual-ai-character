#!/usr/bin/env python3
"""Focused tests for the Symphony publication gate."""

from __future__ import annotations

from copy import deepcopy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "symphony-spark-container/scripts/check-publication.py"


class PublicationGateTests(unittest.TestCase):
    def _artifact(self) -> dict[str, object]:
        return {
            "schema_version": "symphony.publication.v1",
            "issue_id": "3",
            "plan_id": "PLAN-001",
            "path": "full",
            "evidence_revision": "evidence-001",
            "source_fingerprint": "a" * 64,
            "changed_files": ["WORKFLOW.md"],
            "acceptance": {f"ACC-{number:03d}": "passed" for number in range(1, 7)},
            "checks": [
                {
                    "check_id": check_id,
                    "command": {
                        "focused-tests": "python3 -B symphony-spark-container/tests/check-config.test.py -v && python3 -B symphony-spark-container/tests/check-publication.test.py -v",
                        "route-check": "python3 -B symphony-spark-container/scripts/check-config.py validate --workspace symphony-spark-container --workflow WORKFLOW.md",
                        "git-diff-check": "git diff --check",
                        "pnpm-typecheck": "pnpm typecheck",
                        "pnpm-lint": "pnpm lint",
                    }[check_id],
                    "working_directory": ".",
                    "exit_status": 0,
                    "status": "passed",
                    "observed_at": "2026-09-22T00:00:00Z",
                    "evidence_revision": "evidence-001",
                    "source_fingerprint": "a" * 64,
                    "output_ref": f".git/symphony/issue-3/checks/{check_id}.json",
                    "result_summary": f"{check_id} passed.",
                }
                for check_id in (
                    "focused-tests",
                    "route-check",
                    "git-diff-check",
                    "pnpm-typecheck",
                    "pnpm-lint",
                )
            ],
            "tasks": [
                {
                    "task_id": "PLAN-001",
                    "plan_id": "PLAN-001",
                    "status": "accepted",
                    "dependencies": [],
                    "acceptance_ids": ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-006"],
                    "attempt": 1,
                    "attempt_started_at": "2026-09-22T00:00:00Z",
                    "owner": {
                        "role": "planner",
                        "model": "gpt-6-astra",
                        "reasoning": "high",
                        "route_reason": "The planner defines the task graph.",
                    },
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "evidence": {
                        "summary": "The plan was accepted.",
                        "attempt": 1,
                        "checks": {
                            "focused-tests": "python3 -B symphony-spark-container/tests/check-config.test.py -v && python3 -B symphony-spark-container/tests/check-publication.test.py -v",
                        },
                        "worker_checks": {
                            "worker-focused-tests": "python3 -B symphony-spark-container/tests/check-publication.test.py -v",
                        },
                    },
                },
                {
                    "task_id": "IMPLEMENT-001",
                    "plan_id": "PLAN-001",
                    "status": "accepted",
                    "dependencies": ["PLAN-001"],
                    "acceptance_ids": ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-006"],
                    "attempt": 1,
                    "attempt_started_at": "2026-09-22T00:00:00Z",
                    "owner": {
                        "role": "implementation-worker",
                        "model": "gpt-5.6-luna",
                        "reasoning": "xhigh",
                        "route_reason": "The worker owns the bounded implementation.",
                    },
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "evidence": {"summary": "The implementation checks passed.", "attempt": 1, "changed_files": ["WORKFLOW.md"]},
                },
                {
                    "task_id": "VALIDATE-001",
                    "plan_id": "PLAN-001",
                    "status": "accepted",
                    "dependencies": ["IMPLEMENT-001"],
                    "acceptance_ids": ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-006"],
                    "attempt": 1,
                    "attempt_started_at": "2026-09-22T00:00:00Z",
                    "owner": {
                        "role": "primary-coordinator",
                        "model": "gpt-5.6-luna",
                        "reasoning": "xhigh",
                        "route_reason": "The coordinator owns validation.",
                    },
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "evidence": {"summary": "The validation checks passed.", "attempt": 1},
                },
                {
                    "task_id": "PROGRESS-001",
                    "plan_id": "PLAN-001",
                    "status": "accepted",
                    "dependencies": ["IMPLEMENT-001"],
                    "acceptance_ids": ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-006"],
                    "attempt": 1,
                    "attempt_started_at": "2026-09-22T00:00:00Z",
                    "owner": {
                        "role": "progress-orchestrator",
                        "model": "gpt-6-astra",
                        "reasoning": "high",
                        "route_reason": "The reviewer owns the checkpoint.",
                    },
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "evidence": {"summary": "The checkpoint passed.", "attempt": 1},
                },
                {
                    "task_id": "ACCEPT-001",
                    "plan_id": "PLAN-001",
                    "status": "accepted",
                    "dependencies": ["VALIDATE-001"],
                    "acceptance_ids": ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-006"],
                    "attempt": 1,
                    "attempt_started_at": "2026-09-22T00:00:00Z",
                    "owner": {
                        "role": "acceptance-reviewer",
                        "model": "gpt-6-astra",
                        "reasoning": "high",
                        "route_reason": "The reviewer owns final acceptance.",
                    },
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "evidence": {"summary": "The acceptance review passed.", "attempt": 1},
                },
            ],
            "worker_results": [
                {
                    "schema_version": "symphony.worker-result.v1",
                    "issue_id": "3",
                    "plan_id": "PLAN-001",
                    "task_id": "IMPLEMENT-001",
                    "attempt": 1,
                    "status": "completed",
                    "changed_files": ["WORKFLOW.md"],
                    "acceptance_ids": ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005", "ACC-006"],
                    "route": {
                        "role": "implementation-worker",
                        "model": "gpt-5.6-luna",
                        "reasoning": "xhigh",
                        "route_reason": "The worker owns the bounded implementation.",
                        "invocation_id": "worker-001",
                    },
                    "evidence": {
                        "summary": "The worker returned complete evidence.",
                        "output_ref": ".git/symphony/issue-3/workers/IMPLEMENT-001.json",
                    },
                    "checks": [
                        {
                            "check_id": "worker-focused-tests",
                            "command": "python3 -B symphony-spark-container/tests/check-publication.test.py -v",
                            "status": "passed",
                            "exit_status": 0,
                        }
                    ],
                    "risks": [],
                    "unfinished_work": [],
                    "scope_error": None,
                    "observed_at": "2026-09-22T00:00:00Z",
                }
            ],
            "route_records": [
                {
                    "task_id": "VALIDATE-001",
                    "role": "primary-coordinator",
                    "model": "gpt-5.6-luna",
                    "reasoning": "xhigh",
                    "status": "verified",
                    "route_reason": "The coordinator owns integration and publication.",
                    "invocation_id": "coord-001",
                    "observed_at": "2026-09-22T00:00:00Z",
                },
                {
                    "task_id": "PLAN-001",
                    "role": "planner",
                    "model": "gpt-6-astra",
                    "reasoning": "high",
                    "status": "verified",
                    "route_reason": "The planner owns read-only task design.",
                    "invocation_id": "plan-001",
                    "observed_at": "2026-09-22T00:00:00Z",
                },
                {
                    "task_id": "IMPLEMENT-001",
                    "role": "implementation-worker",
                    "model": "gpt-5.6-luna",
                    "reasoning": "xhigh",
                    "status": "verified",
                    "route_reason": "The worker owns bounded implementation.",
                    "invocation_id": "worker-001",
                    "observed_at": "2026-09-22T00:00:00Z",
                },
                {
                    "task_id": "PROGRESS-001",
                    "role": "progress-orchestrator",
                    "model": "gpt-6-astra",
                    "reasoning": "high",
                    "status": "verified",
                    "route_reason": "The reviewer owns the full-path checkpoint.",
                    "invocation_id": "progress-001",
                    "observed_at": "2026-09-22T00:00:00Z",
                },
                {
                    "task_id": "ACCEPT-001",
                    "role": "acceptance-reviewer",
                    "model": "gpt-6-astra",
                    "reasoning": "high",
                    "status": "verified",
                    "route_reason": "The reviewer owns final acceptance.",
                    "invocation_id": "accept-001",
                    "observed_at": "2026-09-22T00:00:00Z",
                },
            ],
            "checkpoints": [
                {
                    "checkpoint_id": "PROGRESS-001",
                    "plan_id": "PLAN-001",
                    "worker_wave": 1,
                    "trigger": "wave_started",
                    "decision": "CONTINUE",
                    "reviewer": {"role": "progress-orchestrator", "model": "gpt-6-astra", "reasoning": "high"},
                    "evidence": {"task_ids": ["IMPLEMENT-001"], "files": ["WORKFLOW.md"], "checks": [], "findings": []},
                    "observed_at": "2026-09-22T00:00:00Z",
                }
            ],
            "review": {
                "role": "acceptance-reviewer",
                "model": "gpt-6-astra",
                "reasoning": "high",
                "verdict": "ACCEPT",
                "findings": [],
                "review_id": "review-001",
                "invocation_id": "accept-001",
                "evidence_revision": "evidence-001",
                "source_fingerprint": "a" * 64,
                "observed_at": "2026-09-22T00:00:00Z",
            },
            "repairs": {"cycles": 0, "max_cycles": 2, "open_task_ids": [], "records": []},
            "drift": self._drift(),
            "git": {"branch": "symphony/issue-3", "scope_clean": True, "secret_scan": "diff reviewed"},
            "published": False,
        }

    def _drift(self) -> dict[str, object]:
        paths = [
            "WORKFLOW.md",
            "config/config.toml",
            "config/agents/acceptance-reviewer.toml",
            "config/agents/implementation-worker-qwen.toml",
            "config/agents/implementation-worker.toml",
            "config/agents/planner.toml",
            "config/agents/progress-orchestrator.toml",
            "config/spark-qwen.config.toml",
        ]
        source_files = [{"path": path, "sha256": "b" * 64} for path in paths]
        target_files = [{"path": path, "source_path": path, "sha256": "b" * 64} for path in paths]
        return {
            "status": "matched",
            "required_files": paths,
            "source_files": source_files,
            "targets": {
                "installed": {"status": "matched", "files": target_files, "extra_files": []},
                "codex_home": {
                    "status": "matched",
                    "files": [file for file in target_files if file["source_path"] != "WORKFLOW.md"],
                    "extra_files": [],
                },
            },
            "hash_algorithm": "sha256",
        }

    def _run(self, artifact: dict[str, object], *arguments: str) -> subprocess.CompletedProcess[str]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as stream:
            json.dump(artifact, stream)
            stream.flush()
            return subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--artifact", stream.name, *arguments],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

    def _repair_artifact(self) -> dict[str, object]:
        artifact = self._artifact()
        repair_task = deepcopy(artifact["tasks"][1])  # type: ignore[index]
        repair_task["task_id"] = "REPAIR-001-001"
        repair_task["dependencies"] = ["IMPLEMENT-001"]
        repair_task["attempt_started_at"] = "2026-09-22T00:01:00Z"
        repair_task["evidence"]["summary"] = "The repair checks passed."  # type: ignore[index]
        artifact["tasks"].append(repair_task)  # type: ignore[index]
        artifact["tasks"][2]["dependencies"].append("REPAIR-001-001")  # type: ignore[index]

        repair_result = deepcopy(artifact["worker_results"][0])  # type: ignore[index]
        repair_result["task_id"] = "REPAIR-001-001"
        repair_result["route"]["invocation_id"] = "repair-001"  # type: ignore[index]
        repair_result["evidence"]["output_ref"] = ".git/symphony/issue-3/workers/REPAIR-001-001.json"  # type: ignore[index]
        repair_result["observed_at"] = "2026-09-22T00:01:00Z"
        artifact["worker_results"].append(repair_result)  # type: ignore[index]

        repair_route = deepcopy(
            next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        )
        repair_route["task_id"] = "REPAIR-001-001"
        repair_route["invocation_id"] = "repair-001"
        repair_route["observed_at"] = "2026-09-22T00:01:00Z"
        artifact["route_records"].append(repair_route)  # type: ignore[index]
        artifact["checkpoints"][0]["evidence"]["task_ids"].append("REPAIR-001-001")  # type: ignore[index]
        artifact["checkpoints"][0]["observed_at"] = "2026-09-22T00:01:00Z"  # type: ignore[index]
        artifact["checks"][0]["observed_at"] = "2026-09-22T00:01:00Z"  # type: ignore[index]
        artifact["review"]["observed_at"] = "2026-09-22T00:01:00Z"  # type: ignore[index]
        artifact["repairs"] = {
            "cycles": 1,
            "max_cycles": 2,
            "open_task_ids": [],
            "records": [
                {
                    "task_id": "REPAIR-001-001",
                    "status": "accepted",
                    "cycle": 1,
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "acceptance_ids": ["ACC-001"],
                    "rerun_check_ids": ["focused-tests"],
                    "failure_refs": ["focused-tests"],
                    "resolution": "The repair evidence was recorded.",
                }
            ],
        }
        return artifact

    def test_complete_evidence_is_accepted(self) -> None:
        result = self._run(self._artifact())

        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "accepted")

    def test_checks_must_match_the_reviewed_source_revision(self) -> None:
        artifact = self._artifact()
        artifact["checks"][0]["source_fingerprint"] = "c" * 64  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_FINGERPRINT_MISMATCH", result.stdout)

    def test_required_checks_must_follow_the_active_implementation(self) -> None:
        artifact = self._artifact()
        artifact["worker_results"][0]["observed_at"] = "2026-09-22T00:01:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_focused-tests_STALE", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_focused_check_command_must_match_the_accepted_plan(self) -> None:
        artifact = self._artifact()
        artifact["tasks"][0]["evidence"]["checks"]["focused-tests"] = "python3 -B custom-focused-tests.py"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_PLAN_COMMAND_INVALID", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_worker_result_is_required_for_each_implementation_task(self) -> None:
        artifact = self._artifact()
        del artifact["worker_results"]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("WORKER_RESULTS_MISSING", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_failed_worker_result_cannot_be_published(self) -> None:
        artifact = self._artifact()
        artifact["worker_results"][0]["status"] = "failed"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("WORKER_RESULT_1_NOT_COMPLETED", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_failed_prior_attempt_is_preserved_when_the_new_attempt_passes(self) -> None:
        artifact = self._artifact()
        task = artifact["tasks"][1]  # type: ignore[index]
        task["attempt"] = 2
        task["attempt_started_at"] = "2026-09-22T00:01:00Z"
        task["evidence"]["attempt"] = 2  # type: ignore[index]

        active_result = artifact["worker_results"][0]  # type: ignore[index]
        prior_result = deepcopy(active_result)
        prior_result["attempt"] = 1
        prior_result["status"] = "failed"
        prior_result["unfinished_work"] = ["The first attempt failed."]
        prior_result["scope_error"] = "The first attempt stopped."
        prior_result["route"]["invocation_id"] = "worker-history-001"  # type: ignore[index]
        prior_result["observed_at"] = "2026-09-22T00:00:30Z"
        artifact["worker_results"].append(prior_result)  # type: ignore[index]
        active_result["attempt"] = 2
        active_result["route"]["invocation_id"] = "worker-002"  # type: ignore[index]
        active_result["observed_at"] = "2026-09-22T00:02:00Z"
        worker_route = next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        worker_route["invocation_id"] = "worker-history-001"
        worker_route["observed_at"] = "2026-09-22T00:00:30Z"
        worker_route = deepcopy(worker_route)
        worker_route["invocation_id"] = "worker-002"
        worker_route["observed_at"] = "2026-09-22T00:02:00Z"
        artifact["route_records"].append(worker_route)  # type: ignore[index]
        for check in artifact["checks"]:  # type: ignore[index]
            check["observed_at"] = "2026-09-22T00:02:00Z"
        artifact["checkpoints"][0]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]
        artifact["review"]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_reverted_file_from_a_failed_attempt_does_not_enter_the_final_diff(self) -> None:
        artifact = self._artifact()
        task = artifact["tasks"][1]  # type: ignore[index]
        task["attempt"] = 2
        task["attempt_started_at"] = "2026-09-22T00:01:00Z"
        task["scope"]["include"].append("docs/README.md")  # type: ignore[index]
        task["evidence"]["attempt"] = 2  # type: ignore[index]

        active_result = artifact["worker_results"][0]  # type: ignore[index]
        prior_result = deepcopy(active_result)
        prior_result["attempt"] = 1
        prior_result["status"] = "failed"
        prior_result["changed_files"] = ["WORKFLOW.md", "docs/README.md"]
        prior_result["route"]["invocation_id"] = "worker-history-002"  # type: ignore[index]
        prior_result["observed_at"] = "2026-09-22T00:00:30Z"
        artifact["worker_results"].append(prior_result)  # type: ignore[index]
        active_result["attempt"] = 2
        active_result["route"]["invocation_id"] = "worker-003"  # type: ignore[index]
        active_result["observed_at"] = "2026-09-22T00:02:00Z"
        worker_route = next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        worker_route["invocation_id"] = "worker-history-002"
        worker_route["observed_at"] = "2026-09-22T00:00:30Z"
        worker_route = deepcopy(worker_route)
        worker_route["invocation_id"] = "worker-003"
        worker_route["observed_at"] = "2026-09-22T00:02:00Z"
        artifact["route_records"].append(worker_route)  # type: ignore[index]
        artifact["checkpoints"][0]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]
        for check in artifact["checks"]:  # type: ignore[index]
            check["observed_at"] = "2026-09-22T00:02:00Z"
        artifact["review"]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_implementation_requires_the_planner_dependency(self) -> None:
        artifact = self._artifact()
        artifact["tasks"][1]["dependencies"] = []  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_IMPLEMENT-001_PLANNER_DEPENDENCY_MISSING", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_scope_cannot_include_and_exclude_the_same_path(self) -> None:
        artifact = self._artifact()
        artifact["tasks"][1]["scope"]["exclude"] = ["WORKFLOW.md"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_2_SCOPE_INCLUDE_EXCLUDE_OVERLAP", result.stdout)

    def test_worker_result_must_stay_inside_its_own_exact_scope(self) -> None:
        artifact = self._artifact()
        implementation = deepcopy(artifact["tasks"][1])  # type: ignore[index]
        implementation["task_id"] = "IMPLEMENT-002"
        implementation["scope"] = {"include": ["docs/README.md"], "exclude": []}
        implementation["evidence"]["changed_files"] = ["WORKFLOW.md"]  # type: ignore[index]
        artifact["tasks"].append(implementation)  # type: ignore[index]

        worker_result = deepcopy(artifact["worker_results"][0])  # type: ignore[index]
        worker_result["task_id"] = "IMPLEMENT-002"
        worker_result["route"]["invocation_id"] = "worker-002"  # type: ignore[index]
        worker_result["evidence"]["output_ref"] = ".git/symphony/issue-3/workers/IMPLEMENT-002.json"  # type: ignore[index]
        artifact["worker_results"].append(worker_result)  # type: ignore[index]

        worker_route = deepcopy(
            next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        )
        worker_route["task_id"] = "IMPLEMENT-002"
        worker_route["invocation_id"] = "worker-002"
        artifact["route_records"].append(worker_route)  # type: ignore[index]
        artifact["checkpoints"][0]["evidence"]["task_ids"].append("IMPLEMENT-002")  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("WORKER_RESULT_2_FILE_OUTSIDE_SCOPE", result.stdout)

    def test_final_changed_files_must_match_active_worker_results(self) -> None:
        artifact = self._artifact()
        artifact["changed_files"].append("docs/README.md")  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHANGED_FILES_RESULT_MISMATCH", result.stdout)

    def test_repair_task_must_keep_the_predecessor_scope(self) -> None:
        artifact = self._repair_artifact()
        artifact["tasks"][-1]["scope"] = {"include": ["docs/README.md"], "exclude": []}  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_TASK_SCOPE_MISMATCH", result.stdout)

    def test_light_path_does_not_require_progress_route(self) -> None:
        artifact = self._artifact()
        artifact["path"] = "light"
        artifact["checkpoints"] = []
        artifact["tasks"] = [
            task for task in artifact["tasks"] if task["task_id"] != "PROGRESS-001"  # type: ignore[index]
        ]  # type: ignore[index]
        artifact["route_records"] = [
            route
            for route in artifact["route_records"]
            if route["role"] != "progress-orchestrator"
        ]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    # https://github.com/moeru-ai/airi/issues/3
    def test_repair_can_reuse_the_scope_of_an_accepted_dependency(self) -> None:
        result = self._run(self._repair_artifact())

        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "accepted")

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_two_ordered_repairs_can_reuse_the_original_scope(self) -> None:
        artifact = self._repair_artifact()
        second_task = deepcopy(artifact["tasks"][-1])  # type: ignore[index]
        second_task["task_id"] = "REPAIR-001-002"
        second_task["dependencies"] = ["REPAIR-001-001"]
        second_task["attempt_started_at"] = "2026-09-22T00:02:00Z"
        second_task["evidence"]["summary"] = "The second repair checks passed."  # type: ignore[index]
        artifact["tasks"].append(second_task)  # type: ignore[index]
        artifact["tasks"][2]["dependencies"].append("REPAIR-001-002")  # type: ignore[index]

        second_result = deepcopy(artifact["worker_results"][-1])  # type: ignore[index]
        second_result["task_id"] = "REPAIR-001-002"
        second_result["route"]["invocation_id"] = "repair-002"  # type: ignore[index]
        second_result["evidence"]["output_ref"] = ".git/symphony/issue-3/workers/REPAIR-001-002.json"  # type: ignore[index]
        second_result["observed_at"] = "2026-09-22T00:02:00Z"
        artifact["worker_results"].append(second_result)  # type: ignore[index]

        second_route = deepcopy(artifact["route_records"][-1])  # type: ignore[index]
        second_route["task_id"] = "REPAIR-001-002"
        second_route["invocation_id"] = "repair-002"
        second_route["observed_at"] = "2026-09-22T00:02:00Z"
        artifact["route_records"].append(second_route)  # type: ignore[index]
        artifact["repairs"]["cycles"] = 2  # type: ignore[index]
        artifact["repairs"]["records"].append({  # type: ignore[index]
            "task_id": "REPAIR-001-002",
            "status": "accepted",
            "cycle": 2,
            "scope": {"include": ["WORKFLOW.md"], "exclude": []},
            "acceptance_ids": ["ACC-001"],
            "rerun_check_ids": ["focused-tests"],
            "failure_refs": ["focused-tests"],
            "resolution": "The second repair evidence was recorded.",
        })
        artifact["checkpoints"][0]["evidence"]["task_ids"].append("REPAIR-001-002")  # type: ignore[index]
        artifact["checkpoints"][0]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]
        artifact["checks"][0]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]
        artifact["review"]["observed_at"] = "2026-09-22T00:02:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_reused_acceptance_invocation_is_not_independent(self) -> None:
        artifact = self._artifact()
        artifact["review"]["invocation_id"] = "worker-001"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REVIEW_INVOCATION_NOT_INDEPENDENT", result.stdout)

    def test_review_must_follow_active_worker_results(self) -> None:
        artifact = self._artifact()
        artifact["worker_results"][0]["observed_at"] = "2026-09-22T00:01:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REVIEW_BEFORE_WORKERS", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_independent_implementation_scope_overlap_is_rejected(self) -> None:
        artifact = self._artifact()
        implementation = deepcopy(artifact["tasks"][1])  # type: ignore[index]
        implementation["task_id"] = "IMPLEMENT-002"
        implementation["dependencies"] = ["PLAN-001"]
        artifact["tasks"].append(implementation)  # type: ignore[index]
        worker_route = deepcopy(
            next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        )
        worker_route["task_id"] = "IMPLEMENT-002"
        worker_route["invocation_id"] = "worker-002"
        artifact["route_records"].append(worker_route)  # type: ignore[index]
        artifact["checkpoints"][0]["evidence"]["task_ids"].append("IMPLEMENT-002")  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_SCOPE_OVERLAP_IMPLEMENT-001_IMPLEMENT-002", result.stdout)

    def test_qwen_worker_route_is_checked_as_a_bounded_implementation_route(self) -> None:
        artifact = self._artifact()
        implementation = next(task for task in artifact["tasks"] if task["task_id"] == "IMPLEMENT-001")  # type: ignore[index]
        implementation["owner"]["role"] = "implementation-worker-qwen"  # type: ignore[index]
        implementation["owner"]["model"] = "qwen3.8-27b"  # type: ignore[index]
        implementation["owner"]["reasoning"] = "low"  # type: ignore[index]
        worker_route = next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        worker_route["role"] = "implementation-worker-qwen"  # type: ignore[index]
        worker_route["model"] = "qwen3.8-27b"  # type: ignore[index]
        worker_route["reasoning"] = "low"  # type: ignore[index]
        worker_result = artifact["worker_results"][0]  # type: ignore[index]
        worker_result["route"]["role"] = "implementation-worker-qwen"  # type: ignore[index]
        worker_result["route"]["model"] = "qwen3.8-27b"  # type: ignore[index]
        worker_result["route"]["reasoning"] = "low"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    def test_coordinator_fallback_route_is_explicit_when_worker_capacity_is_unavailable(self) -> None:
        artifact = self._artifact()
        implementation = next(task for task in artifact["tasks"] if task["task_id"] == "IMPLEMENT-001")  # type: ignore[index]
        implementation["owner"]["role"] = "primary-coordinator"  # type: ignore[index]
        implementation["owner"]["execution_mode"] = "coordinator-fallback"  # type: ignore[index]
        worker_route = next(route for route in artifact["route_records"] if route["role"] == "implementation-worker")  # type: ignore[index]
        worker_route["role"] = "primary-coordinator"
        worker_route["execution_mode"] = "coordinator-fallback"
        worker_result = artifact["worker_results"][0]  # type: ignore[index]
        worker_result["route"]["role"] = "primary-coordinator"  # type: ignore[index]
        worker_result["route"]["execution_mode"] = "coordinator-fallback"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    def test_coordinator_fallback_is_valid_for_a_repair_task(self) -> None:
        artifact = self._repair_artifact()
        repair_task = artifact["tasks"][-1]  # type: ignore[index]
        repair_task["owner"]["role"] = "primary-coordinator"  # type: ignore[index]
        repair_task["owner"]["execution_mode"] = "coordinator-fallback"  # type: ignore[index]
        repair_route = artifact["route_records"][-1]  # type: ignore[index]
        repair_route["role"] = "primary-coordinator"
        repair_route["execution_mode"] = "coordinator-fallback"
        repair_result = artifact["worker_results"][-1]  # type: ignore[index]
        repair_result["route"]["role"] = "primary-coordinator"  # type: ignore[index]
        repair_result["route"]["execution_mode"] = "coordinator-fallback"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    def test_planner_cannot_claim_the_qwen_route(self) -> None:
        artifact = self._artifact()
        planner_route = next(route for route in artifact["route_records"] if route["role"] == "planner")  # type: ignore[index]
        planner_route["model"] = "qwen3.8-27b"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ROUTE_2_ROUTE_INVALID", result.stdout)

    def test_boolean_exit_status_is_not_a_passing_exit_code(self) -> None:
        artifact = self._artifact()
        artifact["checks"][0]["exit_status"] = False  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_PASS_EXIT_CONTRADICTION", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_float_exit_status_is_not_a_passing_exit_code(self) -> None:
        artifact = self._artifact()
        artifact["checks"][0]["exit_status"] = 0.0  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_EXIT_STATUS_INVALID", result.stdout)

    def test_unsafe_scope_is_rejected(self) -> None:
        artifact = self._artifact()
        artifact["tasks"][1]["scope"]["include"] = ["../outside"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_2_SCOPE_INCLUDE_1_INVALID", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_scope_rejects_dot_segments_and_globs(self) -> None:
        for path in ("./WORKFLOW.md", "symphony/*.md"):
            with self.subTest(path=path):
                artifact = self._artifact()
                artifact["tasks"][1]["scope"]["include"] = [path]  # type: ignore[index]

                result = self._run(artifact)

                self.assertEqual(result.returncode, 2)
                self.assertIn("TASK_2_SCOPE_INCLUDE_1_INVALID", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_dependency_cycle_is_rejected(self) -> None:
        artifact = self._artifact()
        artifact["tasks"][1]["dependencies"] = ["IMPLEMENT-001"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_DEPENDENCY_CYCLE", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_check_requires_an_explicit_exit_status(self) -> None:
        artifact = self._artifact()
        del artifact["checks"][0]["exit_status"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_EXIT_STATUS_MISSING", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_check_command_must_match_the_recorded_check(self) -> None:
        artifact = self._artifact()
        artifact["checks"][1]["command"] += " && echo passed"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_2_COMMAND_INVALID", result.stdout)

    def test_validation_task_must_depend_on_implementation_tasks(self) -> None:
        artifact = self._artifact()
        artifact["tasks"][2]["dependencies"] = ["PLAN-001"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_VALIDATE-001_IMPLEMENTATION_DEPENDENCY_MISSING", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_full_checkpoint_requires_the_progress_route_identity(self) -> None:
        artifact = self._artifact()
        artifact["checkpoints"][0]["reviewer"]["role"] = "acceptance-reviewer"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_1_REVIEWER_INVALID", result.stdout)

    def test_checkpoint_requires_an_explicit_utc_timestamp(self) -> None:
        artifact = self._artifact()
        artifact["checkpoints"][0]["observed_at"] = "2026-09-22"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_1_TIMESTAMP_INVALID", result.stdout)

    def test_checkpoint_timestamp_is_required(self) -> None:
        artifact = self._artifact()
        artifact["checkpoints"][0]["observed_at"] = "not-a-timestamp"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_1_TIMESTAMP_INVALID", result.stdout)

    def test_checkpoint_findings_must_be_resolved_before_continue(self) -> None:
        artifact = self._artifact()
        artifact["checkpoints"][0]["evidence"]["findings"] = ["A finding remains open."]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_1_FINDINGS_UNRESOLVED", result.stdout)

    def test_redirect_checkpoint_requires_a_linked_resolution_task(self) -> None:
        artifact = self._artifact()
        checkpoint = artifact["checkpoints"][0]  # type: ignore[index]
        checkpoint["decision"] = "REDIRECT"
        checkpoint["required_action"] = "Repair the recorded finding."
        checkpoint["resolution"] = {
            "status": "resolved",
            "summary": "The repair completed.",
            "task_ids": [],
            "observed_at": "2026-09-22T00:01:00Z",
        }

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_1_REDIRECT_UNRESOLVED", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_light_checkpoint_requires_a_progress_route(self) -> None:
        artifact = self._artifact()
        artifact["path"] = "light"
        artifact["route_records"] = [
            route
            for route in artifact["route_records"]
            if route["role"] != "progress-orchestrator"
        ]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_PROGRESS_ROUTE_MISSING", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_progress_route_requires_a_correlated_checkpoint(self) -> None:
        artifact = self._artifact()
        artifact["checkpoints"] = []

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_PROGRESS_RESULT_PROGRESS-001_MISSING", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_checkpoint_cannot_precede_the_task_attempt(self) -> None:
        artifact = self._artifact()
        artifact["checkpoints"][0]["observed_at"] = "2026-09-21T23:59:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT_1_BEFORE_TASK", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_review_must_match_the_current_evidence_fingerprint(self) -> None:
        artifact = self._artifact()
        artifact["review"]["source_fingerprint"] = "c" * 64  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REVIEW_EVIDENCE_STALE", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_repair_cycle_count_requires_repair_records(self) -> None:
        artifact = self._artifact()
        artifact["repairs"]["cycles"] = 1  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_CYCLES_MISMATCH", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_repair_tasks_require_matching_repair_records(self) -> None:
        artifact = self._repair_artifact()
        artifact["repairs"]["records"] = []  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_TASK_RECORD_MISSING", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_repair_checks_and_review_must_follow_the_repair_attempt(self) -> None:
        artifact = self._repair_artifact()
        artifact["checks"][0]["observed_at"] = "2026-09-22T00:00:00Z"  # type: ignore[index]
        artifact["review"]["observed_at"] = "2026-09-22T00:00:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_CHECK_EVIDENCE_STALE", result.stdout)
        self.assertIn("REPAIR_REVIEW_EVIDENCE_STALE", result.stdout)

    def test_repair_checks_must_follow_repair_completion(self) -> None:
        artifact = self._repair_artifact()
        artifact["worker_results"][-1]["observed_at"] = "2026-09-22T00:05:00Z"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_CHECK_EVIDENCE_STALE", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_repair_must_rerun_a_named_failed_check(self) -> None:
        artifact = self._repair_artifact()
        artifact["repairs"]["records"][0]["failure_refs"] = ["pnpm-lint"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_AFFECTED_CHECK_NOT_RERUN", result.stdout)

    def test_repair_acceptance_ids_must_stay_within_the_predecessor(self) -> None:
        artifact = self._repair_artifact()
        artifact["tasks"][1]["acceptance_ids"] = ["ACC-001"]  # type: ignore[index]
        artifact["worker_results"][0]["acceptance_ids"] = ["ACC-001"]  # type: ignore[index]
        artifact["tasks"][-1]["acceptance_ids"] = ["ACC-001", "ACC-006"]  # type: ignore[index]
        artifact["worker_results"][-1]["acceptance_ids"] = ["ACC-001", "ACC-006"]  # type: ignore[index]
        artifact["repairs"]["records"][0]["acceptance_ids"] = ["ACC-001", "ACC-006"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_TASK_ACCEPTANCE_IDS_MISMATCH", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_repair_record_requires_an_implementation_owner(self) -> None:
        artifact = self._artifact()
        repair_task = dict(artifact["tasks"][0])  # type: ignore[index]
        repair_task["task_id"] = "REPAIR-001-001"
        repair_task["owner"] = {
            "role": "planner",
            "model": "gpt-6-astra",
            "reasoning": "high",
            "route_reason": "The planner owns task design.",
        }
        artifact["tasks"].append(repair_task)  # type: ignore[index]
        artifact["repairs"] = {
            "cycles": 1,
            "max_cycles": 2,
            "open_task_ids": [],
            "records": [
                {
                    "task_id": "REPAIR-001-001",
                    "status": "accepted",
                    "cycle": 1,
                    "scope": {"include": ["WORKFLOW.md"], "exclude": []},
                    "acceptance_ids": ["ACC-001"],
                    "rerun_check_ids": ["focused-tests"],
                    "resolution": "The repair evidence was recorded.",
                }
            ],
        }

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_OWNER_INVALID", result.stdout)

    def test_repair_failure_reference_must_name_a_check_or_finding(self) -> None:
        artifact = self._repair_artifact()
        artifact["repairs"]["records"][0]["failure_refs"] = ["missing-failure"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_1_FAILURE_REF_UNKNOWN", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_matched_drift_requires_the_same_file_set(self) -> None:
        artifact = self._artifact()
        artifact["drift"]["targets"]["installed"]["files"][0]["source_path"] = "other.md"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_INSTALLED_FILE_SET_INVALID", result.stdout)

    def test_generated_drift_report_matches_the_publication_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "installed"
            codex_home = root / "codex-home"
            (installed / "config").mkdir(parents=True)
            (codex_home / "agents").mkdir(parents=True)
            shutil.copy2(ROOT / "WORKFLOW.md", installed / "WORKFLOW.md")
            shutil.copytree(ROOT / "symphony-spark-container/config", installed / "config", dirs_exist_ok=True)
            shutil.copy2(ROOT / "symphony-spark-container/config/config.toml", codex_home / "config.toml")
            shutil.copytree(ROOT / "symphony-spark-container/config/agents", codex_home / "agents", dirs_exist_ok=True)
            shutil.copy2(ROOT / "symphony-spark-container/config/spark-qwen.config.toml", codex_home / "spark-qwen.config.toml")

            report_result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "symphony-spark-container/scripts/check-config.py"),
                    "compare",
                    "--workspace",
                    str(ROOT / "symphony-spark-container"),
                    "--workflow",
                    str(ROOT / "WORKFLOW.md"),
                    "--installed-root",
                    str(installed),
                    "--codex-home",
                    str(codex_home),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(report_result.returncode, 0)
        report = json.loads(report_result.stdout)
        artifact = self._artifact()
        artifact["drift"] = {
            "status": report["status"],
            "required_files": [file["path"] for file in report["source"]["files"]],
            "source_files": report["source"]["files"],
            "targets": report["targets"],
            "hash_algorithm": "sha256",
        }

        result = self._run(artifact)

        self.assertEqual(result.returncode, 0)

    def test_matched_drift_requires_equal_hashes(self) -> None:
        artifact = self._artifact()
        artifact["drift"]["targets"]["installed"]["files"][0]["sha256"] = "c" * 64  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_INSTALLED_MATCH_CONTRADICTION", result.stdout)

    def test_matched_drift_rejects_extra_target_files(self) -> None:
        artifact = self._artifact()
        artifact["drift"]["targets"]["installed"]["extra_files"] = ["stale.toml"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_INSTALLED_MATCH_CONTRADICTION", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_drift_missing_file_cannot_retain_a_hash(self) -> None:
        artifact = self._artifact()
        artifact["drift"]["targets"]["installed"]["files"][0]["status"] = "missing"  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_INSTALLED_1_STATUS_HASH_CONTRADICTION", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_repair_cycles_must_be_contiguous(self) -> None:
        artifact = self._repair_artifact()
        artifact["repairs"]["cycles"] = 2  # type: ignore[index]
        artifact["repairs"]["records"][0]["cycle"] = 2  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_CYCLES_MISMATCH", result.stdout)

    def test_each_mandatory_task_requires_route_evidence(self) -> None:
        artifact = self._artifact()
        artifact["route_records"] = [
            route
            for route in artifact["route_records"]
            if route["task_id"] != "VALIDATE-001"
        ]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ROUTE_TASK_VALIDATE-001_MISSING", result.stdout)

    def test_invalid_check_shape_returns_a_gate_error(self) -> None:
        artifact = self._artifact()
        artifact["checks"][0]["status"] = []  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_STATUS_INVALID", result.stdout)

    # https://github.com/starwaver/virtual-ai-character/issues/3
    def test_malformed_role_and_command_return_stable_gate_errors(self) -> None:
        artifact = self._artifact()
        artifact["route_records"][0]["role"] = []  # type: ignore[index]
        artifact["checks"][0]["command"] = []  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("ROUTE_1_ROLE_INVALID", result.stdout)
        self.assertIn("CHECK_1_COMMAND_INVALID", result.stdout)

    def test_published_artifact_requires_publication_evidence(self) -> None:
        artifact = self._artifact()
        artifact["published"] = True

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("PUBLICATION_EVIDENCE_MISSING", result.stdout)

    def test_published_artifact_requires_correlated_publication_metadata(self) -> None:
        artifact = self._artifact()
        artifact["published"] = True
        artifact["git"]["branch"] = "main"  # type: ignore[index]
        artifact["publication"] = {
            "branch": "main",
            "commit_sha": "not-a-commit",
            "pr_url": "https://example.com/pull/1",
            "published_at": "2026-09-22",
        }

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("PUBLICATION_BRANCH_INVALID", result.stdout)
        self.assertIn("PUBLICATION_COMMIT_INVALID", result.stdout)
        self.assertIn("PUBLICATION_PR_URL_INVALID", result.stdout)
        self.assertIn("PUBLICATION_TIMESTAMP_INVALID", result.stdout)

    def test_publication_timestamp_must_follow_review_evidence(self) -> None:
        artifact = self._artifact()
        artifact["published"] = True
        artifact["publication"] = {
            "branch": "symphony/issue-3",
            "commit_sha": "a" * 40,
            "pr_url": "https://github.com/starwaver/virtual-ai-character/pull/4",
            "published_at": "2026-09-21T23:59:00Z",
        }

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("PUBLICATION_EVIDENCE_STALE", result.stdout)

    def test_missing_acceptance_evidence_is_rejected(self) -> None:
        artifact = self._artifact()
        del artifact["acceptance"]["ACC-004"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ACC-004_MISSING", result.stdout)

    def test_contradictory_check_result_is_rejected(self) -> None:
        artifact = self._artifact()
        artifact["checks"][0]["exit_status"] = 1  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_1_PASS_EXIT_CONTRADICTION", result.stdout)

    def test_required_repository_check_is_rejected_when_missing(self) -> None:
        artifact = self._artifact()
        artifact["checks"] = [
            check for check in artifact["checks"] if check["check_id"] != "pnpm-lint"
        ]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECK_REQUIRED_pnpm-lint_MISSING", result.stdout)

    def test_task_records_are_required(self) -> None:
        artifact = self._artifact()
        del artifact["tasks"]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_RECORDS_MISSING", result.stdout)

    # https://github.com/moeru-ai/airi/issues/3
    def test_malformed_task_container_returns_a_gate_error(self) -> None:
        artifact = self._artifact()
        artifact["tasks"] = None

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("TASK_RECORDS_MISSING", result.stdout)

    def test_open_repair_is_rejected(self) -> None:
        artifact = self._artifact()
        artifact["repairs"]["open_task_ids"] = ["REPAIR-001"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("REPAIR_TASKS_OPEN", result.stdout)

    def test_unknown_drift_blocks_live_rollout(self) -> None:
        artifact = self._artifact()
        artifact["drift"]["status"] = "unrun"  # type: ignore[index]

        result = self._run(artifact, "--live-rollout")

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_NOT_MATCHED_FOR_LIVE_ROLLOUT", result.stdout)

    def test_matched_drift_requires_both_installation_targets(self) -> None:
        artifact = self._artifact()
        del artifact["drift"]["targets"]["codex_home"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_TARGETS_MISSING", result.stdout)

    def test_matched_drift_without_hash_lists_is_rejected(self) -> None:
        artifact = self._artifact()
        del artifact["drift"]["source_files"]  # type: ignore[index]

        result = self._run(artifact)

        self.assertEqual(result.returncode, 2)
        self.assertIn("DRIFT_SOURCE_FILE_SET_INVALID", result.stdout)

    def test_missing_artifact_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--artifact",
                    str(Path(directory) / "missing.json"),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
