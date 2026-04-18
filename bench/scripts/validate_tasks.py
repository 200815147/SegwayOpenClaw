#!/usr/bin/env python3
"""
Validation script for SegwayBench task files.

Uses TaskLoader to load all task files and verifies:
1. Each task has required fields: id, name, category, grading_type, timeout_seconds,
   api_safety_level, prompt, expected_behavior, grading_criteria, automated_checks
2. Each task's grade function in automated_checks can be compiled
3. Prints a summary of all loaded tasks
"""

import sys
from pathlib import Path

# Add scripts dir to path so we can import lib_tasks
sys.path.insert(0, str(Path(__file__).parent))

from lib_tasks import TaskLoader


def validate_tasks():
    tasks_dir = Path(__file__).parent.parent / "tasks"
    print(f"Loading tasks from: {tasks_dir}")
    print("=" * 70)

    loader = TaskLoader(tasks_dir)
    tasks = loader.load_all_tasks()

    if not tasks:
        print("ERROR: No tasks loaded!")
        return False

    print(f"Loaded {len(tasks)} tasks\n")

    required_fields = [
        "task_id", "name", "category", "grading_type", "timeout_seconds",
        "api_safety_level", "prompt", "expected_behavior", "grading_criteria",
        "automated_checks",
    ]

    all_ok = True
    issues = []

    for task in tasks:
        task_ok = True
        task_issues = []

        # Check required fields
        for field in required_fields:
            value = getattr(task, field, None)
            if value is None or value == "" or value == []:
                task_issues.append(f"  MISSING/EMPTY: {field}")
                task_ok = False

        # Check automated_checks can be compiled
        if task.automated_checks:
            # Extract python code from markdown code block if present
            code = task.automated_checks.strip()
            if code.startswith("```python"):
                code = code[len("```python"):].strip()
            if code.startswith("```"):
                code = code[len("```"):].strip()
            if code.endswith("```"):
                code = code[:-len("```")].strip()

            try:
                compile(code, f"<{task.task_id}>", "exec")
                compile_status = "OK"
            except SyntaxError as e:
                compile_status = f"SYNTAX ERROR: {e}"
                task_issues.append(f"  COMPILE ERROR: {e}")
                task_ok = False
        else:
            compile_status = "N/A (no automated checks)"
            task_issues.append("  MISSING: automated_checks")
            task_ok = False

        # Print task summary
        status = "✓" if task_ok else "✗"
        print(f"{status} {task.task_id}")
        print(f"    Name:            {task.name}")
        print(f"    Category:        {task.category}")
        print(f"    Grading Type:    {task.grading_type}")
        print(f"    Timeout:         {task.timeout_seconds}s")
        print(f"    Safety Level:    {task.api_safety_level}")
        print(f"    Prompt:          {task.prompt[:60]}...")
        print(f"    Criteria Count:  {len(task.grading_criteria)}")
        print(f"    Grade Compile:   {compile_status}")
        if task.fixtures:
            print(f"    Fixtures:        {task.fixtures}")
        if task.mock_responses:
            print(f"    Mock Responses:  {list(task.mock_responses.keys())}")

        if task_issues:
            for issue in task_issues:
                print(issue)
            issues.extend([(task.task_id, i) for i in task_issues])
            all_ok = False

        print()

    # Summary
    print("=" * 70)
    print(f"SUMMARY: {len(tasks)} tasks loaded")

    categories = {}
    for task in tasks:
        categories.setdefault(task.category, []).append(task.task_id)

    print(f"\nCategories ({len(categories)}):")
    for cat, task_ids in sorted(categories.items()):
        print(f"  {cat}: {len(task_ids)} tasks - {', '.join(task_ids)}")

    safety_levels = {}
    for task in tasks:
        safety_levels.setdefault(task.api_safety_level, []).append(task.task_id)

    print(f"\nSafety Levels:")
    for level, task_ids in sorted(safety_levels.items()):
        print(f"  {level}: {len(task_ids)} tasks")

    if issues:
        print(f"\nISSUES FOUND ({len(issues)}):")
        for task_id, issue in issues:
            print(f"  [{task_id}] {issue}")
        print("\nRESULT: FAIL")
        return False
    else:
        print("\nNo issues found.")
        print("\nRESULT: PASS")
        return True


if __name__ == "__main__":
    success = validate_tasks()
    sys.exit(0 if success else 1)
