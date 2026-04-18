# SegwayBench 技术文档

## 1. 项目概述

SegwayBench 是一套针对 Segway 配送机器人的 AI Agent 评测系统。它通过预定义的 Markdown 任务文件描述自然语言指令和评分标准，驱动 OpenClaw Agent 调用 Segway skill 执行机器人操作，并通过自动化评分函数对执行结果进行量化评估。

核心目标：衡量不同 LLM 模型作为 OpenClaw Agent 大脑时，操作 Segway 配送机器人的能力。

## 2. 目录结构

```
segway-bench/
├── SKILL.md                           # OpenClaw skill 描述文件
├── scripts/
│   ├── benchmark.py                   # 评测运行器主入口
│   ├── lib_tasks.py                   # Task 加载与解析
│   ├── lib_grading.py                 # 评分引擎
│   ├── lib_agent.py                   # Agent 执行辅助（多 provider 支持）
│   ├── lib_mock.py                    # Mock 层实现（文件级替换）
│   ├── lib_upload.py                  # 结果上传
│   ├── validate_tasks.py             # 任务文件格式校验
│   ├── compare_results.py            # 跨模型对比报告
│   └── verify_integration.py         # 集成测试
├── tasks/
│   ├── task_00_sanity.md              # 健全性检查
│   ├── task_01_area_query.md          # 楼宇查询
│   ├── task_02_station_query.md       # 站点查询
│   ├── task_03_robot_list.md          # 机器人列表
│   ├── task_04_robot_status.md        # 机器人状态
│   ├── task_05_guidance_create.md     # 引领运单创建
│   ├── task_06_task_cancel.md         # 运单取消
│   ├── task_07_box_open.md            # 开箱操作
│   ├── task_08_multi_query_create.md  # 多步骤：查询+创建
│   ├── task_09_error_missing_id.md    # 错误处理：缺失 ID
│   ├── task_10_error_invalid_area.md  # 错误处理：无效楼宇
│   ├── task_11_robot_location.md      # 机器人位置查询
│   ├── task_12_robot_sort_list.md     # 楼宇机器人排序列表
│   ├── task_13_take_deliver_create.md # 取送运单创建
│   ├── task_14_task_status.md         # 运单状态查询
│   ├── task_15_task_history.md        # 历史运单查询
│   ├── task_16_task_priority.md       # 运单优先级修改
│   ├── task_17_box_close.md           # 关箱操作
│   ├── task_18_box_info.md            # 箱门信息查询
│   ├── task_19_map_query.md           # 楼层地图查询
│   ├── task_20_multi_cancel_redeliver.md # 多步骤：取消+重新配送
│   └── task_21_error_no_robot.md      # 错误处理：无可用机器人
├── assets/
│   ├── areas.json                     # 楼宇列表快照
│   ├── stations.json                  # 站点列表快照
│   ├── robots.json                    # 机器人列表快照
│   └── mock_responses.json            # 默认 Mock 响应模板
└── results/                           # 评测结果输出目录
```

## 3. 执行流程

### 3.1 整体调用链路

```
benchmark.py
  │
  ├─ 1. 解析命令行参数（--model, --suite, --safety-mode 等）
  ├─ 2. 验证模型 ID（支持 OpenRouter / Google / NVIDIA 等多 provider）
  ├─ 3. 创建 OpenClaw Agent（openclaw agents add）
  ├─ 4. 加载所有任务文件（TaskLoader）
  │
  └─ 5. 逐任务执行循环：
       │
       ├─ a. prepare_task_workspace()
       │     - 清空 workspace
       │     - 复制 segway-* skill 目录到 workspace/skills/
       │     - 复制 segway_auth.py 到 workspace/skills/
       │
       ├─ b. MockLayer.activate()
       │     - 备份 workspace/skills/segway_auth.py → .py.orig
       │     - 生成包装版 segway_auth.py（内嵌 mock 逻辑）
       │
       ├─ c. execute_openclaw_task()
       │     - subprocess: openclaw agent --message "<prompt>"
       │       └─ openclaw 匹配 skill → 启动子进程执行脚本
       │           └─ python area_map.py areas
       │               └─ import segway_auth  ← 加载的是包装版
       │               └─ segway_auth.call_api()  ← mock 逻辑生效
       │
       ├─ d. MockLayer.deactivate()
       │     - 从 .py.orig 恢复原始 segway_auth.py
       │     - 从 _mock_call_log.json 读取调用日志
       │
       ├─ e. grade_task()
       │     - 执行任务文件中内嵌的 grade() 函数
       │     - 分析 transcript + mock 调用日志
       │     - 返回 GradeResult（各维度分数）
       │
       └─ f. 汇总结果 → JSON 报告
```

