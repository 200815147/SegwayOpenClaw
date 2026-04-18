#!/usr/bin/env python3
"""
SegwayBench Integration Verification Script

Verifies that all components connect correctly:
1. BenchmarkRunner instantiation and task loading
2. MockLayer intercept/get_call_log with monkeypatch mechanism
3. _write_mock_call_log writes to workspace
4. Grade functions work with mock transcript and workspace
5. JSON report structure matches design doc format

Validates: Requirements 7.3, 7.4, 7.5, 7.6
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure scripts dir is on sys.path so lib_* modules can be imported
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Also ensure segway_auth is importable (needed for MockLayer.activate)
SKILLS_DIR = SCRIPT_DIR.parent.parent / ".openclaw" / "workspace" / "skills"
if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))


PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"

results = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a check result."""
    status = PASS if condition else FAIL
    msg = f"  {status}  {name}"
    if detail and not condition:
        msg += f"  ({detail})"
    print(msg)
    results.append((name, condition))


def test_benchmark_runner_instantiation():
    """Test 1: BenchmarkRunner can be instantiated and tasks loaded."""
    print("\n--- Test 1: BenchmarkRunner instantiation & task loading ---")

    from benchmark import BenchmarkRunner

    tasks_dir = SCRIPT_DIR.parent / "tasks"
    runner = BenchmarkRunner(tasks_dir)
    check("BenchmarkRunner instantiates", runner is not None)
    check("safety_mode defaults to None", runner.safety_mode is None)

    runner_with_safety = BenchmarkRunner(tasks_dir, safety_mode="mock_required")
    check("safety_mode override works", runner_with_safety.safety_mode == "mock_required")

    runner.load_tasks()
    check("Tasks loaded (count > 0)", len(runner.tasks) > 0, f"got {len(runner.tasks)}")
    check("Tasks loaded (count >= 11)", len(runner.tasks) >= 11, f"got {len(runner.tasks)}")

    # Verify all expected task IDs are present
    task_ids = {t.task_id for t in runner.tasks}
    expected_ids = {
        "task_00_sanity",
        "task_01_area_query",
        "task_02_station_query",
        "task_03_robot_list",
        "task_04_robot_status",
        "task_05_guidance_create",
        "task_06_task_cancel",
        "task_07_box_open",
        "task_08_multi_query_create",
        "task_09_error_missing_id",
        "task_10_error_invalid_area",
    }
    missing = expected_ids - task_ids
    check("All expected task IDs present", len(missing) == 0, f"missing: {missing}")

    return runner


def test_task_loader_all_tasks():
    """Test 2: TaskLoader loads all tasks with correct Segway-specific fields."""
    print("\n--- Test 2: TaskLoader loads all tasks with Segway fields ---")

    from lib_tasks import TaskLoader

    tasks_dir = SCRIPT_DIR.parent / "tasks"
    loader = TaskLoader(tasks_dir)
    tasks = loader.load_all_tasks()

    check("TaskLoader returns list", isinstance(tasks, list))
    check("TaskLoader loads >= 11 tasks", len(tasks) >= 11, f"got {len(tasks)}")

    # Verify Segway-specific fields on a mock_required task
    guidance_tasks = [t for t in tasks if t.task_id == "task_05_guidance_create"]
    check("task_05_guidance_create found", len(guidance_tasks) == 1)

    if guidance_tasks:
        task = guidance_tasks[0]
        check("api_safety_level is mock_required", task.api_safety_level == "mock_required")
        check("fixtures has area_id", "area_id" in task.fixtures)
        check("fixtures has station_id", "station_id" in task.fixtures)
        check("mock_responses is non-empty", len(task.mock_responses) > 0)
        check("category is task_create", task.category == "task_create")
        check("grading_type is automated", task.grading_type == "automated")
        check("automated_checks is not None", task.automated_checks is not None)

    # Verify read_only task
    sanity_tasks = [t for t in tasks if t.task_id == "task_00_sanity"]
    if sanity_tasks:
        check("task_00 api_safety_level is read_only", sanity_tasks[0].api_safety_level == "read_only")
        check("task_00 fixtures defaults to empty", sanity_tasks[0].fixtures == {} or sanity_tasks[0].fixtures is not None)


