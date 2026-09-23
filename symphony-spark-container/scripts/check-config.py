#!/usr/bin/env python3
"""Report drift between safe Symphony configuration copies.

The command reads only an explicit allowlist of workflow and agent files. It
reports file names, sizes, modes, and SHA-256 values. It never prints file
contents or reads credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import sys
import tomllib
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


SCHEMA_VERSION = "symphony.config.v1"
HASH_ALGORITHM = "sha256"
SOURCE_FILES = (
    Path("WORKFLOW.md"),
    Path("config/config.toml"),
    Path("config/agents/acceptance-reviewer.toml"),
    Path("config/agents/implementation-worker-qwen.toml"),
    Path("config/agents/implementation-worker.toml"),
    Path("config/agents/planner.toml"),
    Path("config/agents/progress-orchestrator.toml"),
    Path("config/spark-qwen.config.toml"),
)
TARGET_SOURCE_FILES = {
    "mirror": SOURCE_FILES,
    # The workflow is consumed from the deployment mirror. Codex home stores
    # only the Codex configuration files that the entrypoint installs there.
    "codex-home": tuple(path for path in SOURCE_FILES if path != Path("WORKFLOW.md")),
}
TARGET_EXTRA_PATTERNS = {
    "mirror": ("config/agents/*.toml", "config/*.config.toml"),
    "codex-home": ("WORKFLOW.md", "agents/*.toml", "*.config.toml"),
}
CODEX_VERSION = "0.155.1"
REQUIRED_AGENT_ROUTES = {
    "planner.toml": {
        "name": "planner",
        "model": "gpt-6-astra",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
    "implementation-worker.toml": {
        "name": "implementation-worker",
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "xhigh",
        "sandbox_mode": "workspace-write",
    },
    "implementation-worker-qwen.toml": {
        "name": "implementation-worker-qwen",
        "model": "qwen3.8-27b",
        "model_provider": "spark_qwen",
        "model_reasoning_effort": "low",
        "sandbox_mode": "workspace-write",
    },
    "progress-orchestrator.toml": {
        "name": "progress-orchestrator",
        "model": "gpt-6-astra",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
    "acceptance-reviewer.toml": {
        "name": "acceptance-reviewer",
        "model": "gpt-6-astra",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
}
REQUIRED_QWEN_PROFILE = {
    "model": "qwen3.8-27b",
    "model_provider": "spark_qwen",
    "model_reasoning_effort": "low",
    "model_reasoning_summary": "none",
    "model_supports_reasoning_summaries": False,
}


class ConfigError(Exception):
    """Report a safe configuration inspection failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _source_paths(root: Path) -> list[Path]:
    """Return the allowlisted source files in stable order."""

    del root
    return list(SOURCE_FILES)


def _target_extra_paths(root: Path, layout: str) -> list[Path]:
    """Return extra files from the non-secret target allowlist."""

    patterns = TARGET_EXTRA_PATTERNS[layout]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(path.relative_to(root) for path in root.glob(pattern)))
    return sorted(set(paths))


def _safe_path(root: Path, relative: Path) -> Path:
    """Resolve one allowlisted path without following an escape symlink."""

    if relative.is_absolute() or ".." in relative.parts:
        raise ConfigError("CONFIG_PATH_ESCAPE", "a configuration path escapes its root")

    candidate = root / relative

    try:
        absolute_path = candidate.absolute()
    except RuntimeError as error:
        raise ConfigError("CONFIG_PATH_ESCAPE", "a configuration path is outside its root") from error
    current = Path(absolute_path.anchor)
    for part in absolute_path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ConfigError("CONFIG_SYMLINK", "a configuration path contains a symlink")
    return candidate


