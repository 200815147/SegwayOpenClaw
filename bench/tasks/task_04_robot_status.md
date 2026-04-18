---
id: task_04_robot_status
name: 机器人状态
category: robot_query
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  robot_id: "robot-001"
  robot_name: "小蓝1号"
---

## Prompt

请查询机器人"小蓝1号"（ID: robot-001）的当前状态。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-robot skill 的 status 或 robot-info 操作
2. 执行 `robot.py status --robot-id robot-001` 或 `robot.py robot-info --robot-id robot-001` 命令查询机器人状态
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-robot 的 status 或 robot-info 操作）
- [ ] Agent 使用了正确的 robot-id 参数（robot-001）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分机器人状态查询任务 - 检查 Agent 是否调用了 robot status 并传入正确的 robot-id。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    called_robot_status = False
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
                        if "robot" in command and ("status" in command or "robot-info" in command or "robot_info" in command):
                            called_robot_status = True
                        if "robot-001" in command or "robot_001" in command:
                            correct_robot_id = True

                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_robot_status else 0.0
    scores["parameter_correctness"] = 1.0 if correct_robot_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