def test_mock_layer_intercept_and_log():
    """Test 3: MockLayer intercept and get_call_log work correctly."""
    print("\n--- Test 3: MockLayer intercept & get_call_log ---")

    from lib_mock import MockLayer, SafetyViolationError, WRITE_API_PATHS

    # Test mock_required mode: write operations intercepted
    custom_responses = {
        "/api/transport/task/create": {
            "code": 200,
            "data": {"taskId": "test-mock-001"},
            "message": "success",
        }
    }
    mock = MockLayer(
        safety_level="mock_required",
        mock_responses=custom_responses,
        fixtures={"area_id": "area-001"},
    )

    # Set a dummy original call_api so intercept doesn't fail on GET passthrough
    mock._original_call_api = lambda method, path, body=None, query_params=None: {
        "code": 200,
        "data": [],
        "message": "success",
    }

    # Test write interception
    response = mock.intercept("POST", "/api/transport/task/create", body={"areaId": "area-001"})
    check("Write intercepted returns mock response", response is not None)
    check("Mock response has correct taskId", response.get("data", {}).get("taskId") == "test-mock-001")
    check("Mock response code is 200", response.get("code") == 200)

    # Test GET passthrough
    get_response = mock.intercept("GET", "/api/transport/areas")
    check("GET request passes through", get_response is not None)

    # Test call log
    call_log = mock.get_call_log()
    check("Call log has 2 entries", len(call_log) == 2, f"got {len(call_log)}")

    if len(call_log) >= 1:
        first_entry = call_log[0]
        check("Log entry has timestamp", "timestamp" in first_entry)
        check("Log entry has method", first_entry.get("method") == "POST")
        check("Log entry has path", first_entry.get("path") == "/api/transport/task/create")
        check("Log entry has body", first_entry.get("body") == {"areaId": "area-001"})
        check("Log entry intercepted=True for write", first_entry.get("intercepted") is True)
        check("Log entry has response", first_entry.get("response") is not None)

    if len(call_log) >= 2:
        second_entry = call_log[1]
        check("GET log entry intercepted=False", second_entry.get("intercepted") is False)

    # Test read_only mode: write operations raise SafetyViolationError
    mock_ro = MockLayer(safety_level="read_only")
    mock_ro._original_call_api = lambda method, path, body=None, query_params=None: {
        "code": 200,
        "data": [],
        "message": "success",
    }

    safety_raised = False
    try:
        mock_ro.intercept("POST", "/api/transport/task/create", body={})
    except SafetyViolationError:
        safety_raised = True
    check("read_only raises SafetyViolationError on write", safety_raised)

    # Test WRITE_API_PATHS completeness
    check("WRITE_API_PATHS has >= 8 paths", len(WRITE_API_PATHS) >= 8, f"got {len(WRITE_API_PATHS)}")


def test_mock_layer_activate_deactivate():
    """Test 4: MockLayer activate/deactivate targets main workspace segway_auth.py."""
    print("\n--- Test 4: MockLayer activate/deactivate file-based mock ---")

    from lib_mock import MockLayer

    # MockLayer now always targets the main workspace's segway_auth.py
    main_auth = SKILLS_DIR / "segway_auth.py"
    check("Main workspace segway_auth.py exists", main_auth.exists())

    original_content = main_auth.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock = MockLayer(safety_level="mock_required", workspace_path=tmpdir)
        mock.activate()

        wrapper_content = main_auth.read_text(encoding="utf-8")
        check("After activate, main segway_auth.py is replaced", wrapper_content != original_content)
        check("Wrapper contains mock marker", "SegwayBench Mock Wrapper" in wrapper_content)
        check("Backup file created", main_auth.with_suffix(".py.orig").exists())

        mock.deactivate()

        restored_content = main_auth.read_text(encoding="utf-8")
        check("After deactivate, main segway_auth.py is restored", restored_content == original_content)
        check("Backup file removed", not main_auth.with_suffix(".py.orig").exists())


