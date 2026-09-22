#!/usr/bin/env python3
"""Reject incomplete or contradictory Symphony publication evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "symphony.publication-gate.v1"
REQUIRED_ACCEPTANCE_IDS = tuple(f"ACC-{number:03d}" for number in range(1, 7))
CHECK_STATUSES = {"passed", "failed", "blocked", "unrun"}
REQUIRED_CHECK_IDS = {
    "focused-tests",
    "route-check",
    "git-diff-check",
    "pnpm-typecheck",
    "pnpm-lint",
}
ROUTE_EXPECTATIONS = {
    "primary-coordinator": ("gpt-5.6-luna", "xhigh"),
    "planner": ("gpt-6-astra", "high"),
    "implementation-worker": ("gpt-5.6-luna", "xhigh"),
    "implementation-worker-qwen": ("qwen3.8-27b", "low"),
    "progress-orchestrator": ("gpt-6-astra", "high"),
    "acceptance-reviewer": ("gpt-6-astra", "high"),
}
TASK_ID_PATTERN = re.compile(r"^(?:PLAN|IMPLEMENT|PROGRESS|ACCEPT|VALIDATE)-[0-9]{3}$|^REPAIR-[0-9]+-[0-9]{3}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DISALLOWED_PATH_CHARS = set("*?[]{}")
REQUIRED_CHECK_COMMANDS = {
    "git-diff-check": {"git diff --check"},
    "pnpm-typecheck": {"pnpm typecheck"},
    "pnpm-lint": {"pnpm lint"},
    "route-check": {
        "python3 symphony-spark-container/scripts/check-config.py validate --workspace symphony-spark-container --workflow WORKFLOW.md",
        "python3 -B symphony-spark-container/scripts/check-config.py validate --workspace symphony-spark-container --workflow WORKFLOW.md",
    },
    "focused-tests": {
        "python3 -B symphony-spark-container/tests/check-config.test.py -v && python3 -B symphony-spark-container/tests/check-publication.test.py -v",
    },
}
DRIFT_REQUIRED_FILES = {
    "WORKFLOW.md",
    "config/config.toml",
    "config/agents/acceptance-reviewer.toml",
    "config/agents/implementation-worker-qwen.toml",
    "config/agents/implementation-worker.toml",
    "config/agents/planner.toml",
    "config/agents/progress-orchestrator.toml",
    "config/spark-qwen.config.toml",
}
IMPLEMENTATION_ROLES = {"implementation-worker", "implementation-worker-qwen"}
TASK_STATUSES = {"accepted"}
WORKER_RESULT_STATUSES = {"completed", "failed", "blocked", "scope_error"}


def _reason(reasons: list[str], code: str) -> None:
    """Add one stable reason code without copying artifact content to output."""

    if code not in reasons:
        reasons.append(code)


def _object(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _timestamp(value: object) -> datetime | None:
    if not _non_empty_string(value) or not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _valid_relative_path(value: object) -> bool:
    if not _non_empty_string(value) or not isinstance(value, str):
        return False
    if (
        "\\" in value
        or "\x00" in value
        or any(ord(character) < 32 for character in value)
        or any(character in DISALLOWED_PATH_CHARS for character in value)
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        return False
    parts = value.split("/")
    return not any(part in {"", ".", ".."} for part in parts)


def _validate_scope(scope: object, reasons: list[str], index: int) -> None:
    record = _object(scope)
    if record is None or not isinstance(record.get("include"), list) or not record["include"] or not isinstance(record.get("exclude"), list):
        _reason(reasons, f"TASK_{index}_SCOPE_INVALID")
        return

    for field in ("include", "exclude"):
        paths = record[field]
        for path_index, path in enumerate(paths, start=1):
            if not _valid_relative_path(path):
                _reason(reasons, f"TASK_{index}_SCOPE_{field.upper()}_{path_index}_INVALID")
        valid_paths = [path for path in paths if _valid_relative_path(path)]
        if len(valid_paths) != len(set(valid_paths)):
            _reason(reasons, f"TASK_{index}_SCOPE_{field.upper()}_DUPLICATE")

    includes = [path for path in record["include"] if _valid_relative_path(path)]
    excludes = [path for path in record["exclude"] if _valid_relative_path(path)]
    if any(_paths_overlap(include, exclude) for include in includes for exclude in excludes):
        _reason(reasons, f"TASK_{index}_SCOPE_INCLUDE_EXCLUDE_OVERLAP")


def _paths_overlap(left: str, right: str) -> bool:
    """Return whether two exact paths identify the same path or nested ownership."""

    left_parts = tuple(left.split("/"))
    right_parts = tuple(right.split("/"))
    shorter, longer = sorted((left_parts, right_parts), key=len)
    return longer[: len(shorter)] == shorter


def _validate_check(check: object, reasons: list[str], index: int) -> str | None:
    record = _object(check)
    if record is None:
        _reason(reasons, f"CHECK_{index}_MISSING")
        return None

    for field in ("check_id", "command", "working_directory", "status", "observed_at", "output_ref", "result_summary"):
        if not _non_empty_string(record.get(field)):
            _reason(reasons, f"CHECK_{index}_{field.upper()}_MISSING")
    if "exit_status" not in record:
        _reason(reasons, f"CHECK_{index}_EXIT_STATUS_MISSING")

    check_id = record.get("check_id") if isinstance(record.get("check_id"), str) else None
    status = record.get("status")
    exit_status = record.get("exit_status")
    if not isinstance(status, str) or status not in CHECK_STATUSES:
        _reason(reasons, f"CHECK_{index}_STATUS_INVALID")
        return check_id

    strict_integer_exit = isinstance(exit_status, int) and not isinstance(exit_status, bool)
    if status in {"passed", "failed"} and not strict_integer_exit:
        _reason(reasons, f"CHECK_{index}_EXIT_STATUS_INVALID")
    if status == "passed" and (not strict_integer_exit or exit_status != 0):
        _reason(reasons, f"CHECK_{index}_PASS_EXIT_CONTRADICTION")
    elif status == "failed" and (not strict_integer_exit or exit_status == 0):
        _reason(reasons, f"CHECK_{index}_FAIL_EXIT_CONTRADICTION")
    elif status in {"blocked", "unrun"}:
        if exit_status is not None:
            _reason(reasons, f"CHECK_{index}_INCOMPLETE_EXIT_STATUS")
        if not _non_empty_string(record.get("required_action")):
            _reason(reasons, f"CHECK_{index}_REQUIRED_ACTION_MISSING")

    if status != "passed":
        _reason(reasons, f"CHECK_{index}_NOT_PASSED")

    command = record.get("command")
    if isinstance(check_id, str) and check_id in REQUIRED_CHECK_COMMANDS and (
        not isinstance(command, str) or command not in REQUIRED_CHECK_COMMANDS[check_id]
    ):
        _reason(reasons, f"CHECK_{index}_COMMAND_INVALID")
    if record.get("working_directory") != ".":
        _reason(reasons, f"CHECK_{index}_WORKING_DIRECTORY_INVALID")
    if _timestamp(record.get("observed_at")) is None:
        _reason(reasons, f"CHECK_{index}_TIMESTAMP_INVALID")
    if _non_empty_string(record.get("output_ref")) and not _valid_relative_path(record["output_ref"]):
        _reason(reasons, f"CHECK_{index}_OUTPUT_REF_INVALID")

    return check_id


def _validate_task_records(record: dict[str, Any], reasons: list[str]) -> set[str]:
    tasks = record.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        _reason(reasons, "TASK_RECORDS_MISSING")
        return set()

    task_ids: set[str] = set()
    dependencies: dict[str, list[str]] = {}
    task_records: dict[str, dict[str, Any]] = {}
    plan_id = record.get("plan_id")

    for index, task in enumerate(tasks, start=1):
        task_record = _object(task)
        if task_record is None:
            _reason(reasons, f"TASK_{index}_MISSING")
            continue

        task_id = task_record.get("task_id")
        if not _non_empty_string(task_id) or not isinstance(task_id, str) or task_id in task_ids or not TASK_ID_PATTERN.fullmatch(task_id):
            _reason(reasons, f"TASK_{index}_ID_INVALID")
        elif isinstance(task_id, str):
            task_ids.add(task_id)
            task_records[task_id] = task_record

        if task_record.get("plan_id") != plan_id:
            _reason(reasons, f"TASK_{index}_PLAN_ID_MISMATCH")
        if task_record.get("status") not in TASK_STATUSES:
            _reason(reasons, f"TASK_{index}_NOT_ACCEPTED")
        dependencies_for_task = task_record.get("dependencies")
        if not isinstance(dependencies_for_task, list) or any(
            not _non_empty_string(item)
            or not isinstance(item, str)
            or TASK_ID_PATTERN.fullmatch(item) is None
            for item in dependencies_for_task
        ):
            _reason(reasons, f"TASK_{index}_DEPENDENCIES_INVALID")
        elif isinstance(task_id, str):
            if len(dependencies_for_task) != len(set(dependencies_for_task)):
                _reason(reasons, f"TASK_{index}_DEPENDENCIES_DUPLICATE")
            dependencies[task_id] = list(dependencies_for_task)
        acceptance_ids = task_record.get("acceptance_ids")
        if not isinstance(acceptance_ids, list) or not acceptance_ids or any(item not in REQUIRED_ACCEPTANCE_IDS for item in acceptance_ids):
            _reason(reasons, f"TASK_{index}_ACCEPTANCE_IDS_INVALID")
        if not _positive_integer(task_record.get("attempt")):
            _reason(reasons, f"TASK_{index}_ATTEMPT_INVALID")

        owner = _object(task_record.get("owner"))
        owner_role = owner.get("role") if owner is not None else None
        if (
            owner is None
            or not isinstance(owner_role, str)
            or owner_role not in ROUTE_EXPECTATIONS
            or not _non_empty_string(owner.get("model"))
            or not _non_empty_string(owner.get("reasoning"))
            or not _non_empty_string(owner.get("route_reason"))
        ):
            _reason(reasons, f"TASK_{index}_OWNER_INVALID")
        elif isinstance(task_id, str) and isinstance(owner_role, str):
            expected_model, expected_reasoning = ROUTE_EXPECTATIONS[owner_role]
            if owner.get("model") != expected_model or owner.get("reasoning") != expected_reasoning:
                _reason(reasons, f"TASK_{index}_OWNER_ROUTE_INVALID")
            expected_roles = {
                "PLAN-001": {"planner"},
                "PROGRESS-": {"progress-orchestrator"},
                "ACCEPT-": {"acceptance-reviewer"},
                "VALIDATE-": {"primary-coordinator"},
            }
            required_roles = next(
                (roles for prefix, roles in expected_roles.items() if task_id == prefix or task_id.startswith(prefix)),
                {"implementation-worker", "implementation-worker-qwen"},
            )
            if owner_role not in required_roles:
                _reason(reasons, f"TASK_{index}_OWNER_ROLE_INVALID")
        _validate_scope(task_record.get("scope"), reasons, index)

        evidence = _object(task_record.get("evidence"))
        if evidence is None or not _non_empty_string(evidence.get("summary")) or evidence.get("attempt") != task_record.get("attempt"):
            _reason(reasons, f"TASK_{index}_EVIDENCE_MISSING")
        if _timestamp(task_record.get("attempt_started_at")) is None:
            _reason(reasons, f"TASK_{index}_ATTEMPT_START_MISSING")

    worker_scopes: dict[str, set[str]] = {}
    for task_id, task in task_records.items():
        owner = _object(task.get("owner"))
        scope = _object(task.get("scope"))
        includes = scope.get("include") if scope is not None else None
        if owner is not None and owner.get("role") in {"implementation-worker", "implementation-worker-qwen"} and isinstance(includes, list):
            worker_scopes[task_id] = {path for path in includes if isinstance(path, str)}

    def depends_on(task_id: str, dependency_id: str) -> bool:
        pending = list(dependencies.get(task_id, []))
        visited_dependencies: set[str] = set()
        while pending:
            candidate = pending.pop()
            if candidate in visited_dependencies:
                continue
            if candidate == dependency_id:
                return True
            visited_dependencies.add(candidate)
            pending.extend(dependencies.get(candidate, []))
        return False

    worker_ids = list(worker_scopes)
    for index, task_id in enumerate(worker_ids):
        for previous_id in worker_ids[:index]:
            if not any(
                _paths_overlap(path, previous_path)
                for path in worker_scopes[task_id]
                for previous_path in worker_scopes[previous_id]
            ):
                continue

            repair_id, other_id = (
                (task_id, previous_id)
                if task_id.startswith("REPAIR-")
                else (previous_id, task_id)
            )
            if repair_id.startswith("REPAIR-") and depends_on(repair_id, other_id):
                continue
            _reason(reasons, f"TASK_SCOPE_OVERLAP_{previous_id}_{task_id}")

    if "PLAN-001" not in task_ids:
        _reason(reasons, "PLAN_TASK_MISSING")
    if not any(task_id.startswith("IMPLEMENT-") for task_id in task_ids):
        _reason(reasons, "IMPLEMENTATION_TASK_MISSING")
    if dependencies.get("PLAN-001"):
        _reason(reasons, "PLAN_DEPENDENCIES_NOT_EMPTY")

    for task_id, task_dependencies in dependencies.items():
        for dependency in task_dependencies:
            if dependency not in task_ids:
                _reason(reasons, f"TASK_{task_id}_DEPENDENCY_MISSING")

    for task_id, task in task_records.items():
        owner = _object(task.get("owner"))
        owner_role = owner.get("role") if owner is not None else None
        if task_id.startswith("IMPLEMENT-") and not depends_on(task_id, "PLAN-001"):
            _reason(reasons, f"TASK_{task_id}_PLANNER_DEPENDENCY_MISSING")
        if task_id.startswith("REPAIR-"):
            direct_dependencies = dependencies.get(task_id, [])
            if not direct_dependencies or not any(
                dependency.startswith(("IMPLEMENT-", "REPAIR-"))
                and task_records.get(dependency, {}).get("status") in TASK_STATUSES
                for dependency in direct_dependencies
            ):
                _reason(reasons, f"TASK_{task_id}_REPAIR_OWNER_DEPENDENCY_MISSING")
        if isinstance(owner_role, str) and owner_role in IMPLEMENTATION_ROLES and task_id.startswith(("IMPLEMENT-", "REPAIR-")):
            scope = _object(task.get("scope"))
            if scope is not None and isinstance(scope.get("include"), list) and not scope["include"]:
                _reason(reasons, f"TASK_{task_id}_SCOPE_EMPTY")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            _reason(reasons, "TASK_DEPENDENCY_CYCLE")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies.get(task_id, []):
            if dependency in task_ids:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_ids:
        visit(task_id)
    return task_ids


def _validate_worker_results(record: dict[str, Any], reasons: list[str]) -> None:
    tasks = record.get("tasks")
    task_records = {
        task.get("task_id"): task
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    } if isinstance(tasks, list) else {}
    worker_tasks = {
        task_id: task
        for task_id, task in task_records.items()
        if task_id.startswith(("IMPLEMENT-", "REPAIR-"))
    }
    results = record.get("worker_results")
    if not isinstance(results, list) or not results:
        _reason(reasons, "WORKER_RESULTS_MISSING")
        return

    changed_files = record.get("changed_files")
    if not isinstance(changed_files, list) or not changed_files:
        _reason(reasons, "CHANGED_FILES_MISSING")
        changed_files = []
    valid_changed_files = {
        path for path in changed_files if _valid_relative_path(path)
    }
    if len(valid_changed_files) != len(changed_files):
        _reason(reasons, "CHANGED_FILES_INVALID")

    results_by_attempt: dict[tuple[str, int], dict[str, Any]] = {}
    for index, result in enumerate(results, start=1):
        result_record = _object(result)
        if result_record is None:
            _reason(reasons, f"WORKER_RESULT_{index}_INVALID")
            continue
        if result_record.get("schema_version") != "symphony.worker-result.v1":
            _reason(reasons, f"WORKER_RESULT_{index}_SCHEMA_INVALID")
        task_id = result_record.get("task_id")
        if not isinstance(task_id, str) or task_id not in worker_tasks:
            _reason(reasons, f"WORKER_RESULT_{index}_TASK_INVALID")
            continue
        task = worker_tasks[task_id]
        if result_record.get("issue_id") != record.get("issue_id"):
            _reason(reasons, f"WORKER_RESULT_{index}_ISSUE_MISMATCH")
        if result_record.get("plan_id") != record.get("plan_id"):
            _reason(reasons, f"WORKER_RESULT_{index}_PLAN_MISMATCH")
        result_attempt = result_record.get("attempt")
        active_attempt = task.get("attempt")
        if not _positive_integer(result_attempt):
            _reason(reasons, f"WORKER_RESULT_{index}_ATTEMPT_INVALID")
        elif not _positive_integer(active_attempt) or result_attempt > active_attempt:
            _reason(reasons, f"WORKER_RESULT_{index}_ATTEMPT_MISMATCH")
        elif (task_id, result_attempt) in results_by_attempt:
            _reason(reasons, f"WORKER_RESULT_{index}_DUPLICATE")
        else:
            results_by_attempt[(task_id, result_attempt)] = result_record
        result_acceptance_ids = result_record.get("acceptance_ids")
        task_acceptance_ids = task.get("acceptance_ids")
        if not isinstance(result_acceptance_ids, list) or any(
            not isinstance(acceptance_id, str) or acceptance_id not in REQUIRED_ACCEPTANCE_IDS
            for acceptance_id in result_acceptance_ids
        ):
            _reason(reasons, f"WORKER_RESULT_{index}_ACCEPTANCE_IDS_INVALID")
        elif isinstance(task_acceptance_ids, list) and set(result_acceptance_ids) != set(task_acceptance_ids):
            _reason(reasons, f"WORKER_RESULT_{index}_ACCEPTANCE_IDS_MISMATCH")
        result_status = result_record.get("status")
        is_active_attempt = result_attempt == active_attempt
        if result_status not in WORKER_RESULT_STATUSES:
            _reason(reasons, f"WORKER_RESULT_{index}_STATUS_INVALID")
        elif result_status != "completed" and is_active_attempt:
            _reason(reasons, f"WORKER_RESULT_{index}_NOT_COMPLETED")
        if _timestamp(result_record.get("observed_at")) is None:
            _reason(reasons, f"WORKER_RESULT_{index}_TIMESTAMP_INVALID")
        started_at = _timestamp(task.get("attempt_started_at"))
        observed_at = _timestamp(result_record.get("observed_at"))
        if is_active_attempt and started_at is not None and observed_at is not None and observed_at < started_at:
            _reason(reasons, f"WORKER_RESULT_{index}_STALE")

        result_files = result_record.get("changed_files")
        if not isinstance(result_files, list) or any(not _valid_relative_path(path) for path in result_files):
            _reason(reasons, f"WORKER_RESULT_{index}_CHANGED_FILES_INVALID")
            result_files = []
        task_evidence = _object(task.get("evidence"))
        task_evidence_files = task_evidence.get("changed_files") if task_evidence is not None else None
        if not isinstance(task_evidence_files, list) or any(not _valid_relative_path(path) for path in task_evidence_files):
            _reason(reasons, f"WORKER_RESULT_{index}_EVIDENCE_FILES_INVALID")
        elif set(result_files) != set(task_evidence_files):
            _reason(reasons, f"WORKER_RESULT_{index}_EVIDENCE_FILES_MISMATCH")
        if is_active_attempt and not set(result_files).issubset(valid_changed_files):
            _reason(reasons, f"WORKER_RESULT_{index}_FILES_NOT_IN_DIFF")

        route = _object(result_record.get("route"))
        owner = _object(task.get("owner"))
        if route is None or owner is None:
            _reason(reasons, f"WORKER_RESULT_{index}_ROUTE_MISSING")
        else:
            for field in ("role", "model", "reasoning", "route_reason", "invocation_id"):
                if not _non_empty_string(route.get(field)):
                    _reason(reasons, f"WORKER_RESULT_{index}_ROUTE_{field.upper()}_MISSING")
            if route.get("role") != owner.get("role") or route.get("model") != owner.get("model") or route.get("reasoning") != owner.get("reasoning"):
                _reason(reasons, f"WORKER_RESULT_{index}_ROUTE_MISMATCH")
            route_records = record.get("route_records")
            matching_route = any(
                isinstance(route_record, dict)
                and route_record.get("task_id") == task_id
                and route_record.get("invocation_id") == route.get("invocation_id")
                for route_record in route_records
            ) if isinstance(route_records, list) else False
            if not matching_route:
                _reason(reasons, f"WORKER_RESULT_{index}_ROUTE_NOT_RECORDED")

        evidence = _object(result_record.get("evidence"))
        if evidence is None or not _non_empty_string(evidence.get("summary")) or not _valid_relative_path(evidence.get("output_ref")):
            _reason(reasons, f"WORKER_RESULT_{index}_EVIDENCE_INVALID")
        unfinished_work = result_record.get("unfinished_work")
        if is_active_attempt and (not isinstance(unfinished_work, list) or unfinished_work):
            _reason(reasons, f"WORKER_RESULT_{index}_UNFINISHED")
        if is_active_attempt and result_record.get("scope_error") not in (None, ""):
            _reason(reasons, f"WORKER_RESULT_{index}_SCOPE_ERROR")
        result_checks = result_record.get("checks")
        if is_active_attempt and (not isinstance(result_checks, list) or not result_checks):
            _reason(reasons, f"WORKER_RESULT_{index}_CHECKS_MISSING")
        elif is_active_attempt and isinstance(result_checks, list):
            for check_index, check in enumerate(result_checks, start=1):
                check_record = _object(check)
                if check_record is None or not _non_empty_string(check_record.get("check_id")) or check_record.get("status") != "passed" or check_record.get("exit_status") != 0 or not _non_empty_string(check_record.get("command")):
                    _reason(reasons, f"WORKER_RESULT_{index}_CHECK_{check_index}_INVALID")
                    continue
                top_level_check = next(
                    (
                        top_level
                        for top_level in record.get("checks", [])
                        if isinstance(top_level, dict) and top_level.get("check_id") == check_record.get("check_id")
                    ),
                    None,
                )
                if top_level_check is None or any(
                    top_level_check.get(field) != check_record.get(field)
                    for field in ("command", "status", "exit_status")
                ):
                    _reason(reasons, f"WORKER_RESULT_{index}_CHECK_{check_index}_MISMATCH")

    for task_id, task in worker_tasks.items():
        active_attempt = task.get("attempt")
        active_result = results_by_attempt.get((task_id, active_attempt)) if isinstance(active_attempt, int) and not isinstance(active_attempt, bool) else None
        if active_result is None or active_result.get("status") != "completed":
            _reason(reasons, f"WORKER_RESULT_{task_id}_MISSING")

    for path in valid_changed_files:
        owned = False
        for task in worker_tasks.values():
            scope = _object(task.get("scope"))
            includes = scope.get("include") if scope is not None else None
            excludes = scope.get("exclude") if scope is not None else None
            if isinstance(includes, list) and isinstance(excludes, list) and any(
                isinstance(include, str) and _paths_overlap(path, include)
                and not any(isinstance(exclude, str) and _paths_overlap(path, exclude) for exclude in excludes)
                for include in includes
            ):
                owned = True
                break
        if not owned:
            _reason(reasons, "CHANGED_FILE_OUTSIDE_OWNERSHIP")


def _validate_route_records(record: dict[str, Any], task_ids: set[str], reasons: list[str]) -> None:
    routes = record.get("route_records")
    if not isinstance(routes, list) or not routes:
        _reason(reasons, "ROUTE_RECORDS_MISSING")
        return

    path = record.get("path")
    observed_roles: set[str] = set()
    observed_keys: set[tuple[str, str, str]] = set()
    observed_invocations: set[str] = set()
    implementation_tasks: set[str] = set()
    tasks = record.get("tasks")
    task_records = {
        task.get("task_id"): task
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    } if isinstance(tasks, list) else {}
    for index, route in enumerate(routes, start=1):
        route_record = _object(route)
        if route_record is None:
            _reason(reasons, f"ROUTE_{index}_MISSING")
            continue
        role = route_record.get("role")
        task_id = route_record.get("task_id")
        invocation_id = route_record.get("invocation_id")
        key = (
            (role, task_id, invocation_id)
            if isinstance(role, str) and isinstance(task_id, str) and isinstance(invocation_id, str)
            else ("", "", "")
        )
        if key in observed_keys:
            _reason(reasons, f"ROUTE_{index}_DUPLICATE")
        observed_keys.add(key)
        if not isinstance(role, str) or role not in ROUTE_EXPECTATIONS:
            _reason(reasons, f"ROUTE_{index}_ROLE_INVALID")
            continue
        observed_roles.add(role)
        expected_model, expected_reasoning = ROUTE_EXPECTATIONS[role]
        if route_record.get("model") != expected_model or route_record.get("reasoning") != expected_reasoning:
            _reason(reasons, f"ROUTE_{index}_ROUTE_INVALID")
        if not isinstance(route_record.get("status"), str) or route_record.get("status") not in {"returned", "verified", "accepted"}:
            _reason(reasons, f"ROUTE_{index}_STATUS_INVALID")
        for field in ("task_id", "route_reason", "observed_at", "invocation_id"):
            if not _non_empty_string(route_record.get(field)):
                _reason(reasons, f"ROUTE_{index}_{field.upper()}_MISSING")
        if isinstance(invocation_id, str):
            if invocation_id in observed_invocations:
                _reason(reasons, f"ROUTE_{index}_INVOCATION_DUPLICATE")
            observed_invocations.add(invocation_id)
        if _timestamp(route_record.get("observed_at")) is None:
            _reason(reasons, f"ROUTE_{index}_TIMESTAMP_INVALID")
        if isinstance(task_id, str) and TASK_ID_PATTERN.fullmatch(task_id) is None:
            _reason(reasons, f"ROUTE_{index}_TASK_ID_INVALID")
        if not isinstance(task_id, str) or task_id not in task_ids:
            _reason(reasons, f"ROUTE_{index}_TASK_MISSING")

        if role == "planner" and task_id != "PLAN-001":
            _reason(reasons, f"ROUTE_{index}_TASK_ID_INVALID")
        elif role == "primary-coordinator" and task_id != "VALIDATE-001":
            _reason(reasons, f"ROUTE_{index}_TASK_ID_INVALID")
        elif role == "progress-orchestrator" and (not isinstance(task_id, str) or not task_id.startswith("PROGRESS-")):
            _reason(reasons, f"ROUTE_{index}_TASK_ID_INVALID")
        elif role == "acceptance-reviewer" and task_id != "ACCEPT-001":
            _reason(reasons, f"ROUTE_{index}_TASK_ID_INVALID")
        elif role in {"implementation-worker", "implementation-worker-qwen"}:
            if not isinstance(task_id, str) or task_id not in task_ids or not task_id.startswith(("IMPLEMENT-", "REPAIR-")):
                _reason(reasons, f"ROUTE_{index}_TASK_ID_INVALID")
            else:
                implementation_tasks.add(task_id)
                task = task_records.get(task_id)
                owner = task.get("owner") if isinstance(task, dict) else None
                if not isinstance(owner, dict) or owner.get("role") != role:
                    _reason(reasons, f"ROUTE_{index}_TASK_OWNER_MISMATCH")

    required_roles = {"primary-coordinator", "planner", "acceptance-reviewer"}
    if path == "full":
        required_roles.add("progress-orchestrator")
    for role in required_roles:
        if role not in observed_roles:
            _reason(reasons, f"ROUTE_{role}_MISSING")
    tasks = record.get("tasks")
    expected_implementation_tasks = {
        task_id
        for task_id, task in ((item.get("task_id"), item) for item in tasks if isinstance(item, dict))
        if isinstance(task_id, str) and task_id.startswith(("IMPLEMENT-", "REPAIR-")) and isinstance(task.get("owner"), dict) and task["owner"].get("role") in {"implementation-worker", "implementation-worker-qwen"}
    } if isinstance(tasks, list) else set()
    if expected_implementation_tasks - implementation_tasks:
        _reason(reasons, "IMPLEMENTATION_ROUTE_INCOMPLETE")
    if not implementation_tasks:
        _reason(reasons, "IMPLEMENTATION_ROUTE_MISSING")


def _validate_checkpoints(record: dict[str, Any], task_ids: set[str], reasons: list[str]) -> None:
    path = record.get("path")
    if path not in {"light", "full"}:
        _reason(reasons, "TASK_PATH_INVALID")
        return
    checkpoints = record.get("checkpoints")
    if not isinstance(checkpoints, list):
        _reason(reasons, "CHECKPOINTS_INVALID")
        return
    if path == "full" and not checkpoints:
        _reason(reasons, "CHECKPOINTS_MISSING")

    routes = record.get("route_records")
    progress_route_ids = {
        route.get("task_id")
        for route in routes if isinstance(route, dict)
        if isinstance(route, dict) and route.get("role") == "progress-orchestrator" and isinstance(route.get("task_id"), str)
    } if isinstance(routes, list) else set()
    if path == "light" and checkpoints and not progress_route_ids:
        _reason(reasons, "CHECKPOINT_PROGRESS_ROUTE_MISSING")

    checkpoint_ids: set[str] = set()
    for index, checkpoint in enumerate(checkpoints, start=1):
        checkpoint_record = _object(checkpoint)
        if checkpoint_record is None:
            _reason(reasons, f"CHECKPOINT_{index}_MISSING")
            continue
        for field in ("checkpoint_id", "plan_id", "trigger", "worker_wave", "reviewer", "evidence", "decision", "observed_at"):
            if field not in checkpoint_record:
                _reason(reasons, f"CHECKPOINT_{index}_{field.upper()}_MISSING")
        checkpoint_id = checkpoint_record.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or TASK_ID_PATTERN.fullmatch(checkpoint_id) is None or not checkpoint_id.startswith("PROGRESS-"):
            _reason(reasons, f"CHECKPOINT_{index}_ID_INVALID")
        elif checkpoint_id in checkpoint_ids:
            _reason(reasons, f"CHECKPOINT_{index}_DUPLICATE")
        elif progress_route_ids and checkpoint_id not in progress_route_ids:
            _reason(reasons, f"CHECKPOINT_{index}_ROUTE_MISSING")
        if isinstance(checkpoint_id, str):
            checkpoint_ids.add(checkpoint_id)
        if checkpoint_record.get("plan_id") != record.get("plan_id"):
            _reason(reasons, f"CHECKPOINT_{index}_PLAN_ID_INVALID")
        if not _non_empty_string(checkpoint_record.get("trigger")):
            _reason(reasons, f"CHECKPOINT_{index}_TRIGGER_INVALID")
        if not _positive_integer(checkpoint_record.get("worker_wave")):
            _reason(reasons, f"CHECKPOINT_{index}_WORKER_WAVE_INVALID")
        reviewer = _object(checkpoint_record.get("reviewer"))
        if (
            reviewer is None
            or reviewer.get("role") != "progress-orchestrator"
            or reviewer.get("model") != ROUTE_EXPECTATIONS["progress-orchestrator"][0]
            or reviewer.get("reasoning") != ROUTE_EXPECTATIONS["progress-orchestrator"][1]
        ):
            _reason(reasons, f"CHECKPOINT_{index}_REVIEWER_INVALID")
        evidence = _object(checkpoint_record.get("evidence"))
        if evidence is None:
            _reason(reasons, f"CHECKPOINT_{index}_EVIDENCE_INVALID")
        else:
            for field in ("task_ids", "files", "checks", "findings"):
                if not isinstance(evidence.get(field), list):
                    _reason(reasons, f"CHECKPOINT_{index}_EVIDENCE_{field.upper()}_INVALID")
            evidence_task_ids = evidence.get("task_ids")
            if isinstance(evidence_task_ids, list) and any(
                not isinstance(task_id, str) or task_id not in task_ids
                for task_id in evidence_task_ids
            ):
                _reason(reasons, f"CHECKPOINT_{index}_EVIDENCE_TASK_ID_INVALID")
            evidence_files = evidence.get("files")
            if isinstance(evidence_files, list):
                for file_path in evidence_files:
                    if not _valid_relative_path(file_path):
                        _reason(reasons, f"CHECKPOINT_{index}_EVIDENCE_FILE_INVALID")
        if checkpoint_record.get("decision") == "CONTINUE":
            continue
        if checkpoint_record.get("decision") == "REDIRECT":
            if not _non_empty_string(checkpoint_record.get("required_action")):
                _reason(reasons, f"CHECKPOINT_{index}_REDIRECT_UNRESOLVED")
            resolution = _object(checkpoint_record.get("resolution"))
            if resolution is None or resolution.get("status") != "resolved" or not _non_empty_string(resolution.get("summary")):
                _reason(reasons, f"CHECKPOINT_{index}_REDIRECT_UNRESOLVED")
            continue
        if checkpoint_record.get("decision") == "BLOCKED" and not _non_empty_string(checkpoint_record.get("required_action")):
            _reason(reasons, f"CHECKPOINT_{index}_REQUIRED_ACTION_MISSING")
        _reason(reasons, f"CHECKPOINT_{index}_NOT_CONTINUE")


def _validate_review(record: dict[str, Any], reasons: list[str]) -> None:
    review = _object(record.get("review"))
    if review is None:
        _reason(reasons, "REVIEW_MISSING")
        return
    if review.get("role") != "acceptance-reviewer":
        _reason(reasons, "REVIEW_ROLE_INVALID")
    if review.get("model") != "gpt-6-astra" or review.get("reasoning") != "high":
        _reason(reasons, "REVIEW_ROUTE_INVALID")
    if review.get("verdict") != "ACCEPT":
        _reason(reasons, "REVIEW_NOT_ACCEPTED")
    if not _non_empty_string(review.get("evidence_revision")) or not _non_empty_string(review.get("source_fingerprint")):
        _reason(reasons, "REVIEW_EVIDENCE_MISSING")
    if _non_empty_string(review.get("source_fingerprint")) and not SHA256_PATTERN.fullmatch(review["source_fingerprint"]):
        _reason(reasons, "REVIEW_FINGERPRINT_INVALID")
    if review.get("evidence_revision") != record.get("evidence_revision") or review.get("source_fingerprint") != record.get("source_fingerprint"):
        _reason(reasons, "REVIEW_EVIDENCE_STALE")
    for field in ("review_id", "invocation_id", "observed_at"):
        if not _non_empty_string(review.get(field)):
            _reason(reasons, f"REVIEW_{field.upper()}_MISSING")

    route_records = record.get("route_records")
    acceptance_invocations = {
        route.get("invocation_id")
        for route in route_records
        if isinstance(route, dict) and route.get("role") == "acceptance-reviewer" and isinstance(route.get("invocation_id"), str)
    } if isinstance(route_records, list) else set()
    review_invocation = review.get("invocation_id")
    if not isinstance(review_invocation, str) or review_invocation not in acceptance_invocations:
        _reason(reasons, "REVIEW_INVOCATION_NOT_RECORDED")
    worker_invocations = {
        route.get("invocation_id")
        for route in route_records
        if isinstance(route, dict) and route.get("role") != "acceptance-reviewer" and isinstance(route.get("invocation_id"), str)
    } if isinstance(route_records, list) else set()
    if isinstance(review_invocation, str) and review_invocation in worker_invocations:
        _reason(reasons, "REVIEW_INVOCATION_NOT_INDEPENDENT")

    review_observed_at = _timestamp(review.get("observed_at"))
    if review_observed_at is None:
        _reason(reasons, "REVIEW_TIMESTAMP_INVALID")
    checks = record.get("checks")
    if review_observed_at is not None and isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            check_observed_at = _timestamp(check.get("observed_at"))
            if check_observed_at is not None and review_observed_at < check_observed_at:
                _reason(reasons, "REVIEW_BEFORE_CHECKS")
                break

    findings = review.get("findings")
    if not isinstance(findings, list):
        _reason(reasons, "REVIEW_FINDINGS_INVALID")
        return
    for index, finding in enumerate(findings, start=1):
        finding_record = _object(finding)
        if (
            finding_record is None
            or not _non_empty_string(finding_record.get("finding_id"))
            or finding_record.get("status") not in {"resolved", "closed"}
            or not _non_empty_string(finding_record.get("resolution"))
        ):
            _reason(reasons, f"REVIEW_FINDING_{index}_OPEN")


def _validate_repairs(record: dict[str, Any], task_ids: set[str], checks: dict[str, dict[str, Any]], reasons: list[str]) -> None:
    repair_task_ids_in_tasks = {
        task_id for task_id in task_ids if task_id.startswith("REPAIR-")
    }
    repairs = _object(record.get("repairs"))
    if repairs is None:
        if repair_task_ids_in_tasks:
            _reason(reasons, "REPAIR_TASK_RECORD_MISSING")
        _reason(reasons, "REPAIRS_MISSING")
        return
    cycles = repairs.get("cycles")
    max_cycles = repairs.get("max_cycles")
    if not isinstance(cycles, int) or isinstance(cycles, bool) or not isinstance(max_cycles, int) or isinstance(max_cycles, bool) or cycles < 0 or max_cycles != 2 or cycles > max_cycles:
        _reason(reasons, "REPAIR_CYCLE_LIMIT")
    if not isinstance(repairs.get("open_task_ids"), list) or repairs.get("open_task_ids") != []:
        _reason(reasons, "REPAIR_TASKS_OPEN")
    records = repairs.get("records")
    if not isinstance(records, list):
        if repair_task_ids_in_tasks:
            _reason(reasons, "REPAIR_TASK_RECORD_MISSING")
        _reason(reasons, "REPAIR_RECORDS_INVALID")
        return
    if records and (not isinstance(cycles, int) or isinstance(cycles, bool) or cycles == 0):
        _reason(reasons, "REPAIR_CYCLES_MISMATCH")
    if not records and isinstance(cycles, int) and not isinstance(cycles, bool) and cycles > 0:
        _reason(reasons, "REPAIR_CYCLES_MISMATCH")

    tasks = record.get("tasks")
    task_records = {
        task.get("task_id"): task
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    } if isinstance(tasks, list) else {}
    dependencies = {
        task_id: task.get("dependencies", [])
        for task_id, task in task_records.items()
        if isinstance(task.get("dependencies"), list)
    }
    repair_task_ids: set[str] = set()
    accepted_repair_task_ids: set[str] = set()
    repair_starts: list[datetime] = []
    for index, repair in enumerate(records, start=1):
        repair_record = _object(repair)
        if repair_record is None:
            _reason(reasons, f"REPAIR_{index}_INVALID")
            continue
        task_id = repair_record.get("task_id")
        if not isinstance(task_id, str) or not task_id.startswith("REPAIR-") or task_id not in task_ids:
            _reason(reasons, f"REPAIR_{index}_TASK_INVALID")
        elif task_id in repair_task_ids:
            _reason(reasons, f"REPAIR_{index}_TASK_DUPLICATE")
        else:
            repair_task_ids.add(task_id)
        task = task_records.get(task_id) if isinstance(task_id, str) else None
        owner = task.get("owner") if isinstance(task, dict) else None
        if not isinstance(owner, dict) or owner.get("role") not in {"implementation-worker", "implementation-worker-qwen"}:
            _reason(reasons, f"REPAIR_{index}_OWNER_INVALID")
        if repair_record.get("status") != "accepted":
            _reason(reasons, f"REPAIR_{index}_NOT_ACCEPTED")
        elif isinstance(task_id, str) and task_id in task_ids:
            accepted_repair_task_ids.add(task_id)
        cycle = repair_record.get("cycle")
        if not _positive_integer(cycle) or cycle > 2 or (isinstance(cycles, int) and not isinstance(cycles, bool) and cycle > cycles):
            _reason(reasons, f"REPAIR_{index}_CYCLE_INVALID")
        _validate_scope(repair_record.get("scope"), reasons, index)
        acceptance_ids = repair_record.get("acceptance_ids")
        if not isinstance(acceptance_ids, list) or not acceptance_ids:
            _reason(reasons, f"REPAIR_{index}_ACCEPTANCE_IDS_MISSING")
        elif any(acceptance_id not in REQUIRED_ACCEPTANCE_IDS for acceptance_id in acceptance_ids):
            _reason(reasons, f"REPAIR_{index}_ACCEPTANCE_IDS_INVALID")
        rerun_check_ids = repair_record.get("rerun_check_ids")
        if not isinstance(rerun_check_ids, list) or not rerun_check_ids:
            _reason(reasons, f"REPAIR_{index}_RERUNS_MISSING")
        elif any(not isinstance(check_id, str) or check_id not in REQUIRED_CHECK_IDS for check_id in rerun_check_ids):
            _reason(reasons, f"REPAIR_{index}_RERUNS_INVALID")
        elif len(rerun_check_ids) != len(set(rerun_check_ids)):
            _reason(reasons, f"REPAIR_{index}_RERUNS_DUPLICATE")
        elif any(check_id not in checks for check_id in rerun_check_ids):
            _reason(reasons, f"REPAIR_{index}_RERUN_CHECK_MISSING")
        if not _non_empty_string(repair_record.get("resolution")):
            _reason(reasons, f"REPAIR_{index}_RESOLUTION_MISSING")
        failure_refs = repair_record.get("failure_refs")
        if not isinstance(failure_refs, list) or not failure_refs or any(not _non_empty_string(reference) for reference in failure_refs):
            _reason(reasons, f"REPAIR_{index}_FAILURE_REFS_MISSING")

        repair_scope = _object(repair_record.get("scope"))
        direct_dependencies = dependencies.get(task_id, []) if isinstance(task_id, str) else []
        owner_dependency = next(
            (
                dependency
                for dependency in direct_dependencies
                if dependency.startswith(("IMPLEMENT-", "REPAIR-"))
            ),
            None,
        )
        owner_task = task_records.get(owner_dependency) if owner_dependency is not None else None
        owner_scope = _object(owner_task.get("scope")) if isinstance(owner_task, dict) else None
        if (
            repair_scope is None
            or owner_scope is None
            or repair_scope.get("include") != owner_scope.get("include")
            or repair_scope.get("exclude") != owner_scope.get("exclude")
        ):
            _reason(reasons, f"REPAIR_{index}_SCOPE_MISMATCH")

        attempt_started_at = _timestamp(task.get("attempt_started_at") if isinstance(task, dict) else None)
        if attempt_started_at is None:
            _reason(reasons, f"REPAIR_{index}_TIMESTAMP_INVALID")
        else:
            repair_starts.append(attempt_started_at)
            if isinstance(rerun_check_ids, list) and all(
                isinstance(check_id, str) and check_id in checks for check_id in rerun_check_ids
            ):
                for check_id in rerun_check_ids:
                    observed_at = _timestamp(checks[check_id].get("observed_at"))
                    if observed_at is None:
                        _reason(reasons, f"REPAIR_{index}_CHECK_TIMESTAMP_INVALID")
                    elif observed_at < attempt_started_at:
                        _reason(reasons, f"REPAIR_{index}_CHECK_EVIDENCE_STALE")

    missing_records = repair_task_ids_in_tasks - repair_task_ids
    if missing_records:
        _reason(reasons, "REPAIR_TASK_RECORD_MISSING")
    missing_accepted_records = repair_task_ids_in_tasks - accepted_repair_task_ids
    if missing_accepted_records and not missing_records:
        _reason(reasons, "REPAIR_TASK_RECORD_NOT_ACCEPTED")

    if repair_starts:
        review = _object(record.get("review"))
        review_observed_at = _timestamp(review.get("observed_at") if review is not None else None)
        if review_observed_at is None:
            _reason(reasons, "REPAIR_REVIEW_TIMESTAMP_INVALID")
        elif review_observed_at < max(repair_starts):
            _reason(reasons, "REPAIR_REVIEW_EVIDENCE_STALE")


def _validate_drift(record: dict[str, Any], live_rollout: bool, reasons: list[str]) -> None:
    drift = _object(record.get("drift"))
    if drift is None:
        _reason(reasons, "DRIFT_MISSING")
        return
    drift_status = drift.get("status")
    if not isinstance(drift_status, str) or drift_status not in {"matched", "mismatch", "unrun", "unavailable"}:
        _reason(reasons, "DRIFT_STATUS_INVALID")
        return
    if drift_status in {"matched", "mismatch"}:
        if drift.get("hash_algorithm") != "sha256":
            _reason(reasons, "DRIFT_HASH_ALGORITHM_INVALID")
        required_files = drift.get("required_files")
        valid_required_files = isinstance(required_files, list) and all(
            isinstance(path, str) and _valid_relative_path(path) for path in required_files
        )
        if not valid_required_files or set(required_files) != DRIFT_REQUIRED_FILES:
            _reason(reasons, "DRIFT_REQUIRED_FILES_INVALID")

        def file_map(files: object, prefix: str, use_source_path: bool = False) -> dict[str, str]:
            result: dict[str, str] = {}
            if not isinstance(files, list):
                return result
            for index, file_record in enumerate(files, start=1):
                if not isinstance(file_record, dict):
                    _reason(reasons, f"DRIFT_{prefix}_{index}_INVALID")
                    continue
                path = file_record.get("source_path") if use_source_path else file_record.get("path")
                if not _valid_relative_path(path) or not isinstance(file_record.get("sha256"), str) or not SHA256_PATTERN.fullmatch(file_record["sha256"]):
                    _reason(reasons, f"DRIFT_{prefix}_{index}_INVALID")
                    continue
                if path in result:
                    _reason(reasons, f"DRIFT_{prefix}_DUPLICATE")
                result[path] = file_record["sha256"]
            return result

        source_map = file_map(drift.get("source_files"), "SOURCE")
        if set(source_map) != DRIFT_REQUIRED_FILES:
            _reason(reasons, "DRIFT_SOURCE_FILE_SET_INVALID")

        targets = drift.get("targets")
        if not isinstance(targets, dict) or set(targets) != {"installed", "codex_home"}:
            _reason(reasons, "DRIFT_TARGETS_MISSING")
            targets = {}
        target_statuses: list[str] = []
        for target_name in ("installed", "codex_home"):
            target = _object(targets.get(target_name))
            if target is None:
                _reason(reasons, f"DRIFT_{target_name.upper()}_MISSING")
                continue
            target_status = target.get("status")
            if target_status not in {"matched", "mismatch"}:
                _reason(reasons, f"DRIFT_{target_name.upper()}_STATUS_INVALID")
                continue
            target_statuses.append(target_status)
            target_map = file_map(target.get("files"), target_name.upper(), use_source_path=True)
            if set(target_map) != DRIFT_REQUIRED_FILES:
                _reason(reasons, f"DRIFT_{target_name.upper()}_FILE_SET_INVALID")
            hashes_match = target_map == source_map and bool(source_map)
            if target_status == "matched" and not hashes_match:
                _reason(reasons, f"DRIFT_{target_name.upper()}_MATCH_CONTRADICTION")
            if target_status == "mismatch" and hashes_match:
                _reason(reasons, f"DRIFT_{target_name.upper()}_MISMATCH_CONTRADICTION")

        expected_status = "matched" if target_statuses and all(status == "matched" for status in target_statuses) else "mismatch"
        if drift_status != expected_status:
            _reason(reasons, "DRIFT_STATUS_CONTRADICTION")
    elif not _non_empty_string(drift.get("required_action")):
        _reason(reasons, "DRIFT_REQUIRED_ACTION_MISSING")

    if live_rollout and drift_status != "matched":
        _reason(reasons, "DRIFT_NOT_MATCHED_FOR_LIVE_ROLLOUT")


def _validate_artifact(artifact: object, live_rollout: bool) -> list[str]:
    reasons: list[str] = []
    record = _object(artifact)
    if record is None:
        return ["ARTIFACT_NOT_OBJECT"]

    if record.get("schema_version") != "symphony.publication.v1":
        _reason(reasons, "SCHEMA_VERSION_INVALID")
    for field in ("issue_id", "plan_id", "evidence_revision", "source_fingerprint"):
        if not _non_empty_string(record.get(field)):
            _reason(reasons, f"{field.upper()}_MISSING")
    if _non_empty_string(record.get("source_fingerprint")) and not SHA256_PATTERN.fullmatch(record["source_fingerprint"]):
        _reason(reasons, "SOURCE_FINGERPRINT_INVALID")

    acceptance = _object(record.get("acceptance"))
    if acceptance is None:
        _reason(reasons, "ACCEPTANCE_MISSING")
    else:
        for acceptance_id in REQUIRED_ACCEPTANCE_IDS:
            if acceptance_id not in acceptance:
                _reason(reasons, f"{acceptance_id}_MISSING")
                continue
            status = acceptance.get(acceptance_id)
            if status != "passed":
                _reason(reasons, f"{acceptance_id}_NOT_PASSED")

    checks = record.get("checks")
    check_ids: set[str] = set()
    check_records: dict[str, dict[str, Any]] = {}
    if not isinstance(checks, list) or not checks:
        _reason(reasons, "CHECKS_MISSING")
    else:
        for index, check in enumerate(checks, start=1):
            check_id = _validate_check(check, reasons, index)
            if check_id is not None:
                if check_id in check_ids:
                    _reason(reasons, f"CHECK_{index}_DUPLICATE")
                check_ids.add(check_id)
                if isinstance(check, dict):
                    check_records[check_id] = check
        for check_id in sorted(REQUIRED_CHECK_IDS - check_ids):
            _reason(reasons, f"CHECK_REQUIRED_{check_id}_MISSING")

    task_ids = _validate_task_records(record, reasons)
    _validate_worker_results(record, reasons)
    _validate_route_records(record, task_ids, reasons)
    _validate_checkpoints(record, task_ids, reasons)
    _validate_review(record, reasons)
    _validate_repairs(record, task_ids, check_records, reasons)
    _validate_drift(record, live_rollout, reasons)

    git = _object(record.get("git"))
    if git is None:
        _reason(reasons, "GIT_EVIDENCE_MISSING")
    else:
        if git.get("scope_clean") is not True:
            _reason(reasons, "GIT_SCOPE_NOT_CLEAN")
        if not _non_empty_string(git.get("secret_scan")):
            _reason(reasons, "GIT_SECRET_SCAN_MISSING")

    published = record.get("published")
    if not isinstance(published, bool):
        _reason(reasons, "PUBLISHED_STATUS_INVALID")
    elif published:
        publication = _object(record.get("publication"))
        if publication is None or not _non_empty_string(publication.get("branch")) or not _non_empty_string(publication.get("commit_sha")) or not _non_empty_string(publication.get("pr_url")) or not _non_empty_string(publication.get("published_at")):
            _reason(reasons, "PUBLICATION_EVIDENCE_MISSING")

    return reasons


def _read_artifact(path: Path) -> tuple[object | None, str | None]:
    if path.is_symlink():
        return None, "ARTIFACT_SYMLINK"
    if not path.exists() or not path.is_file():
        return None, "ARTIFACT_UNAVAILABLE"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "ARTIFACT_INVALID_JSON"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--live-rollout", action="store_true")
    args = parser.parse_args(argv)

    artifact, read_error = _read_artifact(args.artifact)
    if read_error:
        reasons = [read_error]
    else:
        try:
            reasons = _validate_artifact(artifact, args.live_rollout)
        except (AttributeError, KeyError, TypeError, ValueError):
            reasons = ["ARTIFACT_SHAPE_INVALID"]
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "unavailable" if read_error else ("accepted" if not reasons else "rejected"),
        "reason_codes": sorted(reasons),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if read_error:
        return 3
    return 0 if not reasons else 2


if __name__ == "__main__":
    raise SystemExit(main())
