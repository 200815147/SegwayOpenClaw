---
id: task_01_area_query
name: 楼宇查询
category: area_query
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: read_only
---

## Prompt

请查询所有可用的楼宇列表，告诉我有哪些楼宇可以使用配送机器人服务。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-area-map skill 的 areas 操作
2. 执行 `area_map.py areas` 命令查询楼宇列表
3. 将查询结果以清晰的格式呈现给用户

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-area-map 的 areas 操作）
- [ ] Agent 向用户展示了查询结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分楼宇查询任务 - 检查 Agent 是否调用了 area_map areas 操作。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    called_areas = False
    has_response = False

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])

            if role == "assistant":
                for item in content:
                    # 检查 toolCall 中是否包含 area_map 和 areas
                    if isinstance(item, dict) and item.get("type") == "toolCall":
                        command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                        if "area_map" in command and "areas" in command:
                            called_areas = True

                # 检查是否有文本回复
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_areas else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