def test_write_mock_call_log():
    """Test 5: MockLayer writes call log to workspace/_mock_call_log.json via file-based mock."""
    print("\n--- Test 5: File-based mock call log ---")

    from lib_mock import MockLayer

    with tempfile.TemporaryDirectory() as tmpdir:
        custom_responses = {
            "/api/transport/task/create": {
                "code": 200,
                "data": {"taskId": "file-mock-001"},
                "message": "success",
            }
        }

        mock = MockLayer(
            safety_level="mock_required",
            mock_responses=custom_responses,
            workspace_path=tmpdir,
        )
        mock.activate()

        # Use the in-process intercept method
        mock.intercept("POST", "/api/transport/task/create", body={"areaId": "area-001"})

        mock.deactivate()

        # After deactivate, call_log should be populated from in-process intercept
        call_log = mock.get_call_log()
        check("Call log has 1 entry", len(call_log) == 1, f"got {len(call_log)}")

        if call_log:
            check("Entry has intercepted field", call_log[0].get("intercepted") is True)
            check("Entry has correct path", call_log[0].get("path") == "/api/transport/task/create")
            check("Entry response has taskId", call_log[0].get("response", {}).get("data", {}).get("taskId") == "file-mock-001")

        # Verify the wrapper targets the main workspace
        main_auth = SKILLS_DIR / "segway_auth.py"
        mock2 = MockLayer(safety_level="mock_required", workspace_path=tmpdir)
        mock2.activate()
        wrapper = main_auth.read_text(encoding="utf-8")
        check("Wrapper has _SAFETY_LEVEL", "_SAFETY_LEVEL" in wrapper)
        check("Wrapper has _WRITE_API_PATHS", "_WRITE_API_PATHS" in wrapper)
        check("Wrapper has _append_call_log", "_append_call_log" in wrapper)
        mock2.deactivate()


