---
id: task_20_multi_cancel_redeliver
name: 取消运单后重新配送
category: multi_step
grading_type: automated
timeout_seconds: 300
workspace_files: []
api_safety_level: mock_required
fixtures:
  task_id: "mock-task-001"
  robot_id: "robot-001"
mock_responses:
  /api/transport/task/cancel:
    code: 200
    data: null
    message: "success"
  /api/transport/delay/redeliver:
    code: 200
    data: null
    message: "success"
---

## Prompt

机器人 robot-001 上的运单 mock-task-001 出了问题。请先取消这个运单，然后对该机器人上的这个运单执行重新配送操作。

## Expected Behavior

Agent 应当按以下顺序执行：

1. 调用 segway-task-manage skill 的 cancel 操作取消运单 mock-task-001
2. 调用 segway-task-manage skill 的 redeliver 操作，使用 robot-001 和 mock-task-001 执行重新配送
3. 向用户确认两个操作都已完成

## Grading Criteria

- [ ] Agent 调用了 task_manage cancel 取消运单
- [ ] Agent 调用了 task_manage redeliver 重新配送
- [ ] 调用顺序正确（先取消，再重新配送）
- [ ] 参数正确（task-id 和 robot-id）
- [ ] Agent 向用户展示了最终结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    tool_calls = []

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])
            if role == "assistant":
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "toolCall":
                        command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                        tool_calls.append(command)

    called_cancel = any("task_manage" in c and "cancel" in c for c in tool_calls)
    called_redeliver = any("task_manage" in c and "redeliver" in c for c in tool_calls)

    scores["called_cancel"] = 1.0 if called_cancel else 0.0
    scores["called_redeliver"] = 1.0 if called_redeliver else 0.0

    # Check order
    order_correct = False
    if called_cancel and called_redeliver:
        cancel_idx = next((i for i, c in enumerate(tool_calls) if "task_manage" in c and "cancel" in c), -1)
        redeliver_idx = next((i for i, c in enumerate(tool_calls) if "task_manage" in c and "redeliver" in c), -1)
        if cancel_idx < redeliver_idx:
            order_correct = True
    scores["call_order_correct"] = 1.0 if order_correct else 0.0

    # Check parameters
    correct_task_id = any("mock-task-001" in c or "mock_task_001" in c for c in tool_calls)
    correct_robot_id = any("robot-001" in c or "robot_001" in c for c in tool_calls)
    scores["parameter_correctness"] = 1.0 if (correct_task_id and correct_robot_id) else 0.5 if (correct_task_id or correct_robot_id) else 0.0

    has_response = False
    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            if message.get("role") == "assistant":
                content = message.get("content", [])
                if content and len(content) > 0:
                    has_response = True
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
