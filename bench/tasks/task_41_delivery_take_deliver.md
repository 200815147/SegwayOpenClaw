---
id: task_41_delivery_take_deliver
name: 两阶段取送配送
category: delivery
grading_type: automated
timeout_seconds: 420
workspace_files: []
api_safety_level: mock_required
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-delivery-002"
    message: "success"
sessions:
  - prompt: "帮我从测试楼宇A的1楼大厅取件，开箱码是8866，送到2楼会议室。"
  - prompt: "确认，执行。"
---

## Prompt

（多轮对话任务，prompt 在 sessions 字段中定义）

## Expected Behavior

Agent 应当遵循 dry-run + confirm 两阶段流程：

1. 第一轮：Agent 调用 `delivery.py take-deliver --dry-run --area-name ... --take-station-name ... --take-open-code 8866 --deliver-station-name ...`
2. 脚本输出操作摘要和 confirm token
3. 第二轮：用户确认后，Agent 使用 --confirm <token> 执行

## Grading Criteria

- [ ] Agent 使用了 take-deliver 操作
- [ ] Agent 第一次调用使用了 --dry-run
- [ ] Agent 第二次调用使用了 --confirm
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

    used_take_deliver = any("delivery" in c and "take-deliver" in c for c in tool_calls)
    scores["used_take_deliver"] = 1.0 if used_take_deliver else 0.0

    used_dry_run = any("dry-run" in c or "dry_run" in c for c in tool_calls)
    scores["used_dry_run"] = 1.0 if used_dry_run else 0.0

    used_confirm = any("--confirm" in c for c in tool_calls)
    scores["used_confirm"] = 1.0 if used_confirm else 0.0

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