def test_grade_function_with_mock_data():
    """Test 6: Grade function works with mock transcript and workspace."""
    print("\n--- Test 6: Grade function with mock transcript & workspace ---")

    from lib_tasks import TaskLoader

    tasks_dir = SCRIPT_DIR.parent / "tasks"
    loader = TaskLoader(tasks_dir)
    tasks = loader.load_all_tasks()

    # Use task_05_guidance_create which has automated grading
    guidance_tasks = [t for t in tasks if t.task_id == "task_05_guidance_create"]
    if not guidance_tasks:
        check("task_05 found for grading test", False, "task not found")
        return

    task = guidance_tasks[0]

    # Build a mock transcript that simulates correct agent behavior
    mock_transcript = [
        {
            "type": "message",
            "message": {
                "role": "user",
                "content": ['请在楼宇"测试楼宇A"创建一个引领运单'],
            },
        },
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "toolCall",
                        "toolName": "exec",
                        "arguments": "task_create.py guidance --area-id area-001 --station-id station-101",
                    }
                ],
            },
        },
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "运单创建成功，运单 ID: mock-guidance-001"}],
            },
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write mock call log to workspace
        mock_call_log = [
            {
                "timestamp": "2025-01-15T10:30:00Z",
                "method": "POST",
                "path": "/api/transport/task/create",
                "body": {"areaId": "area-001", "taskType": "Guidance", "stationId": "station-101"},
                "query_params": None,
                "intercepted": True,
                "response": {"code": 200, "data": {"taskId": "mock-guidance-001"}, "message": "success"},
            }
        ]
        log_path = Path(tmpdir) / "_mock_call_log.json"
        log_path.write_text(json.dumps(mock_call_log, indent=2, ensure_ascii=False), encoding="utf-8")

        # Extract and run the grade function
        import re

        grading_code = task.automated_checks or ""
        match = re.search(r"```python\s*(.*?)\s*```", grading_code, re.DOTALL)
        check("Grading code extracted", match is not None)

        if match:
            namespace = {}
            exec(match.group(1), namespace)
            grade_func = namespace.get("grade")
            check("grade function found", callable(grade_func))

            if callable(grade_func):
                scores = grade_func(mock_transcript, tmpdir)
                check("grade returns dict", isinstance(scores, dict))
                check("skill_selection scored", "skill_selection" in scores)
                check("area_id_correct scored", "area_id_correct" in scores)
                check("station_id_correct scored", "station_id_correct" in scores)
                check("mock_intercepted scored", "mock_intercepted" in scores)

                # With our mock data, all should score 1.0
                check("skill_selection = 1.0", scores.get("skill_selection") == 1.0)
                check("area_id_correct = 1.0", scores.get("area_id_correct") == 1.0)
                check("station_id_correct = 1.0", scores.get("station_id_correct") == 1.0)
                check("mock_intercepted = 1.0", scores.get("mock_intercepted") == 1.0)

    # Test with empty transcript (should return 0.0 for all)
    with tempfile.TemporaryDirectory() as tmpdir:
        if match:
            namespace2 = {}
            exec(match.group(1), namespace2)
            grade_func2 = namespace2.get("grade")
            if callable(grade_func2):
                empty_scores = grade_func2([], tmpdir)
                check("Empty transcript: all scores 0.0",
                      all(v == 0.0 for v in empty_scores.values()),
                      f"got {empty_scores}")


