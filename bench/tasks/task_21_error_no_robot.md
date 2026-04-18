---
id: task_21_error_no_robot
name: 无可用机器人错误处理
category: error_handling
grading_type: automated
timeout_seconds: 180
workspace_files: []
api_safety_level: mock_required
fixtures:
  area_id: "area-001"
  station_id: "station-101"
mock_responses:
  /api/transport/task/create:
    code: 9012
    data: null
    message: "无可用机器人"
---

## Prompt

请在楼宇 area-001 创建一个引领运单，目标站点为 station-101。

## Expected Behavior

Agent 应当：

1. 调用 segway-task-create skill 的 guidance 操作尝试创建运单
2. 收到 Mock 层返回的错误响应（code: 9012, message: "无可用机器人"）
3. 正确解读错误信息并向用户清晰地传达当前没有可用的机器人
4. 可选：建议用户稍后重试或检查机器人状态

## Grading Criteria

- [ ] Agent 尝试执行了创建运单操作
- [ ] Agent 向用户传达了错误信息（无可用机器人或类似表述）
- [ ] Agent 的回复对用户有帮助

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    attempted_create = False
    communicated_error = False
    helpful_response = False

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])
            if role == "assistant":
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "toolCall":
                            command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                            if "task_create" in command and "guidance" in command:
                                attempted_create = True
                        if item.get("type") == "text":
                            text = str(item.get("text", ""))
                            error_indicators = [
                                "无可用", "没有可用", "机器人不可用", "无法",
                                "失败", "错误", "9012", "不可用",
                                "no robot", "unavailable", "not available"
                            ]
                            if any(ind in text for ind in error_indicators):
                                communicated_error = True
                            help_indicators = [
                                "稍后", "重试", "等待", "检查", "状态",
                                "retry", "later", "wait", "check"
                            ]
                            if any(ind in text for ind in help_indicators):
                                helpful_response = True

    scores["attempted_create"] = 1.0 if attempted_create else 0.0
    scores["communicated_error"] = 1.0 if communicated_error else 0.0
    scores["helpful_response"] = 1.0 if helpful_response else 0.0
    return scores
```
