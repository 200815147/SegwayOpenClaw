---
id: task_42_delivery_status
name: 配送状态总览
category: delivery
grading_type: automated
timeout_seconds: 180
workspace_files: []
api_safety_level: full_mock
---

## Prompt

请查看测试楼宇A的配送状态，包括运力情况、站点和机器人信息。

## Expected Behavior

Agent 应当：

1. 调用 segway-delivery 的 status 操作，传入楼宇名称
2. 将运力状态、站点列表、机器人列表等信息展示给用户

这是一个只读操作，不需要用户确认。

## Grading Criteria

- [ ] Agent 调用了 segway-delivery 的 status 操作
- [ ] Agent 使用了楼宇名称参数
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
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

    used_status = any("delivery" in c and "status" in c for c in tool_calls)
    scores["used_delivery_status"] = 1.0 if used_status else 0.0

    used_name = any("area-name" in c or "area_name" in c for c in tool_calls)
    scores["used_name_param"] = 1.0 if used_name else 0.0

    has_response = any(
        entry.get("type") == "message" and
        entry.get("message", {}).get("role") == "assistant" and
        len(entry.get("message", {}).get("content", [])) > 0
        for entry in transcript
    )
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
