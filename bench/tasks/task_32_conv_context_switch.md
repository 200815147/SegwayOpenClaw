---
id: task_32_conv_context_switch
name: 上下文切换对话
category: conversation
grading_type: automated
timeout_seconds: 360
workspace_files: []
api_safety_level: full_mock
fixtures:
  robot_id_1: "robot-001"
  robot_id_2: "robot-002"
sessions:
  - prompt: "请查询机器人 robot-001 的当前状态。"
  - prompt: "再查一下机器人 robot-002 的状态。"
  - prompt: "第一个机器人的箱门信息也帮我查一下。"
---

## Prompt

（多轮对话任务，prompt 在 sessions 字段中定义）

## Expected Behavior

Agent 应当在同一个对话中：

1. 第一轮：查询 robot-001 的状态
2. 第二轮：切换到查询 robot-002 的状态（不混淆 ID）
3. 第三轮：回到 robot-001，查询其箱门信息（测试上下文中多个实体的区分能力）

关键评估点：Agent 能否在多个机器人之间正确切换上下文，不混淆 ID。

## Grading Criteria

- [ ] Agent 在第一轮查询了 robot-001 的状态
- [ ] Agent 在第二轮查询了 robot-002 的状态（不是 robot-001）
- [ ] Agent 在第三轮查询了 robot-001 的箱门信息（正确回溯到第一个机器人）

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

    # Check robot-001 status query
    queried_r1_status = any(
        "robot" in c and ("status" in c or "robot-info" in c) and "robot-001" in c
        for c in tool_calls
    )
    scores["queried_robot1_status"] = 1.0 if queried_r1_status else 0.0

    # Check robot-002 status query
    queried_r2_status = any(
        "robot" in c and ("status" in c or "robot-info" in c) and "robot-002" in c
        for c in tool_calls
    )
    scores["queried_robot2_status"] = 1.0 if queried_r2_status else 0.0

    # Check robot-001 box info query
    queried_r1_box = any(
        "box_control" in c and "info" in c and "robot-001" in c
        for c in tool_calls
    )
    scores["queried_robot1_box_info"] = 1.0 if queried_r1_box else 0.0

    # Check no ID confusion (robot-002 should not appear in box info calls)
    no_confusion = not any(
        "box_control" in c and "info" in c and "robot-002" in c
        for c in tool_calls
    )
    scores["no_id_confusion"] = 1.0 if no_confusion else 0.0

    return scores
```
