---
id: task_33_conv_correction
name: 用户纠正对话
category: conversation
grading_type: automated
timeout_seconds: 360
workspace_files: []
api_safety_level: mock_required
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-corrected-001"
    message: "success"
sessions:
  - prompt: "请在楼宇 area-001 创建一个引领运单到站点 station-101。"
  - prompt: "等等，我说错了，目标站点应该是 station-202，不是 station-101。请重新创建。"
---

## Prompt

（多轮对话任务，prompt 在 sessions 字段中定义）

## Expected Behavior

Agent 应当在同一个对话中：

1. 第一轮：调用 task_create guidance 创建运单到 station-101
2. 第二轮：用户纠正目标站点，Agent 应重新调用 task_create guidance，使用 station-202

关键评估点：Agent 能否正确处理用户的纠正指令，使用新的参数重新执行操作。

## Grading Criteria

- [ ] Agent 在第一轮创建了运单（station-101）
- [ ] Agent 在第二轮重新创建了运单（station-202）
- [ ] 第二轮使用了正确的纠正后参数

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

    # Check first creation with station-101
    first_create = any(
        "task_create" in c and "guidance" in c and "station-101" in c
        for c in tool_calls
    )
    scores["first_create"] = 1.0 if first_create else 0.0

    # Check second creation with station-202
    second_create = any(
        "task_create" in c and "guidance" in c and "station-202" in c
        for c in tool_calls
    )
    scores["corrected_create"] = 1.0 if second_create else 0.0

    # Check mock log for the corrected call
    mock_log_path = Path(workspace_path) / "_mock_call_log.json"
    corrected_in_log = False
    if mock_log_path.exists():
        try:
            mock_log = json.loads(mock_log_path.read_text())
            for call in mock_log:
                if call.get("path") == "/api/transport/task/create":
                    body = call.get("body") or {}
                    body_str = json.dumps(body)
                    if "station-202" in body_str:
                        corrected_in_log = True
        except (json.JSONDecodeError, KeyError):
            pass
    scores["correction_applied"] = 1.0 if corrected_in_log else 0.0

    return scores
```
