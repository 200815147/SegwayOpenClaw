---
id: task_11_robot_location
name: 机器人位置查询
category: robot_query
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  area_id: "area-001"
  robot_id: "robot-001"
  area_name: "测试楼宇A"
  robot_name: "小蓝1号"
---

## Prompt

请查询楼宇"测试楼宇A"（ID: area-001）中机器人"小蓝1号"（ID: robot-001）的当前位置。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-robot skill 的 location 操作
2. 执行 `robot.py location --area-id area-001 --robot-id robot-001` 命令查询机器人位置
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-robot 的 location 操作）
- [ ] Agent 使用了正确的 area-id 参数（area-001）
- [ ] Agent 使用了正确的 robot-id 参数（robot-001）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_location = False
    correct_area_id = False
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
                        if "robot" in command and "location" in command and "locations" not in command:
                            called_location = True
                        if "area-001" in command or "area_001" in command:
                            correct_area_id = True
                        if "robot-001" in command or "robot_001" in command:
                            correct_robot_id = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_location else 0.0
    scores["area_id_correct"] = 1.0 if correct_area_id else 0.0
    scores["robot_id_correct"] = 1.0 if correct_robot_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
