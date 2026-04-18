---
id: task_02_station_query
name: 站点查询
category: area_query
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
fixtures:
  area_id: "area-001"
  area_name: "测试楼宇A"
---

## Prompt

请查询楼宇"测试楼宇A"（ID: area-001）下的所有站点列表。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-area-map skill 的 stations 操作
2. 执行 `area_map.py stations --area-id area-001` 命令查询站点列表
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-area-map 的 stations 操作）
- [ ] Agent 使用了正确的 area-id 参数（area-001）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分站点查询任务 - 检查 Agent 是否调用了 area_map stations 并传入正确的 area-id。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    called_stations = False
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
                        if "area_map" in command and "stations" in command:
                            called_stations = True
                        if "area-001" in command or "area_001" in command:
                            correct_area_id = True

                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_stations else 0.0
    scores["parameter_correctness"] = 1.0 if correct_area_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
