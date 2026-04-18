---
id: task_30_conv_query_chain
name: 连续查询对话
category: conversation
grading_type: automated
timeout_seconds: 360
workspace_files: []
api_safety_level: full_mock
sessions:
  - prompt: "请查询所有可用的楼宇列表。"
  - prompt: "刚才查到的第一个楼宇，帮我查一下它下面有哪些站点。"
  - prompt: "再帮我查一下那个楼宇里有哪些机器人。"
---

## Prompt

（多轮对话任务，prompt 在 sessions 字段中定义）

## Expected Behavior

Agent 应当在同一个对话中：

1. 第一轮：调用 area_map areas 查询楼宇列表，返回结果
2. 第二轮：根据上下文中第一个楼宇的 areaId，调用 area_map stations 查询站点
3. 第三轮：根据上下文中的 areaId，调用 robot sort-list 或 robot list 查询机器人

关键评估点：Agent 能否利用前序对话的上下文信息，而不是要求用户重复提供 ID。

## Grading Criteria

- [ ] Agent 在第一轮调用了 areas 查询
- [ ] Agent 在第二轮调用了 stations 查询并传入了 areaId
- [ ] Agent 在第三轮调用了机器人相关查询
- [ ] Agent 没有在后续轮次要求用户重新提供已知信息

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

    called_areas = any("area_map" in c and "areas" in c for c in tool_calls)
    called_stations = any("area_map" in c and "stations" in c for c in tool_calls)
    called_robots = any("robot" in c and ("list" in c or "sort-list" in c or "sort_list" in c) for c in tool_calls)

    scores["called_areas"] = 1.0 if called_areas else 0.0
    scores["called_stations"] = 1.0 if called_stations else 0.0
    scores["called_robots"] = 1.0 if called_robots else 0.0

    # Check that stations call has an area id parameter (context utilization)
    stations_has_param = False
    for c in tool_calls:
        if "area_map" in c and "stations" in c and ("area" in c.lower()):
            stations_has_param = True
    scores["context_utilization"] = 1.0 if (called_stations and stations_has_param) else 0.0

    return scores
```