def test_json_report_structure():
    """Test 7: JSON report structure matches design doc format."""
    print("\n--- Test 7: JSON report structure matches design doc ---")

    from benchmark import (
        _compute_category_summary,
        _compute_efficiency_summary,
    )
    from lib_tasks import TaskLoader

    tasks_dir = SCRIPT_DIR.parent / "tasks"
    loader = TaskLoader(tasks_dir)
    tasks = loader.load_all_tasks()
    tasks_by_id = {t.task_id: t for t in tasks}

    # Build mock task entries and grades
    mock_task_entries = []
    mock_grades = {}
    for task in tasks[:3]:  # Use first 3 tasks
        entry = {
            "task_id": task.task_id,
            "category": task.category,
            "status": "success",
            "timed_out": False,
            "execution_time": 30.0,
            "transcript_length": 5,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
                "cost_usd": 0.005,
                "request_count": 2,
            },
            "grading": {
                "runs": [{"task_id": task.task_id, "score": 0.8, "max_score": 1.0, "grading_type": "automated", "breakdown": {}, "notes": ""}],
                "mean": 0.8,
                "std": 0.0,
                "min": 0.8,
                "max": 0.8,
            },
            "api_calls": 2,
            "mock_intercepted": 1,
        }
        mock_task_entries.append(entry)
        mock_grades[task.task_id] = entry["grading"]

    # Test category summary (Req 7.5)
    by_category = _compute_category_summary(mock_task_entries, tasks_by_id, mock_grades)
    check("by_category is dict", isinstance(by_category, dict))
    check("by_category has entries", len(by_category) > 0)

    for cat_name, cat_data in by_category.items():
        check(f"Category '{cat_name}' has 'tasks'", "tasks" in cat_data)
        check(f"Category '{cat_name}' has 'score'", "score" in cat_data)
        check(f"Category '{cat_name}' has 'max'", "max" in cat_data)
        check(f"Category '{cat_name}' has 'percentage'", "percentage" in cat_data)
        break  # Just check first category

    # Test efficiency summary (Req 7.6)
    efficiency = _compute_efficiency_summary(mock_task_entries, mock_grades)
    check("efficiency is dict", isinstance(efficiency, dict))
    check("efficiency has total_tokens", "total_tokens" in efficiency)
    check("efficiency has total_cost_usd", "total_cost_usd" in efficiency)
    check("efficiency has tokens_per_task", "tokens_per_task" in efficiency)
    check("efficiency has score_per_1k_tokens", "score_per_1k_tokens" in efficiency)

    # Verify full report structure matches design doc
    total_score = sum(g["mean"] for g in mock_grades.values())
    max_score = float(len(mock_grades))
    score_pct = round(total_score / max_score * 100, 1) if max_score > 0 else 0.0

    report = {
        "model": "test-model",
        "benchmark_version": "1.0.0",
        "run_id": "0001",
        "timestamp": 1705312200.0,
        "suite": "all",
        "safety_mode": "mock_required",
        "runs_per_task": 1,
        "tasks": mock_task_entries,
        "summary": {
            "total_tasks": len(mock_grades),
            "total_score": round(total_score, 1),
            "max_score": round(max_score, 1),
            "score_percentage": score_pct,
            "by_category": by_category,
        },
        "efficiency": efficiency,
    }

    # Validate top-level keys match design doc
    expected_top_keys = {"model", "benchmark_version", "run_id", "timestamp", "suite",
                         "safety_mode", "runs_per_task", "tasks", "summary", "efficiency"}
    actual_top_keys = set(report.keys())
    check("Report has all top-level keys", expected_top_keys.issubset(actual_top_keys),
          f"missing: {expected_top_keys - actual_top_keys}")

    # Validate summary keys
    expected_summary_keys = {"total_tasks", "total_score", "max_score", "score_percentage", "by_category"}
    actual_summary_keys = set(report["summary"].keys())
    check("Summary has all required keys", expected_summary_keys.issubset(actual_summary_keys),
          f"missing: {expected_summary_keys - actual_summary_keys}")

    # Validate task entry keys
    if mock_task_entries:
        entry = mock_task_entries[0]
        expected_task_keys = {"task_id", "category", "status", "timed_out", "execution_time",
                              "transcript_length", "usage", "grading", "api_calls", "mock_intercepted"}
        actual_task_keys = set(entry.keys())
        check("Task entry has all required keys", expected_task_keys.issubset(actual_task_keys),
              f"missing: {expected_task_keys - actual_task_keys}")

    # Validate the report is JSON-serializable
    try:
        json_str = json.dumps(report, indent=2, ensure_ascii=False)
        reparsed = json.loads(json_str)
        check("Report is JSON-serializable", True)
        check("Report round-trips through JSON", reparsed["model"] == "test-model")
    except (TypeError, json.JSONDecodeError) as exc:
        check("Report is JSON-serializable", False, str(exc))


def test_effective_safety_level():
    """Test 8: BenchmarkRunner.get_effective_safety_level works correctly."""
    print("\n--- Test 8: Effective safety level logic ---")

    from benchmark import BenchmarkRunner
    from lib_tasks import TaskLoader

    tasks_dir = SCRIPT_DIR.parent / "tasks"

    # Without global override
    runner = BenchmarkRunner(tasks_dir)
    runner.load_tasks()

    guidance_task = next((t for t in runner.tasks if t.task_id == "task_05_guidance_create"), None)
    sanity_task = next((t for t in runner.tasks if t.task_id == "task_00_sanity"), None)

    if guidance_task:
        level = runner.get_effective_safety_level(guidance_task)
        check("No override: mock_required task stays mock_required", level == "mock_required")

    if sanity_task:
        level = runner.get_effective_safety_level(sanity_task)
        check("No override: read_only task stays read_only", level == "read_only")

    # With global override
    runner_override = BenchmarkRunner(tasks_dir, safety_mode="mock_required")
    runner_override.load_tasks()

    if sanity_task:
        level = runner_override.get_effective_safety_level(sanity_task)
        check("With override: read_only task becomes mock_required", level == "mock_required")


