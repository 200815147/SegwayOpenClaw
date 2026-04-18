---
id: task_18_box_info
name: 箱门信息查询
category: box_control
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  robot_id: "robot-001"
  robot_name: "小蓝1号"
---

## Prompt

请查询机器人"小蓝1号"（ID: robot-001）的箱门部署信息，我想知道它有多少个箱格、还剩多少可用。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-box-control skill 的 info 操作
2. 执行 `box_control.py info --robot-id robot-001` 命令查询箱门信息
3. 将箱格数、剩余箱格数等信息以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-box-control 的 info 操作）
- [ ] Agent 使用了正确的 robot-id 参数（robot-001）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_box_info = False
    correct_robot_id = False
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
                        if "box_control" in command and "info" in command:
                            called_box_info = True
                        if "robot-001" in command or "robot_001" in command:
                            correct_robot_id = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_box_info else 0.0
    scores["parameter_correctness"] = 1.0 if correct_robot_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