def _file_record_at(candidate: Path, relative: Path) -> dict[str, Any]:
    """Return non-secret identity data for one configuration file."""

    if candidate.is_symlink():
        raise ConfigError("CONFIG_SYMLINK", "a configuration path is a symlink")
    if not candidate.exists():
        return {"path": relative.as_posix(), "status": "missing"}
    if not candidate.is_file():
        return {"path": relative.as_posix(), "status": "invalid"}

    digest = hashlib.sha256()
    size = 0
    with candidate.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)

    mode = stat.S_IMODE(candidate.stat().st_mode)
    return {
        "path": relative.as_posix(),
        "status": "present",
        "sha256": digest.hexdigest(),
        "size": size,
        "mode": oct(mode),
    }


def _file_record(root: Path, relative: Path) -> dict[str, Any]:
    """Return a file record for a path below a checked root."""

    return _file_record_at(_safe_path(root, relative), relative)


def _safe_workflow_path(workflow_path: Path) -> Path:
    """Resolve the explicitly selected workflow without following symlinks."""

    if workflow_path.name != "WORKFLOW.md":
        raise ConfigError("CONFIG_WORKFLOW_PATH", "the workflow path must name WORKFLOW.md")

    try:
        absolute_path = workflow_path.absolute()
    except RuntimeError as error:
        raise ConfigError("CONFIG_PATH_ESCAPE", "the workflow path cannot be resolved") from error

    current = Path(absolute_path.anchor)
    for part in absolute_path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ConfigError("CONFIG_SYMLINK", "the workflow path contains a symlink")
    return workflow_path


def _manifest(root: Path, workflow_path: Path | None = None) -> dict[str, Any]:
    """Build a safe source manifest from the explicit file allowlist."""

    try:
        root.resolve(strict=True)
    except FileNotFoundError as error:
        raise ConfigError("CONFIG_ROOT_MISSING", "the configuration root is unavailable") from error

    selected_workflow = _safe_workflow_path(workflow_path) if workflow_path is not None else None
    files: list[dict[str, Any]] = []
    source_paths = _source_paths(root)
    for relative in source_paths:
        if relative == Path("WORKFLOW.md") and selected_workflow is not None:
            files.append(_file_record_at(selected_workflow, relative))
        else:
            files.append(_file_record(root, relative))
    return {
        "schema_version": SCHEMA_VERSION,
        "layout": "source",
        "status": "matched" if all(file["status"] == "present" for file in files) else "unavailable",
        "hash_algorithm": HASH_ALGORITHM,
        "required_files": [relative.as_posix() for relative in source_paths],
        "files": files,
    }


