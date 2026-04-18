---
id: task_07_box_open
name: 开箱操作
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

请打开机器人 robot-001 的 1 号和 2 号箱门。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-box-control skill 的 open 操作
2. 执行 `box_control.py open --robot-id robot-001 --box-indexes 1,2` 命令打开箱门
3. Mock 层将拦截写操作并返回模拟的成功响应
4. Agent 向用户确认箱门已成功打开

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-box-control 的 open 操作）
- [ ] Agent 使用了正确的 robot-id 参数（robot-001）
- [ ] Agent 使用了正确的 box-indexes 参数（包含 1 和 2）
- [ ] Agent 向用户确认了操作结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分开箱操作任务 - 检查 Agent 是否调用了 box_control open 并传入正确参数。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    called_box_open = False
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
                        if "box_control" in command and "open" in command:
                            called_box_open = True
                        if "robot-001" in command or "robot_001" in command:
                            correct_robot_id = True
                        if "box-indexes" in command or "box_indexes" in command:
                            has_box_indexes = True

                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_box_open else 0.0
    scores["robot_id_correct"] = 1.0 if correct_robot_id else 0.0
    scores["box_indexes_provided"] = 1.0 if has_box_indexes else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
