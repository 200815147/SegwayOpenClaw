#!/usr/bin/env python3
"""
SegwayBench - Segway Robot Agent Benchmarking System

This script orchestrates benchmarking of OpenClaw agents on Segway robot tasks.
Extends PinchBench with MockLayer integration and safety-mode support.
"""
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml>=6.0.1",
# ]
# ///

import argparse
import json
import logging
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Load .env from main openclaw workspace so SEGWAY_* vars are available
# to all subprocesses (openclaw agent → skill scripts)
_main_env_path = Path.home() / ".openclaw" / "workspace" / ".env"
if _main_env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_main_env_path, override=False)
    except ImportError:
        # Fallback: parse .env manually
        for line in _main_env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

from lib_agent import (
    cleanup_agent_sessions,
    ensure_agent_exists,
    execute_openclaw_task,
    ModelValidationError,
    prepare_task_workspace,
    slugify_model,
    validate_model,
)
from lib_grading import GradeResult, grade_task
from lib_mock import MockLayer
from lib_tasks import Task, TaskLoader


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("benchmark.log")],
)

logger = logging.getLogger("benchmark")


class OpenClawAgent:
    """Scaffold for OpenClaw agent creation and execution."""

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = config or {}
        logger.info(f"Initialized OpenClawAgent: {agent_id}")

    def execute_task(self, task: Task, simulate: bool = False) -> Dict[str, Any]:
        if simulate:
            logger.info("Simulate flag no longer supported for execute_task")
        raise NotImplementedError("Use execute_openclaw_task helper for real runs")


class BenchmarkRunner:
    """Orchestrates benchmark execution across tasks and agents."""

    def __init__(self, tasks_dir: Path, safety_mode: Optional[str] = None):
        self.task_loader = TaskLoader(tasks_dir)
        self.tasks: List[Task] = []
        self.agents: List[OpenClawAgent] = []
        self.safety_mode = safety_mode
        logger.info("Initialized BenchmarkRunner (safety_mode=%s)", safety_mode)

    def load_tasks(self) -> None:
        """Load all tasks from the tasks directory."""
        logger.info("Loading tasks...")
        self.tasks = self.task_loader.load_all_tasks()
        logger.info(f"Loaded {len(self.tasks)} tasks")

    def create_agent(self, agent_id: str, config: Optional[Dict[str, Any]] = None) -> OpenClawAgent:
        logger.info(f"Creating agent: {agent_id}")
        agent = OpenClawAgent(agent_id, config)
        self.agents.append(agent)
        return agent

    def get_effective_safety_level(self, task: Task) -> str:
        """Determine effective safety level: --safety-mode override or task's own level."""
        if self.safety_mode is not None:
            return self.safety_mode
        return task.api_safety_level

    def print_task_summary(self) -> None:
        """Print a summary of all loaded tasks."""
        if not self.tasks:
            logger.warning("No tasks loaded")
            return

        print("\n" + "=" * 80)
        print(f"LOADED TASKS SUMMARY ({len(self.tasks)} tasks)")
        print("=" * 80)

        for task in self.tasks:
            print(f"\n[{task.task_id}] {task.name}")
            print(f"  Category: {task.category}")
            print(f"  Grading: {task.grading_type}")
            print(f"  Safety: {task.api_safety_level}")
            print(f"  Timeout: {task.timeout_seconds}s")
            print(f"  Criteria: {len(task.grading_criteria)} items")
            print(
                f"  Prompt: {task.prompt[:100]}..."
                if len(task.prompt) > 100
                else f"  Prompt: {task.prompt}"
            )

        print("\n" + "=" * 80)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SegwayBench - Segway Robot Agent Benchmark Runner")
    parser.add_argument(
        "--model",
        required=False,
        help="Model identifier (e.g., openrouter/anthropic/claude-sonnet-4, google/gemini-2.5-flash, nvidia/deepseek-ai/deepseek-v3.2)",
    )
    parser.add_argument(
        "--suite",
        default="all",
        help='Tasks to run: "all", "automated-only", or comma-separated IDs',
    )
    parser.add_argument(
        "--safety-mode",
        choices=["read_only", "mock_required", "full_mock", "live_allowed"],
        default=None,
        help="Global safety level override: read_only, mock_required, full_mock (all APIs mocked), live_allowed",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Results directory",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Request a new API token and save it to local config",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading to server",
    )
    parser.add_argument(
        "--upload",
        type=str,
        metavar="RESULTS_JSON",
        help="Upload a previous run's results JSON and exit (skips benchmarking)",
    )
    parser.add_argument(
        "--timeout-multiplier",
        type=float,
        default=1.0,
        help="Scale all task timeouts",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs per task for averaging",
    )
    parser.add_argument(
        "--judge",
        default=None,
        help="Judge model identifier (default: openrouter/anthropic/claude-opus-4.5)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (shows transcript contents, workspace files, etc.)",
    )
    parser.add_argument(
        "--official-key",
        type=str,
        metavar="KEY",
        help="Official key to mark submission as official",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue running all tasks even if sanity check scores 0%%",
    )
    parser.add_argument(
        "--task-delay",
        type=float,
        default=10,
        help="Seconds to wait between tasks (useful for rate-limited APIs, e.g. --task-delay 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only prepare workspace and show files, don't call any model",
    )
    return parser.parse_args()


