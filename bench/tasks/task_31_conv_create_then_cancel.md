---
id: task_31_conv_create_then_cancel
name: 创建后取消对话
category: conversation
grading_type: automated
timeout_seconds: 360
workspace_files: []
api_safety_level: mock_required
fixtures:
  area_id: "area-001"
  station_id: "station-101"
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-conv-task-001"
    message: "success"
  /api/transport/task/cancel:
    code: 200
    data: null
    message: "success"
sessions:
  - prompt: "请在楼宇 area-001 创建一个引领运单，目标站点 station-101。"
  - prompt: "刚才创建的那个运单，帮我取消掉。"
---

## Prompt

（多轮对话任务，prompt 在 sessions 字段中定义）

## Expected Behavior

Agent 应当在同一个对话中：

1. 第一轮：调用 task_create guidance 创建运单，获得 taskId
2. 第二轮：利用上下文中的 taskId（mock-conv-task-001），调用 task_manage cancel 取消运单

关键评估点：Agent 能否从第一轮的创建结果中提取 taskId，在第二轮中正确使用。

## Grading Criteria

- [ ] Agent 在第一轮调用了 guidance 创建运单
- [ ] Agent 在第二轮调用了 cancel 取消运单
- [ ] Agent 在取消时使用了正确的 taskId（来自创建结果）

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

    called_create = any("task_create" in c and "guidance" in c for c in tool_calls)
    called_cancel = any("task_manage" in c and "cancel" in c for c in tool_calls)

    scores["called_create"] = 1.0 if called_create else 0.0
    scores["called_cancel"] = 1.0 if called_cancel else 0.0

    # Check if cancel used the taskId from create result
    task_id_used = any("mock-conv-task-001" in c for c in tool_calls)
    scores["context_task_id"] = 1.0 if (called_cancel and task_id_used) else 0.0

    # Check mock log for both operations
    mock_log_path = Path(workspace_path) / "_mock_call_log.json"
    both_intercepted = False
    if mock_log_path.exists():
        try:
            mock_log = json.loads(mock_log_path.read_text())
            has_create = any(c.get("path") == "/api/transport/task/create" and c.get("intercepted") for c in mock_log)
            has_cancel = any(c.get("path") == "/api/transport/task/cancel" and c.get("intercepted") for c in mock_log)
            both_intercepted = has_create and has_cancel
        except (json.JSONDecodeError, KeyError):
            pass
    scores["both_operations_executed"] = 1.0 if both_intercepted else 0.0

    return scores
```