### 3.2 单任务执行时序

```
benchmark.py          OpenClaw CLI          Skill 脚本           Segway API
    │                     │                     │                    │
    │─prepare_workspace──▶│                     │                    │
    │─MockLayer.activate─▶│                     │                    │
    │  (替换segway_auth)  │                     │                    │
    │                     │                     │                    │
    │─openclaw agent ────▶│                     │                    │
    │  --message "..."    │─匹配skill──────────▶│                    │
    │                     │                     │─import segway_auth │
    │                     │                     │  (加载包装版)       │
    │                     │                     │                    │
    │                     │                     │─call_api(GET,...)──▶│ (读操作放行)
    │                     │                     │◀──真实响应──────────│
    │                     │                     │                    │
    │                     │                     │─call_api(POST,...) │
    │                     │                     │  (写操作被拦截)     │
    │                     │                     │◀──mock 响应         │
    │                     │                     │                    │
    │                     │                     │─写入_mock_call_log │
    │                     │                     │                    │
    │◀──transcript────────│                     │                    │
    │                     │                     │                    │
    │─MockLayer.deactivate│                     │                    │
    │  (恢复原始文件)      │                     │                    │
    │─读取call_log────────│                     │                    │
    │─grade_task()────────│                     │                    │
```


## 4. Mock 层机制

### 4.1 问题背景

benchmark.py 通过 `subprocess` 调用 `openclaw agent --message`，openclaw 再启动子进程执行 skill 脚本。每个 skill 脚本是独立的 Python 进程，自己 `import segway_auth` 并调用 `call_api()`。因此传统的 Python monkeypatch 无法跨进程生效。

### 4.2 文件级替换方案

MockLayer 采用文件级替换实现跨进程 mock：

1. **activate()** 阶段：
   - 将 workspace 中的 `segway_auth.py` 备份为 `segway_auth.py.orig`
   - 生成一个包装版 `segway_auth.py` 写入原位置
   - 包装版通过 `exec()` 加载原始代码，保留所有函数（`gmt_time`, `gen_authorization`, `get_config`, `send_request`）
   - 用带 mock 逻辑的 `call_api()` 覆盖原版

2. **包装版 call_api() 逻辑**：
   ```
   if 写操作 + mock_required → 返回预定义 mock 响应
   if 写操作 + read_only    → 抛出 RuntimeError（安全违规）
   if full_mock             → 所有请求返回 mock 响应（读写均拦截）
   if 读操作               → 调用原始真实 API
   if live_allowed          → 所有请求调用真实 API
   ```

3. **调用日志**：
   - 每次 `call_api()` 调用都追加写入 `workspace/_mock_call_log.json`
   - 使用 `fcntl.flock` 文件锁保证并发安全
   - 日志格式：`{timestamp, method, path, body, query_params, intercepted, response}`

4. **deactivate()** 阶段：
   - 从 `.py.orig` 恢复原始 `segway_auth.py`
   - 从 `_mock_call_log.json` 读取调用日志到内存供评分使用

### 4.3 三级安全模式

| 安全级别 | 读操作（GET） | 写操作（POST） | 适用场景 |
|---------|-------------|--------------|---------|
| `read_only` | 放行到真实 API | 阻断并报错 | 只读查询类任务 |
| `mock_required` | 放行到真实 API | 拦截并返回 mock 响应 | 写操作类任务（推荐） |
| `full_mock` | 拦截并返回 mock 响应 | 拦截并返回 mock 响应 | 完全离线评测，不依赖真实 API |
| `live_allowed` | 放行到真实 API | 放行到真实 API | 需要真实写操作的场景 |

写操作 API 路径集合（`WRITE_API_PATHS`）：

| API 路径 | 操作 |
|---------|------|
| `/api/transport/task/create` | 运单创建 |
| `/api/transport/task/cancel` | 运单取消 |
| `/api/transport/task/priority` | 优先级修改 |
| `/api/transport/robot/boxs/open` | 开箱 |
| `/api/transport/robot/boxs/close` | 关箱 |
| `/api/transport/task/put/verify` | 取物确认 |
| `/api/transport/task/take/verify` | 取件确认 |
| `/api/transport/delay/redeliver` | 重新配送 |

