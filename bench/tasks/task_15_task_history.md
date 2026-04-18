---
id: task_15_task_history
name: 历史运单查询
category: task_manage
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  start_time: "1743436800000"
  end_time: "1743523200000"
---

## Prompt

请查询 2025 年 4 月 1 日（时间戳 1743436800000）到 2025 年 4 月 2 日（时间戳 1743523200000）之间的历史运单记录。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-task-manage skill 的 history 操作
2. 执行 `task_manage.py history --start-time 1743436800000 --end-time 1743523200000` 命令查询历史运单
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-task-manage 的 history 操作）
- [ ] Agent 使用了正确的 start-time 参数
- [ ] Agent 使用了正确的 end-time 参数
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_history = False
    correct_start = False
    correct_end = False
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
                        if "task_manage" in command and "history" in command:
                            called_history = True
                        if "1743436800000" in command:
                            correct_start = True
                        if "1743523200000" in command:
                            correct_end = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_history else 0.0
    scores["start_time_correct"] = 1.0 if correct_start else 0.0
    scores["end_time_correct"] = 1.0 if correct_end else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
