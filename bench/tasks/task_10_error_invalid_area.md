---
id: task_10_error_invalid_area
name: 无效楼宇ID错误处理
category: error_handling
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: mock_required
mock_responses:
  /api/transport/areas:
    code: 9001
    data: null
    message: "楼宇不存在"
---

## Prompt

请查询楼宇 ID 为 invalid-area-999 的站点列表。

## Expected Behavior

Agent 应当：

1. 尝试调用 segway-area-map skill 查询站点列表
2. 收到 Mock 层返回的错误响应（code: 9001, message: "楼宇不存在"）
3. 正确解读错误信息并向用户清晰地传达该楼宇不存在
4. 可选：建议用户检查楼宇 ID 或查询可用楼宇列表

## Grading Criteria

- [ ] Agent 尝试执行了查询操作
- [ ] Agent 向用户传达了错误信息（楼宇不存在或类似表述）
- [ ] Agent 的回复对用户有帮助（如建议检查 ID 或查询可用楼宇）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分无效楼宇 ID 错误处理任务 - 检查 Agent 是否正确传达了错误信息。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    attempted_query = False
    communicated_error = False

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])

            if role == "assistant":
                for item in content:
                    if isinstance(item, dict):
                        # 检查是否尝试了查询
                        if item.get("type") == "toolCall":
                            command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                            if "area_map" in command or "station" in command:
                                attempted_query = True

                        # 检查文本回复中是否传达了错误信息
                        if item.get("type") == "text":
                            text = str(item.get("text", ""))
                            error_indicators = [
                                "不存在", "无效", "错误", "找不到", "无法找到",
                                "不可用", "失败", "error", "not found", "invalid",
                                "9001"
                            ]
                            if any(indicator in text for indicator in error_indicators):
                                communicated_error = True

    # 检查是否提供了恢复建议（如建议检查 ID 或查询可用楼宇）
    recovery_suggestion = False
    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])
            if role == "assistant":
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = str(item.get("text", ""))
                        recovery_indicators = [
                            "检查", "确认", "重新", "正确的",
                            "可用", "列表", "查询", "尝试",
                            "verify", "check", "try", "available"
                        ]
                        if any(indicator in text for indicator in recovery_indicators):
                            recovery_suggestion = True

    scores["attempted_query"] = 1.0 if attempted_query else 0.0
    scores["communicated_error"] = 1.0 if communicated_error else 0.0
    scores["recovery_suggestion"] = 1.0 if recovery_suggestion else 0.0

    return scores
```