def _select_task_ids(tasks: List[Task], suite: str) -> Optional[List[str]]:
    if suite == "all":
        return None
    if suite == "automated-only":
        return [task.task_id for task in tasks if task.grading_type == "automated"]
    return [task_id.strip() for task_id in suite.split(",") if task_id.strip()]


def _next_run_id(run_root: Path, output_dir: Path = None) -> str:
    """Determine the next run ID by scanning both /tmp workspace dirs and the
    results output directory.  This prevents ID collisions when /tmp is cleared
    (e.g. after a reboot) but result files still exist in output_dir."""
    run_root.mkdir(parents=True, exist_ok=True)
    existing = []
    for entry in run_root.iterdir():
        if entry.is_dir() and entry.name.isdigit():
            existing.append(int(entry.name))
    # Also scan output_dir for result files like "0005_model-slug.json"
    if output_dir is not None and output_dir.exists():
        import re
        for entry in output_dir.iterdir():
            m = re.match(r"^(\d{4})_.*\.json$", entry.name)
            if m:
                existing.append(int(m.group(1)))
    next_id = (max(existing) + 1) if existing else 1
    return f"{next_id:04d}"


def _get_git_version(script_dir: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            cwd=script_dir,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _compute_efficiency_summary(
    task_entries: List[Dict[str, Any]],
    grades_by_task_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute aggregate token efficiency metrics across all tasks."""
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_cost_usd = 0.0
    total_requests = 0
    total_execution_time = 0.0
    tasks_with_usage = 0

    per_task_efficiency: List[Dict[str, Any]] = []
    for entry in task_entries:
        usage = entry.get("usage", {})
        task_id = entry["task_id"]
        grading = grades_by_task_id.get(task_id, {})
        score = float(grading.get("mean", 0.0))

        inp = int(usage.get("input_tokens", 0))
        out = int(usage.get("output_tokens", 0))
        tot = int(usage.get("total_tokens", 0))
        cost = float(usage.get("cost_usd", 0.0) or 0.0)
        reqs = int(usage.get("request_count", 0))
        exec_time = float(entry.get("execution_time", 0.0) or 0.0)

        total_input_tokens += inp
        total_output_tokens += out
        total_tokens += tot
        total_cost_usd += cost
        total_requests += reqs
        total_execution_time += exec_time

        if tot > 0:
            tasks_with_usage += 1

        per_task_efficiency.append(
            {
                "task_id": task_id,
                "score": round(score, 4),
                "total_tokens": tot,
                "cost_usd": round(cost, 6),
                "tokens_per_score_point": round(tot / score, 1) if score > 0 else None,
            }
        )

    all_scores = [float(g.get("mean", 0.0)) for g in grades_by_task_id.values()]
    total_score = sum(all_scores)
    num_tasks = len(all_scores)

    summary: Dict[str, Any] = {
        "total_tokens": total_tokens,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cost_usd": round(total_cost_usd, 6),
        "total_requests": total_requests,
        "total_execution_time_seconds": round(total_execution_time, 2),
        "tasks_with_usage_data": tasks_with_usage,
        "tokens_per_task": round(total_tokens / num_tasks, 1) if num_tasks > 0 else 0,
        "cost_per_task_usd": round(total_cost_usd / num_tasks, 6) if num_tasks > 0 else 0,
        "score_per_1k_tokens": (
            round(total_score / (total_tokens / 1000), 6) if total_tokens > 0 else None
        ),
        "score_per_dollar": (
            round(total_score / total_cost_usd, 4) if total_cost_usd > 0 else None
        ),
        "per_task": per_task_efficiency,
    }
    return summary


def _compute_category_summary(
    task_entries: List[Dict[str, Any]],
    tasks_by_id: Dict[str, Task],
    grades_by_task_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute by_category breakdown for the JSON report summary."""
    category_data: Dict[str, Dict[str, float]] = {}

    for entry in task_entries:
        task_id = entry["task_id"]
        task = tasks_by_id.get(task_id)
        if not task:
            continue

        category = task.category if task.category else "uncategorized"
        grading = grades_by_task_id.get(task_id, {})
        mean_score = float(grading.get("mean", 0.0))
        max_score = 1.0

        if category not in category_data:
            category_data[category] = {"tasks": 0, "score": 0.0, "max": 0.0}

        category_data[category]["tasks"] += 1
        category_data[category]["score"] += mean_score
        category_data[category]["max"] += max_score

    by_category: Dict[str, Any] = {}
    for category in sorted(category_data.keys()):
        data = category_data[category]
        pct = round(data["score"] / data["max"] * 100, 1) if data["max"] > 0 else 0.0
        by_category[category] = {
            "tasks": int(data["tasks"]),
            "score": round(data["score"], 1),
            "max": round(data["max"], 1),
            "percentage": pct,
        }

    return by_category


def _log_efficiency_summary(
    efficiency: Dict[str, Any],
    grades_by_task_id: Dict[str, Dict[str, Any]],
) -> None:
    """Log a human-readable token efficiency summary."""
    all_scores = [float(g.get("mean", 0.0)) for g in grades_by_task_id.values()]
    mean_score = statistics.mean(all_scores) if all_scores else 0.0

    logger.info("\n%s", "=" * 80)
    logger.info("📊 TOKEN EFFICIENCY SUMMARY")
    logger.info("%s", "=" * 80)
    logger.info(
        "   Total tokens used: %s (input: %s, output: %s)",
        f"{efficiency['total_tokens']:,}",
        f"{efficiency['total_input_tokens']:,}",
        f"{efficiency['total_output_tokens']:,}",
    )
    logger.info("   Total API requests: %s", f"{efficiency['total_requests']:,}")
    if efficiency["total_cost_usd"] > 0:
        logger.info("   Total cost: $%.4f", efficiency["total_cost_usd"])
    logger.info(
        "   Avg tokens/task: %s",
        f"{efficiency['tokens_per_task']:,.0f}",
    )
    logger.info("   Mean score: %.4f", mean_score)
    if efficiency.get("score_per_1k_tokens") is not None:
        logger.info(
            "   Score per 1K tokens: %.4f (higher = more efficient)",
            efficiency["score_per_1k_tokens"],
        )
    if efficiency.get("score_per_dollar") is not None:
        logger.info(
            "   Score per dollar: %.4f (higher = more cost-efficient)",
            efficiency["score_per_dollar"],
        )
    logger.info("%s", "=" * 80)


def _log_category_summary(
    task_entries: List[Dict[str, Any]],
    tasks_by_id: Dict[str, Task],
) -> None:
    """Log a summary grouped by category."""
    category_scores: Dict[str, Dict[str, float]] = {}

    for entry in task_entries:
        task_id = entry["task_id"]
        task = tasks_by_id.get(task_id)
        if not task:
            continue

        category = task.category.upper() if task.category else "UNCATEGORIZED"
        grading = entry.get("grading", {})
        mean_score = float(grading.get("mean", 0.0))
        max_score = 1.0

        if category not in category_scores:
            category_scores[category] = {"earned": 0.0, "possible": 0.0, "task_count": 0}

        category_scores[category]["earned"] += mean_score
        category_scores[category]["possible"] += max_score
        category_scores[category]["task_count"] += 1

    total_earned = sum(c["earned"] for c in category_scores.values())
    total_possible = sum(c["possible"] for c in category_scores.values())
    overall_pct = (total_earned / total_possible * 100) if total_possible > 0 else 0

    logger.info("\n%s", "=" * 80)
    logger.info("🤖 SEGWAYBENCH SCORE SUMMARY")
    logger.info("%s", "=" * 80)
    logger.info("")
    logger.info("   Overall Score: %.1f%% (%.1f / %.1f)", overall_pct, total_earned, total_possible)
    logger.info("")
    logger.info("   %-20s %8s %12s", "CATEGORY", "SCORE", "TASKS")
    logger.info("   %s", "-" * 44)

    for category in sorted(category_scores.keys()):
        data = category_scores[category]
        pct = (data["earned"] / data["possible"] * 100) if data["possible"] > 0 else 0
        task_count = int(data["task_count"])
        task_label = "task" if task_count == 1 else "tasks"

        if pct >= 90:
            indicator = "🟢"
        elif pct >= 70:
            indicator = "🟡"
        else:
            indicator = "🔴"

        logger.info(
            "   %s %-17s %6.1f%% %6d %s",
            indicator,
            category,
            pct,
            task_count,
            task_label,
        )

    logger.info("   %s", "-" * 44)
    logger.info("%s", "=" * 80)


def _write_mock_call_log(workspace_path: str, call_log: List[Dict[str, Any]]) -> None:
    """Write MockLayer call log to workspace/_mock_call_log.json."""
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "_mock_call_log.json"
    log_path.write_text(json.dumps(call_log, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("   Wrote mock call log (%d entries) to %s", len(call_log), log_path)


def _dry_run(runner: "BenchmarkRunner", args: argparse.Namespace, skill_root: Path) -> None:
    """Dry-run mode: prepare workspace for each task using the real prepare_task_workspace,
    activate mock, show all files, don't call any model."""
    task_ids = _select_task_ids(runner.tasks, args.suite)
    tasks_to_run = runner.tasks
    if task_ids is not None:
        tasks_to_run = [t for t in runner.tasks if t.task_id in task_ids]

    run_id = "dry-run"
    skill_dir = skill_root
    # Use a fake agent_id — prepare_task_workspace will use fallback path
    agent_id = "bench-dry-run"

    for i, task in enumerate(tasks_to_run, 1):
        effective_safety = runner.get_effective_safety_level(task)
        print(f"\n{'=' * 70}")
        print(f"📋 Task {i}/{len(tasks_to_run)}: {task.task_id}")
        print(f"   Name:           {task.name}")
        print(f"   Category:       {task.category}")
        print(f"   Safety Level:   {effective_safety} (task default: {task.api_safety_level})")
        print(f"   Timeout:        {task.timeout_seconds}s")
        print(f"   Fixtures:       {task.fixtures or '{}'}")
        print(f"   Mock Responses: {list(task.mock_responses.keys()) if task.mock_responses else '[]'}")
        print(f"   Prompt:         {task.prompt[:80]}...")
        print(f"{'=' * 70}")

        # Use the real prepare_task_workspace
        workspace = prepare_task_workspace(skill_dir, run_id, task, agent_id)

        # Activate mock to show the wrapper
        mock_layer = MockLayer(
            safety_level=effective_safety,
            mock_responses=task.mock_responses,
            fixtures=task.fixtures,
            workspace_path=str(workspace),
        )
        mock_layer.activate()

        # List all files in workspace
        print(f"\n   📁 Workspace: {workspace}")
        print(f"   Files:")
        for f in sorted(workspace.rglob("*")):
            if f.is_file():
                rel = f.relative_to(workspace)
                size = f.stat().st_size
                marker = ""
                if f.name == "segway_auth.py":
                    try:
                        head = f.read_text(encoding="utf-8", errors="ignore")[:200]
                        if "SegwayBench Mock Wrapper" in head:
                            marker = " ← MOCK WRAPPER"
                    except OSError:
                        pass
                elif f.name == "segway_auth.py.orig":
                    marker = " ← ORIGINAL BACKUP"
                elif f.name == ".env":
                    marker = " ← ENV VARS"
                print(f"      {rel} ({size:,} bytes){marker}")

        mock_layer.deactivate()

    print(f"\n{'=' * 70}")
    print(f"✅ Dry-run complete. {len(tasks_to_run)} tasks inspected.")
    print(f"   No models were called. Use without --dry-run to execute.")
    print(f"{'=' * 70}")


def main():
    """Main entry point for the SegwayBench benchmark script."""
    script_dir = Path(__file__).parent
    skill_root = script_dir.parent
    tasks_dir = skill_root / "tasks"

    logger.info("🤖 SegwayBench - Segway Robot Agent Benchmarking")
    print("\n" + "🤖 " * 30)
    print("🤖 " * 30 + "\n")
    logger.info("🤖 Starting SegwayBench 🤖")
    time.sleep(2)

    if not tasks_dir.exists():
        logger.error(f"❌ Tasks directory not found: {tasks_dir}")
        sys.exit(1)

    args = _parse_args()
    if not args.model and not args.register and not args.upload and not args.dry_run:
        logger.error("Missing required argument: --model (unless using --register or --upload)")
        sys.exit(2)

    if args.register:
        try:
            from lib_upload import UploadError, register_token, save_token_config

            token, claim_url = register_token()
            config_path = save_token_config(token, claim_url)
            logger.info("Saved token to %s", config_path)
            if claim_url:
                logger.info("Claim URL: %s", claim_url)
            return
        except UploadError as exc:
            logger.error("Registration failed: %s", exc)
            sys.exit(1)

    if args.upload:
        results_path = Path(args.upload)
        if not results_path.exists():
            logger.error("Results file not found: %s", results_path)
            sys.exit(1)
        try:
            from lib_upload import UploadError, upload_results

            result = upload_results(results_path)
            if result.rank is not None:
                logger.info("Uploaded to leaderboard: rank #%s", result.rank)
            if result.leaderboard_url:
                logger.info("View at: %s", result.leaderboard_url)
            logger.info("Upload complete.")
            return
        except UploadError as exc:
            logger.error("Upload failed: %s", exc)
            sys.exit(1)

    logger.info("🔧 Initializing BenchmarkRunner...")
    runner = BenchmarkRunner(tasks_dir, safety_mode=args.safety_mode)

    logger.info("📂 Loading tasks from directory...")
    runner.load_tasks()

    # --dry-run: prepare workspace for first task, show files, then exit
    if args.dry_run:
        _dry_run(runner, args, skill_root)
        return

    model_slug = slugify_model(args.model)
    run_root = Path("/tmp/segwaybench")
    run_id = _next_run_id(run_root, Path(args.output_dir))
    skill_dir = skill_root
    agent_id = f"bench-{model_slug}"
    agent_workspace = Path(f"/tmp/segwaybench/{run_id}/agent_workspace")

    # Validate model exists before wasting time on tasks
    try:
        validate_model(args.model)
    except ModelValidationError as exc:
        logger.error("❌ %s", exc)
        sys.exit(1)

    ensure_agent_exists(agent_id, args.model, agent_workspace)
    cleanup_agent_sessions(agent_id)

    task_ids = _select_task_ids(runner.tasks, args.suite)
    results = []
    grades_by_task_id = {}
    sanity_task_id = "task_00_sanity"

    tasks_to_run = runner.tasks
    if task_ids is not None:
        tasks_to_run = [task for task in runner.tasks if task.task_id in task_ids]
    tasks_by_id = {task.task_id: task for task in tasks_to_run}

    runs_per_task = max(1, args.runs)
    for i, task in enumerate(tasks_to_run, 1):
        task_grades = []
        task_results = []
        for run_index in range(runs_per_task):
            # Rate-limit delay between tasks (skip before the very first task)
            if args.task_delay > 0 and (i > 1 or run_index > 0):
                logger.info("⏳ Waiting %.1fs between tasks (--task-delay)", args.task_delay)
                time.sleep(args.task_delay)

            logger.info("\n%s", "=" * 80)
            logger.info(
                "📋 Task %s/%s (Run %s/%s)",
                i,
                len(tasks_to_run),
                run_index + 1,
                runs_per_task,
            )
            logger.info("%s", "=" * 80)

            # Recreate agent for each task to ensure full session isolation.
            # Without this, openclaw may carry over conversation context from
            # previous tasks, causing inconsistent results between single-task
            # and batch runs.
            cleanup_agent_sessions(agent_id)
            ensure_agent_exists(agent_id, args.model, agent_workspace)

            # Determine effective safety level
            effective_safety = runner.get_effective_safety_level(task)
            logger.info("   Safety level: %s (task default: %s)", effective_safety, task.api_safety_level)

            # Create and activate MockLayer
            # Prepare workspace first so MockLayer can write the wrapper file
            workspace = prepare_task_workspace(skill_dir, f"{run_id}-{run_index + 1}", task, agent_id)
            workspace_path = str(workspace)

            mock_layer = MockLayer(
                safety_level=effective_safety,
                mock_responses=task.mock_responses,
                fixtures=task.fixtures,
                workspace_path=workspace_path,
            )

            execution_error = None
            try:
                mock_layer.activate()
                logger.info("   MockLayer activated (safety=%s)", effective_safety)

                result = execute_openclaw_task(
                    task=task,
                    agent_id=agent_id,
                    model_id=args.model,
                    run_id=f"{run_id}-{run_index + 1}",
                    timeout_multiplier=args.timeout_multiplier,
                    skill_dir=skill_dir,
                    verbose=args.verbose,
                    workspace_override=workspace,
                )
            except Exception as exc:
                execution_error = str(exc)
                logger.warning("Task execution failed for %s, continuing: %s", task.task_id, exc)
                result = {
                    "agent_id": agent_id,
                    "task_id": task.task_id,
                    "status": "error",
                    "transcript": [],
                    "usage": {},
                    "workspace": "",
                    "exit_code": -1,
                    "timed_out": False,
                    "execution_time": 0.0,
                    "stdout": "",
                    "stderr": execution_error,
                }
            finally:
                mock_layer.deactivate()
                logger.info("   MockLayer deactivated")

            # Call log is read from disk by deactivate()
            call_log = mock_layer.get_call_log()

            # Count mock stats for the result entry
            api_calls = len(call_log)
            mock_intercepted = sum(1 for entry in call_log if entry.get("intercepted"))

            try:
                grade_kwargs = dict(
                    task=task, execution_result=result, skill_dir=skill_dir, verbose=args.verbose
                )
                if args.judge:
                    grade_kwargs["judge_model"] = args.judge
                grade = grade_task(**grade_kwargs)
            except Exception as exc:
                if execution_error:
                    note = f"Execution failed: {execution_error}; Grading failed: {exc}"
                else:
                    note = f"Grading failed: {exc}"
                logger.warning("Task grading failed for %s, continuing: %s", task.task_id, exc)
                grade = GradeResult(
                    task_id=task.task_id,
                    score=0.0,
                    max_score=1.0,
                    grading_type=task.grading_type,
                    breakdown={},
                    notes=note,
                )

            # Attach mock stats to result
            result["api_calls"] = api_calls
            result["mock_intercepted"] = mock_intercepted

            task_grades.append(grade)
            task_results.append(result)
            results.append(result)

            # Log score immediately after grading
            score_pct = grade.score / grade.max_score * 100 if grade.max_score > 0 else 0
            status_emoji = (
                "✅" if grade.score >= grade.max_score else "⚠️" if grade.score > 0 else "❌"
            )
            logger.info(
                "%s Task %s: %.1f/%.1f (%.0f%%) - %s",
                status_emoji,
                task.task_id,
                grade.score,
                grade.max_score,
                score_pct,
                grade.grading_type,
            )
            if grade.notes:
                logger.info("   Notes: %s", grade.notes[:200])

        task_scores = [grade.score for grade in task_grades]
        grades_by_task_id[task.task_id] = {
            "runs": [grade.to_dict() for grade in task_grades],
            "mean": statistics.mean(task_scores),
            "std": statistics.stdev(task_scores) if len(task_scores) > 1 else 0.0,
            "min": min(task_scores),
            "max": max(task_scores),
        }

        all_runs_missing_transcript = all(
            not run_result.get("transcript") for run_result in task_results
        )
        if (
            task.task_id == sanity_task_id
            and grades_by_task_id[task.task_id]["mean"] == 0.0
            and not args.no_fail_fast
            and not all_runs_missing_transcript
        ):
            logger.error(
                "🚨 FAIL FAST: Sanity check (%s) scored 0%%. Aborting benchmark run.",
                sanity_task_id,
            )
            sys.exit(3)
        if task.task_id == sanity_task_id and grades_by_task_id[task.task_id]["mean"] == 0.0:
            if all_runs_missing_transcript:
                logger.warning(
                    "⚠️ Sanity check scored 0%% but transcripts were missing; skipping fail-fast."
                )

    # Build output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    task_entries = [
        {
            "task_id": result["task_id"],
            "category": tasks_by_id[result["task_id"]].category,
            "status": result["status"],
            "timed_out": result["timed_out"],
            "execution_time": result["execution_time"],
            "transcript_length": len(result["transcript"]),
            "transcript": result["transcript"],
            "usage": result.get("usage", {}),
            "workspace": result["workspace"],
            "grading": grades_by_task_id[result["task_id"]],
            "frontmatter": tasks_by_id[result["task_id"]].frontmatter,
            "api_calls": result.get("api_calls", 0),
            "mock_intercepted": result.get("mock_intercepted", 0),
        }
        for result in results
    ]

    efficiency = _compute_efficiency_summary(task_entries, grades_by_task_id)
    by_category = _compute_category_summary(task_entries, tasks_by_id, grades_by_task_id)

    # Compute overall summary
    total_score = sum(grades_by_task_id[tid]["mean"] for tid in grades_by_task_id)
    max_score = float(len(grades_by_task_id))
    score_pct = round(total_score / max_score * 100, 1) if max_score > 0 else 0.0

    aggregate = {
        "model": args.model,
        "benchmark_version": _get_git_version(skill_root),
        "run_id": run_id,
        "timestamp": time.time(),
        "suite": args.suite,
        "safety_mode": args.safety_mode or "per_task",
        "runs_per_task": runs_per_task,
        "tasks": task_entries,
        "summary": {
            "total_tasks": len(grades_by_task_id),
            "total_score": round(total_score, 1),
            "max_score": round(max_score, 1),
            "score_percentage": score_pct,
            "by_category": by_category,
        },
        "efficiency": efficiency,
    }

    output_path = output_dir / f"{run_id}_{model_slug}.json"
    output_path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("📊 Final score: %.2f/%.0f (%.1f%%)", total_score, max_score, score_pct)
    logger.info("Saved results to %s", output_path)
    _log_category_summary(task_entries, tasks_by_id)
    _log_efficiency_summary(efficiency, grades_by_task_id)

    if args.no_upload:
        logger.info("Skipping upload (--no-upload)")
    else:
        try:
            from lib_upload import UploadError, upload_results

            result = upload_results(output_path, official_key=args.official_key)
            if result.submission_id:
                logger.info("Submission ID: %s", result.submission_id)
            if result.rank is not None:
                logger.info("Uploaded to leaderboard: rank #%s", result.rank)
            if result.leaderboard_url:
                logger.info("View at: %s", result.leaderboard_url)
        except UploadError as exc:
            logger.warning("Upload failed: %s", exc)


if __name__ == "__main__":
    main()
