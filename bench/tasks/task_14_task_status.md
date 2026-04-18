---
id: task_14_task_status
name: 运单状态查询
category: task_manage
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  task_id: "task-20250401-001"
---

## Prompt

请查询运单 task-20250401-001 的当前状态。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-task-manage skill 的 status 操作
2. 执行 `task_manage.py status --task-id task-20250401-001` 命令查询运单状态
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-task-manage 的 status 操作）
- [ ] Agent 使用了正确的 task-id 参数
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_status = False
    correct_task_id = False
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
                        if "task_manage" in command and "status" in command:
                            called_status = True
                        if "task-20250401-001" in command:
                            correct_task_id = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_status else 0.0
    scores["parameter_correctness"] = 1.0 if correct_task_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