def _target_manifest(source: dict[str, Any], root: Path, layout: str) -> dict[str, Any]:
    """Read the source file identities from an installed target layout."""

    target_source_paths = TARGET_SOURCE_FILES[layout]
    target_source_path_set = set(target_source_paths)
    target_files: list[dict[str, Any]] = []
    expected_target_paths: set[Path] = set()
    for source_file in source["files"]:
        relative = Path(source_file["path"])
        if relative not in target_source_path_set:
            continue
        target_relative = relative
        if layout == "codex-home" and relative.parts[0] == "config":
            target_relative = relative.relative_to("config")
        expected_target_paths.add(target_relative)
        record = _file_record(root, target_relative)
        record["source_path"] = relative.as_posix()
        target_files.append(record)

    extra_files = [
        path.as_posix()
        for path in _target_extra_paths(root, layout)
        if path not in expected_target_paths
    ]

    if any(file["status"] != "present" for file in source["files"]):
        status = "unavailable"
    elif any(file["status"] != "present" for file in target_files):
        status = "unavailable"
    elif extra_files:
        status = "mismatch"
    else:
        source_by_path = {file["path"]: file for file in source["files"]}
        status = "matched"
        for target_file in target_files:
            source_file = source_by_path[target_file["source_path"]]
            if target_file["sha256"] != source_file["sha256"]:
                status = "mismatch"
                break

    return {
        "schema_version": SCHEMA_VERSION,
        "layout": layout,
        "status": status,
        "hash_algorithm": HASH_ALGORITHM,
        "required_files": [relative.as_posix() for relative in target_source_paths],
        "files": target_files,
        "extra_files": extra_files,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """Write a report with replacement after a complete temporary write."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        json.dump(value, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
    os.replace(temporary_path, path)


def _dump(value: dict[str, Any], report: Path | None) -> None:
    """Write a report to stdout and, when requested, to a file."""

    encoded = json.dumps(value, indent=2, sort_keys=True)
    print(encoded)
    if report is not None:
        _write_json(report, value)


def _workflow_command(workflow_path: Path) -> list[str] | None:
    """Return the exact Codex command from the workflow front matter."""

    try:
        safe_workflow_path = _safe_workflow_path(workflow_path)
    except ConfigError:
        return None
    if not safe_workflow_path.is_file():
        return None
    try:
        contents = safe_workflow_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    front_matter = re.match(r"\A---\n(.*?)\n---\n", contents, flags=re.DOTALL)
    if front_matter is None:
        return None
    section_indent: int | None = None
    property_indent: int | None = None
    for line in front_matter.group(1).splitlines():
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" \t"))
        if section_indent is None:
            if line.strip() == "codex:":
                section_indent = indent
            continue

        if indent <= section_indent:
            break
        if property_indent is None:
            property_indent = indent
        if indent != property_indent:
            continue

        match = re.match(r"^[ \t]+command:\s*(.+?)\s*$", line)
        if match:
            try:
                return shlex.split(match.group(1))
            except ValueError:
                return None
    return None


def _validate_routes(root: Path, workflow_path: Path | None) -> dict[str, Any]:
    """Validate the required non-secret model routes without exposing values."""

    reasons: list[str] = []
    role_results: list[dict[str, str]] = []
    for filename, expected in REQUIRED_AGENT_ROUTES.items():
        relative = Path("config/agents") / filename
        try:
            candidate = _safe_path(root, relative)
            with candidate.open("rb") as stream:
                actual = tomllib.load(stream)
        except (ConfigError, FileNotFoundError, NotADirectoryError, PermissionError, tomllib.TOMLDecodeError):
            reasons.append(f"INVALID_AGENT_{filename}")
            role_results.append({"path": relative.as_posix(), "status": "invalid"})
            continue

        mismatches = [key for key, value in expected.items() if actual.get(key) != value]
        if mismatches:
            reasons.append(f"INVALID_AGENT_{filename}")
            role_results.append({"path": relative.as_posix(), "status": "invalid"})
        else:
            role_results.append({"path": relative.as_posix(), "status": "matched"})

    try:
        config_path = _safe_path(root, Path("config/config.toml"))
        with config_path.open("rb") as stream:
            config = tomllib.load(stream)
    except (ConfigError, FileNotFoundError, NotADirectoryError, PermissionError, tomllib.TOMLDecodeError):
        reasons.append("INVALID_CONFIG")
        config = {}

    agents = config.get("agents")
    thread_limit = agents.get("max_concurrent_threads_per_session") if isinstance(agents, dict) else None
    if (
        not isinstance(agents, dict)
        or agents.get("enabled") is not True
        or not isinstance(thread_limit, int)
        or isinstance(thread_limit, bool)
        or thread_limit < 4
        or agents.get("default_subagent_model") != "gpt-5.6-luna"
        or agents.get("default_subagent_reasoning_effort") != "xhigh"
    ):
        reasons.append("INVALID_AGENT_CAPACITY")

    providers = config.get("model_providers")
    qwen_provider = providers.get("spark_qwen") if isinstance(providers, dict) else None
    if (
        not isinstance(qwen_provider, dict)
        or qwen_provider.get("base_url") != "http://qwen:8000/v1"
        or qwen_provider.get("wire_api") != "responses"
        or qwen_provider.get("requires_openai_auth") is not False
    ):
        reasons.append("INVALID_QWEN_PROVIDER")

    try:
        profile_path = _safe_path(root, Path("config/spark-qwen.config.toml"))
        with profile_path.open("rb") as stream:
            profile = tomllib.load(stream)
    except (ConfigError, FileNotFoundError, NotADirectoryError, PermissionError, tomllib.TOMLDecodeError):
        reasons.append("INVALID_QWEN_PROFILE")
        profile = {}
    if not isinstance(profile, dict) or any(profile.get(key) != value for key, value in REQUIRED_QWEN_PROFILE.items()):
        reasons.append("INVALID_QWEN_PROFILE")

    workflow_candidate = workflow_path or root / Path("WORKFLOW.md")
    command = _workflow_command(workflow_candidate)
    if command is None:
        reasons.append("INVALID_WORKFLOW_ROUTE")
    expected_command = [
        "codex",
        "--config",
        "shell_environment_policy.inherit=all",
        "--config",
        'model="gpt-5.6-luna"',
        "--config",
        "model_reasoning_effort=xhigh",
        "app-server",
    ]
    if command != expected_command:
        reasons.append("INVALID_WORKFLOW_ROUTE")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "matched" if not reasons else "mismatch",
        "reason_codes": sorted(set(reasons)),
        "roles": role_results,
        "compatibility": {"codex_version": CODEX_VERSION, "status": "declared"},
    }


def _source_command(args: argparse.Namespace) -> int:
    source = _manifest(Path(args.workspace), Path(args.workflow) if args.workflow else None)
    _dump(source, Path(args.report) if args.report else None)
    return 0 if source["status"] == "matched" else 2


def _validate_command(args: argparse.Namespace) -> int:
    result = _validate_routes(Path(args.workspace), Path(args.workflow) if args.workflow else None)
    _dump(result, Path(args.report) if args.report else None)
    return 0 if result["status"] == "matched" else 2


def _compare_command(args: argparse.Namespace) -> int:
    source = _manifest(Path(args.workspace), Path(args.workflow) if args.workflow else None)
    targets: dict[str, dict[str, Any]] = {}
    for name, root, layout in (
        ("installed", args.installed_root, "mirror"),
        ("codex_home", args.codex_home, "codex-home"),
    ):
        if root:
            try:
                targets[name] = _target_manifest(source, Path(root), layout)
            except ConfigError as error:
                targets[name] = {
                    "schema_version": SCHEMA_VERSION,
                    "layout": layout,
                    "status": "unavailable",
                    "reason_code": error.code,
                }
        else:
            targets[name] = {
                "schema_version": SCHEMA_VERSION,
                "layout": layout,
                "status": "unavailable",
                "reason_code": "CONFIG_ROOT_NOT_SPECIFIED",
            }

    statuses = {target["status"] for target in targets.values()}
    if source["status"] != "matched" or "unavailable" in statuses:
        status = "unavailable"
        exit_code = 3
    elif "mismatch" in statuses:
        status = "mismatch"
        exit_code = 2
    else:
        status = "matched"
        exit_code = 0

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "hash_algorithm": HASH_ALGORITHM,
        "required_files": source["required_files"],
        "source_files": source["files"],
        "source": source,
        "targets": targets,
        "compatibility": {"codex_version": CODEX_VERSION, "status": "declared"},
        "execution_observation": "not_available",
    }
    if status == "unavailable":
        report["required_action"] = "Resolve unavailable configuration state before publication."
    _dump(report, Path(args.report) if args.report else None)
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    source = subparsers.add_parser("source", help="report the source configuration")
    source.add_argument("--workspace", default=".")
    source.add_argument("--workflow")
    source.add_argument("--report")
    source.set_defaults(handler=_source_command)

    validate = subparsers.add_parser("validate", help="validate required model routes")
    validate.add_argument("--workspace", default=".")
    validate.add_argument("--workflow")
    validate.add_argument("--report")
    validate.set_defaults(handler=_validate_command)

    compare = subparsers.add_parser("compare", help="compare source and installed copies")
    compare.add_argument("--workspace", default=".")
    compare.add_argument("--workflow")
    compare.add_argument("--installed-root")
    compare.add_argument("--codex-home")
    compare.add_argument("--report")
    compare.set_defaults(handler=_compare_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the safe configuration report command."""

    try:
        args = _parser().parse_args(argv)
        return args.handler(args)
    except ConfigError as error:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "status": "unavailable", "reason_code": error.code}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
