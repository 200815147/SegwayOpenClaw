---
name: segway-bench
description: Run SegwayBench benchmarks to evaluate AI Agent performance on Segway delivery robot tasks. Use when testing model capabilities on robot operations including area queries, station lookups, task creation, task management, box control, multi-step workflows, and error handling scenarios.
metadata:
  author: segway-bench
  version: "1.0.0"
---

# SegwayBench Benchmark Skill

SegwayBench measures how well LLM models perform as the brain of an OpenClaw agent when operating Segway delivery robots. It evaluates agents across real-world robot operation scenarios including querying areas and stations, creating and managing delivery tasks, controlling robot boxes, and handling errors.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenClaw instance (this agent)
- Segway API credentials configured via `segway_auth`

## Quick Start

```bash
cd <skill_directory>

# Run benchmark with a specific model
uv run benchmark.py --model anthropic/claude-sonnet-4

# Run only automated tasks (faster)
uv run benchmark.py --model anthropic/claude-sonnet-4 --suite automated-only

# Run specific tasks
uv run benchmark.py --model anthropic/claude-sonnet-4 --suite task_01_area_query,task_05_guidance_create

# Run with safety mode override (force all tasks to use mock)
uv run benchmark.py --model anthropic/claude-sonnet-4 --safety-mode mock_required

# Skip uploading results
uv run benchmark.py --model anthropic/claude-sonnet-4 --no-upload
```

## Available Task Categories

| Category | Description |
|----------|-------------|
| `area_query` | Area and station lookup queries |
| `robot_query` | Robot list and status queries |
| `task_create` | Delivery task creation (guidance, pickup/delivery) |
| `task_manage` | Task cancellation, priority changes, status queries |
| `box_control` | Robot box open/close and verification |
| `multi_step` | Multi-step workflows combining queries and actions |
| `error_handling` | Error scenarios (missing IDs, invalid parameters) |

## Available Tasks

| Task | Category | Description |
|------|----------|-------------|
| `task_00_sanity` | Basic | Verify agent works |
| `task_01_area_query` | area_query | Query available areas |
| `task_02_station_query` | area_query | Query stations in an area |
| `task_03_robot_list` | robot_query | List all robots |
| `task_04_robot_status` | robot_query | Query robot status |
| `task_05_guidance_create` | task_create | Create guidance delivery task |
| `task_06_task_cancel` | task_manage | Cancel a delivery task |
| `task_07_box_open` | box_control | Open robot box |
| `task_08_multi_query_create` | multi_step | Query then create task |
| `task_09_error_missing_id` | error_handling | Handle missing ID error |
| `task_10_error_invalid_area` | error_handling | Handle invalid area error |

## Command Line Options

| Option | Description |
|--------|-------------|
| `--model` | Model identifier (e.g., `anthropic/claude-sonnet-4`) |
| `--suite` | `all`, `automated-only`, or comma-separated task IDs |
| `--safety-mode` | Global safety level override: `read_only`, `mock_required`, or `live_allowed` |
| `--output-dir` | Results directory (default: `results/`) |
| `--timeout-multiplier` | Scale task timeouts for slower models |
| `--runs` | Number of runs per task for averaging |
| `--no-upload` | Skip uploading to leaderboard |

## Safety Modes

- **read_only**: Allow real API calls for GET/query operations only
- **mock_required**: Intercept all write operations and return mock responses (recommended for safe testing)
- **live_allowed**: Allow real write operations (use with caution)

Use `--safety-mode mock_required` to globally override all tasks to use mock responses for write operations.

## Results

Results are saved as JSON in the output directory:

```bash
# View task scores
jq '.tasks[] | {task_id, score: .grading.mean}' results/0001_anthropic-claude-sonnet-4.json

# Show scores by category
jq '.summary.by_category' results/*.json

# Show failed tasks
jq '.tasks[] | select(.grading.mean < 0.5)' results/*.json
```

## Adding Custom Tasks

Create a markdown file in `tasks/` following the task template. Each task needs:

- YAML frontmatter (id, name, category, grading_type, timeout, api_safety_level)
- Optional fixtures and mock_responses in frontmatter
- Prompt section (Chinese natural language)
- Expected behavior
- Grading criteria
- Automated checks (Python grading function)
