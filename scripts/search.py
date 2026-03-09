#!/usr/bin/env python3
"""Cross-platform deep search runner for Codex CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_MODEL = "gpt-5.2"
DEFAULT_TIMEOUT = 120
DEFAULT_SANDBOX = "workspace-write"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def script_path() -> Path:
    return Path(__file__).resolve()


def skill_root(path: Path) -> Path:
    return path.resolve().parents[1]


def default_result_dir(path: Path) -> Path:
    return skill_root(path) / "data" / "codex-search-results"


def resolve_result_dir(path: Path, override: Optional[str]) -> Path:
    candidate = override or os.environ.get("CODEX_DEEP_SEARCH_RESULT_DIR")
    if candidate:
        return Path(candidate).expanduser().resolve()
    return default_result_dir(path)


def default_output_path(result_dir: Path, task_name: str) -> Path:
    return result_dir / f"{task_name}.md"


def raw_log_path(result_dir: Path, task_name: str) -> Path:
    return result_dir / f"{task_name}.raw.log"


def meta_path(result_dir: Path, task_name: str) -> Path:
    return result_dir / f"{task_name}.meta.json"


def latest_meta_path(result_dir: Path) -> Path:
    return result_dir / "latest-meta.json"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_metadata(result_dir: Path, task_name: str, payload: dict) -> Path:
    task_meta = meta_path(result_dir, task_name)
    write_json(task_meta, payload)
    write_json(latest_meta_path(result_dir), payload)
    return task_meta


def build_search_instruction(prompt: str, output_path: Path) -> str:
    return "\n".join(
        [
            "You are a research assistant. Search the web for the following query.",
            "",
            "CRITICAL RULES:",
            f"1. Write findings to {output_path} incrementally after each meaningful discovery.",
            "2. Start the file with a title and query, then append sections as you discover them.",
            "3. Keep searches focused with a maximum of 8 web searches.",
            "4. Include source URLs inline.",
            "5. End with a brief summary section.",
            "",
            f"Query: {prompt}",
            "",
            "Start by writing the file header now, then search and append.",
        ]
    )


def render_header(prompt: str, status: str = "In progress...") -> str:
    return f"# Deep Search Report\n**Query:** {prompt}\n**Status:** {status}\n---\n"


def resolve_codex_bin(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    candidate = value or os.environ.get("CODEX_BIN") or "codex"
    resolved = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
    if resolved and os.path.exists(resolved):
        return resolved, None
    return None, f"Codex executable not found: {candidate}"


def duration_seconds(start_monotonic: float) -> int:
    return max(0, int(round(time.monotonic() - start_monotonic)))


def run_post_hook(
    hook_command: Optional[str],
    *,
    task_name: str,
    output_path: Path,
    meta_file: Path,
    status: str,
    exit_code: int,
    duration: int,
) -> Optional[str]:
    if not hook_command:
        return None

    env = os.environ.copy()
    env.update(
        {
            "TASK_NAME": task_name,
            "OUTPUT": str(output_path),
            "META_FILE": str(meta_file),
            "STATUS": status,
            "EXIT_CODE": str(exit_code),
            "DURATION": str(duration),
        }
    )
    completed = subprocess.run(
        hook_command,
        shell=True,
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return None
    detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
    return f"post-run hook failed: {detail}"


def finalize_output(output_path: Path, status: str, error: Optional[str]) -> None:
    if output_path.exists():
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n**Final Status:** {status}\n")
            if error:
                handle.write(f"**Error:** {error}\n")
            handle.write(f"\n---\n_Search completed at {utc_now_iso()}_\n")


def run_search(
    *,
    prompt: str,
    task_name: str,
    model: str,
    timeout_seconds: int,
    result_dir: Path,
    output_path: Path,
    codex_bin: Optional[str],
    post_run_hook: Optional[str],
) -> int:
    result_dir.mkdir(parents=True, exist_ok=True)
    ensure_parent(output_path)

    started_at = utc_now_iso()
    start_monotonic = time.monotonic()
    raw_log = raw_log_path(result_dir, task_name)
    output_path.write_text(render_header(prompt), encoding="utf-8")

    running_payload = {
        "task_name": task_name,
        "prompt": prompt,
        "output": str(output_path),
        "raw_log": str(raw_log),
        "started_at": started_at,
        "completed_at": None,
        "duration_seconds": 0,
        "exit_code": None,
        "status": "running",
        "model": model,
        "pid": os.getpid(),
        "error": None,
        "hook_error": None,
    }
    task_meta = write_metadata(result_dir, task_name, running_payload)

    resolved_codex, error = resolve_codex_bin(codex_bin)
    if not resolved_codex:
        duration = duration_seconds(start_monotonic)
        finalize_output(output_path, "failed", error)
        failed_payload = {
            **running_payload,
            "completed_at": utc_now_iso(),
            "duration_seconds": duration,
            "exit_code": 127,
            "status": "failed",
            "error": error,
        }
        task_meta = write_metadata(result_dir, task_name, failed_payload)
        hook_error = run_post_hook(
            post_run_hook,
            task_name=task_name,
            output_path=output_path,
            meta_file=task_meta,
            status="failed",
            exit_code=127,
            duration=duration,
        )
        if hook_error:
            failed_payload["hook_error"] = hook_error
            write_metadata(result_dir, task_name, failed_payload)
        return 127

    command = [
        resolved_codex,
        "exec",
        "--model",
        model,
        "--full-auto",
        "--skip-git-repo-check",
        "--sandbox",
        DEFAULT_SANDBOX,
        "-c",
        'model_reasoning_effort="low"',
        build_search_instruction(prompt, output_path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        raw_log.write_text(stdout + stderr, encoding="utf-8")
        exit_code = completed.returncode
        status = "done" if exit_code == 0 else "failed"
        error = None if exit_code == 0 else (stderr.strip() or stdout.strip() or f"exit {exit_code}")
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        raw_log.write_text(stdout + stderr, encoding="utf-8")
        exit_code = 124
        status = "timeout"
        error = f"search timed out after {timeout_seconds}s"

    finalize_output(output_path, status, error)
    duration = duration_seconds(start_monotonic)
    completed_payload = {
        **running_payload,
        "completed_at": utc_now_iso(),
        "duration_seconds": duration,
        "exit_code": exit_code,
        "status": status,
        "error": error,
    }
    task_meta = write_metadata(result_dir, task_name, completed_payload)
    hook_error = run_post_hook(
        post_run_hook,
        task_name=task_name,
        output_path=output_path,
        meta_file=task_meta,
        status=status,
        exit_code=exit_code,
        duration=duration,
    )
    if hook_error:
        completed_payload["hook_error"] = hook_error
        write_metadata(result_dir, task_name, completed_payload)
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform deep search runner for Codex CLI.")
    parser.add_argument("--prompt", required=True, help="Research query.")
    parser.add_argument("--task-name", default=f"search-{int(time.time())}", help="Task identifier.")
    parser.add_argument("--output", help="Output markdown path.")
    parser.add_argument("--result-dir", help="Directory for task result artifacts.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Codex model name.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds.")
    parser.add_argument("--codex-bin", help="Codex executable path or name.")
    parser.add_argument("--post-run-hook", help="Optional shell command executed after task completion.")
    parser.add_argument("--dispatch", action="store_true", help="Run the search in the background.")
    return parser


def dispatch_search(args: argparse.Namespace) -> int:
    result_dir = resolve_result_dir(script_path(), args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(result_dir, args.task_name)

    running_payload = {
        "task_name": args.task_name,
        "prompt": args.prompt,
        "output": str(output_path),
        "raw_log": str(raw_log_path(result_dir, args.task_name)),
        "started_at": utc_now_iso(),
        "completed_at": None,
        "duration_seconds": 0,
        "exit_code": None,
        "status": "running",
        "model": args.model,
        "pid": None,
        "error": None,
        "hook_error": None,
    }
    task_meta = write_metadata(result_dir, args.task_name, running_payload)

    child_args = [
        sys.executable,
        str(script_path()),
        "--prompt",
        args.prompt,
        "--task-name",
        args.task_name,
        "--result-dir",
        str(result_dir),
        "--output",
        str(output_path),
        "--model",
        args.model,
        "--timeout",
        str(args.timeout),
    ]
    if args.codex_bin:
        child_args.extend(["--codex-bin", args.codex_bin])
    if args.post_run_hook:
        child_args.extend(["--post-run-hook", args.post_run_hook])

    with raw_log_path(result_dir, args.task_name).open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            child_args,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    running_payload["pid"] = process.pid
    task_meta = write_metadata(result_dir, args.task_name, running_payload)
    print(json.dumps({"task_name": args.task_name, "meta_file": str(task_meta), "output": str(output_path)}))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dispatch:
        return dispatch_search(args)

    result_dir = resolve_result_dir(script_path(), args.result_dir)
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(result_dir, args.task_name)
    return run_search(
        prompt=args.prompt,
        task_name=args.task_name,
        model=args.model,
        timeout_seconds=args.timeout,
        result_dir=result_dir,
        output_path=output_path,
        codex_bin=args.codex_bin,
        post_run_hook=args.post_run_hook,
    )


if __name__ == "__main__":
    sys.exit(main())
