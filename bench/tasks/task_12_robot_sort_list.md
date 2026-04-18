---
id: task_12_robot_sort_list
name: 楼宇机器人排序列表
category: robot_query
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  area_id: "area-001"
  area_name: "测试楼宇A"
---

## Prompt

请查询楼宇"测试楼宇A"（ID: area-001）下所有机器人的排序列表。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-robot skill 的 sort-list 操作
2. 执行 `robot.py sort-list --area-id area-001` 命令查询机器人排序列表
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-robot 的 sort-list 操作）
- [ ] Agent 使用了正确的 area-id 参数（area-001）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    scores = {}
    called_sort_list = False
    correct_area_id = False
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
                        if "robot" in command and "sort-list" in command:
                            called_sort_list = True
                        if "area-001" in command or "area_001" in command:
                            correct_area_id = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_sort_list else 0.0
    scores["parameter_correctness"] = 1.0 if correct_area_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0
    return scores
```
