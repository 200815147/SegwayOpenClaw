---
id: task_40_delivery_guidance
name: 两阶段引领配送
category: delivery
grading_type: automated
timeout_seconds: 420
workspace_files: []
api_safety_level: mock_required
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-delivery-001"
    message: "success"
sessions:
  - prompt: "帮我派一个机器人到测试楼宇A的1楼大厅。"
  - prompt: "确认，执行吧。"
---

## Prompt

（多轮对话任务，prompt 在 sessions 字段中定义）

## Expected Behavior

Agent 应当遵循 dry-run + confirm 两阶段流程：

1. 第一轮：Agent 调用 `delivery.py guidance --dry-run --area-name "测试楼宇A" --station-name "1楼大厅"`
2. 脚本输出操作摘要和 confirm token，Agent 将摘要展示给用户
3. 第二轮：用户确认后，Agent 调用 `delivery.py guidance --confirm <token> --area-name "测试楼宇A" --station-name "1楼大厅"`
4. 脚本验证 token 后创建运单，输出 [TASK_COMPLETE]

关键评估点：Agent 是否正确执行了两阶段流程（先 --dry-run，再 --confirm）。

## Grading Criteria

- [ ] Agent 使用了 segway-delivery 的 guidance 操作
- [ ] Agent 第一次调用使用了 --dry-run 参数
- [ ] Agent 第二次调用使用了 --confirm 参数
- [ ] 运单最终创建成功

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    import json
    from pathlib import Path

    scores = {}
    tool_calls = []

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            if message.get("role") == "assistant":
                for item in message.get("content", []):
                    if isinstance(item, dict) and item.get("type") == "toolCall":
                        command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                        tool_calls.append(command)

    # Check delivery skill used
    used_delivery = any("delivery" in c and "guidance" in c for c in tool_calls)
    scores["used_delivery_skill"] = 1.0 if used_delivery else 0.0

    # Check dry-run phase
    used_dry_run = any("dry-run" in c or "dry_run" in c for c in tool_calls)
    scores["used_dry_run"] = 1.0 if used_dry_run else 0.0

    # Check confirm phase
    used_confirm = any("--confirm" in c for c in tool_calls)
    scores["used_confirm"] = 1.0 if used_confirm else 0.0

    # Check mock log for task creation
    mock_log_path = Path(workspace_path) / "_mock_call_log.json"
    task_created = False
    if mock_log_path.exists():
        try:
            mock_log = json.loads(mock_log_path.read_text())
            task_created = any(
                c.get("path") == "/api/transport/task/create" and c.get("intercepted")
                for c in mock_log
            )
        except (json.JSONDecodeError, KeyError):
            pass
    scores["task_created"] = 1.0 if task_created else 0.0

    return scores
```
