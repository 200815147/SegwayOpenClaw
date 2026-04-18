---
id: task_16_task_priority
name: 运单优先级修改
category: task_manage
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: mock_required
fixtures:
  task_id: "mock-task-001"
  priority_level: 55
---

## Prompt

请将运单 mock-task-001 的优先级调整为 55。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-task-manage skill 的 priority 操作
2. 执行 `task_manage.py priority --task-id mock-task-001 --priority-level 55` 命令修改优先级
3. Mock 层将拦截写操作并返回模拟的成功响应
4. Agent 向用户确认优先级已成功修改

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-task-manage 的 priority 操作）
- [ ] Agent 使用了正确的 task-id 参数（mock-task-001）
- [ ] Agent 使用了正确的 priority-level 参数（55）
- [ ] Agent 向用户确认了操作结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_priority = False
    correct_task_id = False
    correct_level = False
    has_response = False

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])
            if role == "assistant":
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "toolCall":
                        command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                        if "task_manage" in command and "priority" in command:
                            called_priority = True
                        if "mock-task-001" in command or "mock_task_001" in command:
                            correct_task_id = True
                        if "55" in command:
                            correct_level = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_priority else 0.0
    scores["task_id_correct"] = 1.0 if correct_task_id else 0.0
    scores["priority_level_correct"] = 1.0 if correct_level else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