### 4.4 Mock 响应数据

每个任务可在 YAML frontmatter 中通过 `mock_responses` 字段自定义 mock 响应。未定义时使用默认响应模板（`DEFAULT_MOCK_RESPONSES`）。

默认响应示例：
```json
{
  "/api/transport/task/create": {
    "code": 200,
    "data": {"taskId": "mock-task-001"},
    "message": "success"
  }
}
```

错误场景响应（用于错误处理类任务）：
```json
{
  "invalid_area_id": {"code": 9001, "data": null, "message": "楼宇不存在"},
  "no_robot_available": {"code": 9012, "data": null, "message": "无可用机器人"},
  "task_not_found": {"code": 9002, "data": null, "message": "运单不存在"}
}
```

## 5. 任务文件格式

### 5.1 YAML Frontmatter

每个任务文件是一个 Markdown 文件，包含 YAML frontmatter 和多个段落：

```yaml
---
id: task_05_guidance_create          # 唯一任务 ID
name: 创建引领运单                     # 任务名称
category: task_create                 # 分类
grading_type: automated               # 评分类型：automated | llm_judge | hybrid
timeout_seconds: 180                  # 超时时间（秒）
workspace_files: []                   # 需要预置到 workspace 的文件
api_safety_level: mock_required       # 安全级别
fixtures:                             # 预设测试数据
  area_id: "area-001"
  station_id: "station-101"
mock_responses:                       # 自定义 mock 响应（可选）
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-guidance-001"
    message: "success"
---
```

### 5.2 Markdown 段落

| 段落 | 说明 |
|-----|------|
| `## Prompt` | 发送给 Agent 的中文自然语言指令 |
| `## Expected Behavior` | Agent 应执行的步骤描述 |
| `## Grading Criteria` | checklist 格式的评分条件 |
| `## Automated Checks` | 内嵌的 Python 评分函数 |
| `## LLM Judge Rubric` | LLM 裁判评分标准（llm_judge/hybrid 类型时） |