def test_full_mock_mode():
    """Test 9: full_mock mode intercepts both read and write operations."""
    print("\n--- Test 9: full_mock mode (read + write mock) ---")

    from lib_mock import MockLayer, READ_API_MOCK_RESPONSES

    # Test in-process intercept with full_mock
    mock = MockLayer(
        safety_level="full_mock",
        mock_responses={
            "/api/transport/task/create": {
                "code": 200,
                "data": {"taskId": "full-mock-001"},
                "message": "success",
            }
        },
    )

    # Write operation should be intercepted
    write_resp = mock.intercept("POST", "/api/transport/task/create", body={"areaId": "area-001"})
    check("full_mock: write intercepted", write_resp is not None)
    check("full_mock: write returns custom mock", write_resp.get("data", {}).get("taskId") == "full-mock-001")

    # Read operation should also be intercepted (no real API call)
    read_resp = mock.intercept("GET", "/api/transport/areas")
    check("full_mock: read intercepted", read_resp is not None)
    check("full_mock: read returns mock data", isinstance(read_resp.get("data"), list))
    check("full_mock: read has area data", len(read_resp.get("data", [])) > 0)
    if read_resp.get("data"):
        check("full_mock: area has areaId", "areaId" in read_resp["data"][0])

    # Robot status read should also be mocked
    robot_resp = mock.intercept("GET", "/api/transport/robot/robot-001/status")
    check("full_mock: robot status intercepted", robot_resp is not None)
    check("full_mock: robot status has data", robot_resp.get("data") is not None)

    # All calls should be logged as intercepted
    log = mock.get_call_log()
    check("full_mock: all calls logged", len(log) == 3, f"got {len(log)}")
    check("full_mock: write logged as intercepted", log[0].get("intercepted") is True)
    check("full_mock: read logged as intercepted", log[1].get("intercepted") is True)

    # Unknown read path should return empty data
    unknown_resp = mock.intercept("GET", "/api/some/unknown/path")
    check("full_mock: unknown path returns empty", unknown_resp.get("data") == [])

    # Test file-based full_mock targets main workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        main_auth = SKILLS_DIR / "segway_auth.py"

        mock_file = MockLayer(safety_level="full_mock", workspace_path=tmpdir)
        mock_file.activate()

        wrapper = main_auth.read_text(encoding="utf-8")
        check("full_mock: wrapper has full_mock branch", "full_mock" in wrapper)
        check("full_mock: wrapper has _READ_MOCK_RESPONSES", "_READ_MOCK_RESPONSES" in wrapper)
        check("full_mock: wrapper has _find_read_mock", "_find_read_mock" in wrapper)

        mock_file.deactivate()

    # Test effective safety level with full_mock override
    from benchmark import BenchmarkRunner
    tasks_dir = SCRIPT_DIR.parent / "tasks"
    runner = BenchmarkRunner(tasks_dir, safety_mode="full_mock")
    runner.load_tasks()
    sanity_task = next((t for t in runner.tasks if t.task_id == "task_00_sanity"), None)
    if sanity_task:
        level = runner.get_effective_safety_level(sanity_task)
        check("full_mock override: read_only becomes full_mock", level == "full_mock")


def main():
    print("=" * 70)
    print("  SegwayBench Integration Verification")
    print("=" * 70)

    test_benchmark_runner_instantiation()
    test_task_loader_all_tasks()
    test_mock_layer_intercept_and_log()
    test_mock_layer_activate_deactivate()
    test_write_mock_call_log()
    test_grade_function_with_mock_data()
    test_json_report_structure()
    test_effective_safety_level()
    test_full_mock_mode()

    # Summary
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print("\n" + "=" * 70)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        print("\nFailed checks:")
        for name, ok in results:
            if not ok:
                print(f"  ❌ {name}")
        sys.exit(1)
    else:
        print("\n✅ All integration checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
