---
id: task_17_box_close
name: 关箱操作
category: box_control
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: mock_required
fixtures:
  robot_id: "robot-001"
  box_indexes: "1,2"
---

## Prompt

请关闭机器人 robot-001 的 1 号和 2 号箱门。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-box-control skill 的 close 操作
2. 执行 `box_control.py close --robot-id robot-001 --box-indexes 1,2` 命令关闭箱门
3. Mock 层将拦截写操作并返回模拟的成功响应
4. Agent 向用户确认箱门已成功关闭

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-box-control 的 close 操作）
- [ ] Agent 使用了正确的 robot-id 参数（robot-001）
- [ ] Agent 使用了正确的 box-indexes 参数
- [ ] Agent 向用户确认了操作结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_box_close = False
    correct_robot_id = False
    has_box_indexes = False
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
                        if "box_control" in command and "close" in command:
                            called_box_close = True
                        if "robot-001" in command or "robot_001" in command:
                            correct_robot_id = True
                        if "box-indexes" in command or "box_indexes" in command:
                            has_box_indexes = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_box_close else 0.0
    scores["robot_id_correct"] = 1.0 if correct_robot_id else 0.0
    scores["box_indexes_provided"] = 1.0 if has_box_indexes else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