### 5.3 评分函数签名

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    Args:
        transcript: JSONL 对话记录列表，每条记录包含 type、message 等字段
        workspace_path: 任务工作空间路径，可读取 _mock_call_log.json

    Returns:
        Dict[str, float]，评分维度名称到分数（0.0~1.0）的映射
        例如: {"skill_selection": 1.0, "parameter_correctness": 0.5}
    """
```

最终分数 = 所有维度分数的算术平均值，归一化到 0.0~1.0 范围。


## 6. 任务清单

### 6.1 基础检查

| 任务 ID | 名称 | 安全级别 | 评分维度 |
|--------|------|---------|---------|
| task_00_sanity | 健全性检查 | read_only | agent_responded |

Prompt: "请说'你好，我已准备就绪！'来确认你可以正常响应。"

仅验证 Agent 能否正常响应，任何回复即得满分。作为 fail-fast 检查点，如果此任务得 0 分，默认终止后续任务。

### 6.2 只读查询类（read_only）

| 任务 ID | 名称 | 评分维度 | 预期 Skill 调用 |
|--------|------|---------|----------------|
| task_01_area_query | 楼宇查询 | skill_selection, response_provided | `area_map.py areas` |
| task_02_station_query | 站点查询 | skill_selection, parameter_correctness, response_provided | `area_map.py stations --area-id area-001` |
| task_03_robot_list | 机器人列表 | skill_selection, response_provided | `robot.py list` |
| task_04_robot_status | 机器人状态 | skill_selection, parameter_correctness, response_provided | `robot.py status --robot-id robot-001` |
| task_11_robot_location | 机器人位置查询 | skill_selection, area_id_correct, robot_id_correct, response_provided | `robot.py location --area-id area-001 --robot-id robot-001` |
| task_12_robot_sort_list | 楼宇机器人排序列表 | skill_selection, parameter_correctness, response_provided | `robot.py sort-list --area-id area-001` |
| task_14_task_status | 运单状态查询 | skill_selection, parameter_correctness, response_provided | `task_manage.py status --task-id task-20250401-001` |
| task_15_task_history | 历史运单查询 | skill_selection, start_time_correct, end_time_correct, response_provided | `task_manage.py history --start-time ... --end-time ...` |
| task_18_box_info | 箱门信息查询 | skill_selection, parameter_correctness, response_provided | `box_control.py info --robot-id robot-001` |
| task_19_map_query | 楼层地图查询 | skill_selection, parameter_correctness, response_provided | `area_map.py map-list --area-id area-001` |

这些任务直接调用真实 Segway API 的 GET 接口，不涉及写操作。

### 6.3 写操作类（mock_required）

| 任务 ID | 名称 | 评分维度 | 预期 Skill 调用 |
|--------|------|---------|----------------|
| task_05_guidance_create | 创建引领运单 | skill_selection, area_id_correct, station_id_correct, mock_intercepted | `task_create.py guidance --area-id area-001 --station-id station-101` |
| task_06_task_cancel | 运单取消 | skill_selection, parameter_correctness, response_provided | `task_manage.py cancel --task-id mock-task-001` |
| task_07_box_open | 开箱操作 | skill_selection, robot_id_correct, box_indexes_provided, response_provided | `box_control.py open --robot-id robot-001 --box-indexes 1,2` |
| task_13_take_deliver_create | 创建取送运单 | skill_selection, area_id_correct, take_params_correct, deliver_params_correct, mock_intercepted | `task_create.py take-deliver --area-id area-001 --take-station-id station-101 --take-open-code 8866 --deliver-station-id station-202` |
| task_16_task_priority | 运单优先级修改 | skill_selection, task_id_correct, priority_level_correct, response_provided | `task_manage.py priority --task-id mock-task-001 --priority-level 55` |
| task_17_box_close | 关箱操作 | skill_selection, robot_id_correct, box_indexes_provided, response_provided | `box_control.py close --robot-id robot-001 --box-indexes 1,2` |

写操作被 Mock 层拦截，返回预定义的成功响应。task_05 额外检查 `_mock_call_log.json` 中是否有被拦截的写操作记录。

### 6.4 多步骤复合任务

| 任务 ID | 名称 | 超时 | 评分维度 |
|--------|------|------|---------|
| task_08_multi_query_create | 查询并创建引领运单 | 300s | called_areas, called_stations, called_guidance, call_order_correct, parameter_passing, reasoning_correctness, response_provided |
| task_20_multi_cancel_redeliver | 取消运单后重新配送 | 300s | called_cancel, called_redeliver, call_order_correct, parameter_correctness, response_provided |

Prompt: "请先查询所有可用楼宇列表，找到名为'测试楼宇A'的楼宇，然后查询该楼宇下的站点列表，最后创建一个引领运单到'1楼大厅'站点。"

评估要点：
- Agent 是否按正确顺序调用了三个 skill（areas → stations → guidance）
- 后续调用的参数是否引用了前序调用返回的数据
- Agent 是否跳过查询步骤直接使用硬编码参数（推理正确性扣分）

### 6.5 错误处理类

| 任务 ID | 名称 | 评分维度 |
|--------|------|---------|
| task_09_error_missing_id | 缺失 ID 错误处理 | asked_for_missing_info, did_not_call_blindly |
| task_10_error_invalid_area | 无效楼宇 ID 错误处理 | attempted_query, communicated_error, recovery_suggestion |
| task_21_error_no_robot | 无可用机器人错误处理 | attempted_create, communicated_error, helpful_response |

- task_09: Prompt 故意不提供必要参数，检查 Agent 是否主动询问而非盲目调用 API
- task_10: Mock 层返回错误码 9001，检查 Agent 是否正确解读并传达错误信息
- task_21: Mock 层返回错误码 9012（无可用机器人），检查 Agent 是否正确传达错误并给出建议

## 7. 评分系统

### 7.1 评分流程

```
grade_task(task, execution_result)
  │
  ├─ grading_type == "automated"
  │   └─ 从 task.automated_checks 提取 Python 代码
  │   └─ exec() 执行，获取 grade() 函数
  │   └─ grade(transcript, workspace_path) → Dict[str, float]
  │   └─ 总分 = 各维度分数的算术平均值
  │
  ├─ grading_type == "llm_judge"
  │   └─ 将 transcript 摘要 + rubric 发送给 LLM 裁判模型
  │   └─ 解析 LLM 返回的 JSON 评分
  │
  └─ grading_type == "hybrid"
      └─ 同时执行 automated 和 llm_judge
      └─ 按 grading_weights 加权合并
```

### 7.2 GradeResult 结构

```python
@dataclass
class GradeResult:
    task_id: str           # 任务 ID
    score: float           # 总分（0.0~1.0）
    max_score: float       # 满分（固定 1.0）
    grading_type: str      # automated | llm_judge | hybrid
    breakdown: Dict        # 各维度分数明细
    notes: str             # 评分备注
```

每个任务的总分范围是 0.0 到 1.0（归一化）。例如 task_06 有 3 个评分维度（skill_selection, parameter_correctness, response_provided），如果全部满分则总分 = (1.0 + 1.0 + 1.0) / 3 = 1.0。

### 7.3 Transcript 结构

评分函数接收的 transcript 是 JSONL 对话记录列表，每条记录格式：

```json
{
  "type": "message",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "toolCall",
        "toolName": "exec",
        "arguments": "task_create.py guidance --area-id area-001 --station-id station-101"
      },
      {
        "type": "text",
        "text": "运单创建成功，运单 ID: mock-guidance-001"
      }
    ]
  }
}
```

评分函数通过遍历 transcript 中的 `toolCall` 事件来判断 Agent 调用了哪些 skill 和参数。

## 8. 多 Provider 支持

### 8.1 模型验证

`validate_model()` 支持多种 provider 的模型验证：

1. 先查本地 openclaw `models.json` 配置（支持 nvidia、google、ztf 等所有已配置 provider）
2. 如果是 openrouter 或未指定 provider 的 `org/model` 格式，走 OpenRouter API 在线验证
3. 其他已知 provider 但本地没配置的，放行并警告

### 8.2 支持的 Provider

| Provider | 模型 ID 格式 | 示例 |
|----------|-------------|------|
| OpenRouter | `openrouter/org/model` | `openrouter/anthropic/claude-sonnet-4` |
| Google | `google/model` | `google/gemini-2.5-flash` |
| NVIDIA | `nvidia/org/model` | `nvidia/deepseek-ai/deepseek-v3.2` |
| 自定义 | `provider/model` | `ztf/gemini-3.1-flash-lite-preview` |
| 裸模型 | `org/model` | `anthropic/claude-sonnet-4`（默认走 OpenRouter） |

### 8.3 使用示例

```bash
# OpenRouter
python3 benchmark.py --model openrouter/anthropic/claude-sonnet-4

# Google
python3 benchmark.py --model google/gemini-2.5-flash

# NVIDIA
python3 benchmark.py --model nvidia/deepseek-ai/deepseek-v3.2

# 裸模型（默认走 OpenRouter 验证）
python3 benchmark.py --model anthropic/claude-sonnet-4
```

## 9. Workspace 准备

### 9.1 prepare_task_workspace 流程

每个任务执行前，`prepare_task_workspace()` 会：

1. 获取 Agent 的 workspace 路径
2. 清空 workspace（防止上一个任务的残留文件污染）
3. 写入任务定义的 `workspace_files`（如有）
4. 删除引导文件（BOOTSTRAP.md, SOUL.md 等，防止触发 onboarding 流程）
5. 从主 workspace 复制 `segway_auth.py` 到 `workspace/skills/`
6. 从主 workspace 复制所有 `segway-*` 开头的 skill 目录到 `workspace/skills/`

只复制 segway 相关的 skill，不复制其他无关 skill（如 tavily-search、find-skills 等）。

## 10. 命令行参数

```
python3 benchmark.py [OPTIONS]
```

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `--model` | str | 必填 | 模型标识符 |
| `--suite` | str | `all` | 任务选择：`all`、`automated-only`、逗号分隔的任务 ID |
| `--safety-mode` | str | 无 | 全局安全级别覆盖：`read_only`、`mock_required`、`live_allowed` |
| `--output-dir` | str | `results` | 结果输出目录 |
| `--timeout-multiplier` | float | 1.0 | 超时倍率（慢模型可调大） |
| `--runs` | int | 1 | 每个任务运行次数（用于取平均） |
| `--judge` | str | 无 | LLM 裁判模型（默认 `openrouter/anthropic/claude-opus-4.5`） |
| `--verbose` / `-v` | flag | false | 详细日志（显示 transcript、workspace 文件等） |
| `--no-upload` | flag | false | 跳过上传到排行榜 |
| `--no-fail-fast` | flag | false | 即使 sanity check 得 0 分也继续运行 |
| `--register` | flag | false | 注册新的 API token |
| `--upload` | str | 无 | 上传已有的结果 JSON 文件 |
| `--official-key` | str | 无 | 官方提交密钥 |

## 11. 输出报告格式

评测结果以 JSON 格式保存到 `results/` 目录：

```json
{
  "model": "openrouter/anthropic/claude-sonnet-4",
  "benchmark_version": "1.0.0",
  "run_id": "0001",
  "timestamp": 1705312200.0,
  "suite": "all",
  "safety_mode": "mock_required",
  "runs_per_task": 1,
  "tasks": [
    {
      "task_id": "task_05_guidance_create",
      "category": "task_create",
      "status": "success",
      "timed_out": false,
      "execution_time": 45.2,
      "transcript_length": 12,
      "usage": {
        "input_tokens": 3200,
        "output_tokens": 850,
        "total_tokens": 4050,
        "cost_usd": 0.012,
        "request_count": 3
      },
      "grading": {
        "runs": [{"task_id": "...", "score": 0.85, "max_score": 1.0, ...}],
        "mean": 0.85,
        "std": 0.0,
        "min": 0.85,
        "max": 0.85
      },
      "api_calls": 2,
      "mock_intercepted": 1
    }
  ],
  "summary": {
    "total_tasks": 22,
    "total_score": 19.5,
    "max_score": 22.0,
    "score_percentage": 88.6,
    "by_category": {
      "area_query": {"tasks": 2, "score": 1.9, "max": 2.0, "percentage": 95.0},
      "robot_query": {"tasks": 2, "score": 1.7, "max": 2.0, "percentage": 85.0}
    }
  },
  "efficiency": {
    "total_tokens": 52000,
    "total_cost_usd": 0.156,
    "tokens_per_task": 4727,
    "score_per_1k_tokens": 0.177
  }
}
```

## 12. 工具脚本

### 12.1 validate_tasks.py

校验所有任务文件的格式正确性：

```bash
python3 scripts/validate_tasks.py
```

检查项：
- 必填字段完整性（id, name, category, grading_type, timeout_seconds, api_safety_level, prompt, expected_behavior, grading_criteria, automated_checks）
- grade 函数语法正确性（compile 检查）
- 输出各任务的摘要信息

### 12.2 verify_integration.py

运行 76 项集成检查，验证所有组件正确连接：

```bash
python3 scripts/verify_integration.py
```

覆盖范围：
- BenchmarkRunner 实例化和任务加载
- TaskLoader 解析 Segway 扩展字段
- MockLayer 拦截逻辑和调用日志
- MockLayer 文件级替换机制（activate/deactivate）
- 评分函数执行
- JSON 报告结构
- 安全级别覆盖逻辑

### 12.3 compare_results.py

跨模型对比报告工具，读取 `results/` 下的 `merged_*.json` 生成对比表格：

```bash
# 对比所有已合并的结果
python3 scripts/compare_results.py

# 指定文件
python3 scripts/compare_results.py results/merged_a.json results/merged_b.json

# 输出 Markdown 报告
python3 scripts/compare_results.py --markdown report.md

# 只对比特定分类
python3 scripts/compare_results.py --category robot_query,task_create
```

输出四个维度的对比：总分、分类得分率、逐任务得分、效率（tokens/任务、得分/1K tokens）。

### 12.4 merge_results.py

将同一模型的多个单任务结果合并为一个汇总 JSON：

```bash
python3 scripts/merge_results.py [results_dir]
```

## 13. 添加新任务

在 `tasks/` 目录下创建新的 Markdown 文件，遵循以下模板：

```markdown
---
id: task_XX_your_task
name: 你的任务名称
category: area_query          # 选择合适的分类
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: mock_required  # 或 read_only
fixtures:                        # 可选：预设测试数据
  some_id: "value"
mock_responses:                  # 可选：自定义 mock 响应
  /api/some/path:
    code: 200
    data: null
    message: "success"
---

## Prompt

用中文描述发送给 Agent 的指令。

## Expected Behavior

描述 Agent 应执行的步骤。

## Grading Criteria

- [ ] 评分条件 1
- [ ] 评分条件 2

## Automated Checks

\```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    # 你的评分逻辑
    scores["dimension_name"] = 1.0 if condition else 0.0
    return scores
\```
```

添加后运行 `validate_tasks.py` 验证格式正确性。
