---
id: task_03_robot_list
name: 机器人列表
category: robot_query
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
---

## Prompt

请查询所有可用的配送机器人列表。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-robot skill 的 list 操作
2. 执行 `robot.py list` 命令查询机器人列表
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-robot 的 list 操作）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分机器人列表查询任务 - 检查 Agent 是否调用了 robot list 操作。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    called_robot_list = False
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
                        if "robot" in command and "list" in command:
                            called_robot_list = True

                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_robot_list else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
