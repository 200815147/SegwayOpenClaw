---
id: task_09_error_missing_id
name: 缺失ID错误处理
category: error_handling
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: mock_required
---

## Prompt

请帮我创建一个引领运单。

## Expected Behavior

Agent 应当：

1. 识别用户请求中缺少必要的参数（楼宇 ID 和站点 ID）
2. 主动向用户询问缺失的信息，而非直接尝试调用 API
3. 以友好的方式提示用户需要提供哪些信息

Agent 不应在缺少必要参数的情况下直接调用运单创建 API。

## Grading Criteria

- [ ] Agent 识别到缺少必要参数
- [ ] Agent 主动向用户询问缺失的楼宇 ID 或站点 ID 信息
- [ ] Agent 没有在缺少参数的情况下直接调用创建 API

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分缺失 ID 错误处理任务 - 检查 Agent 是否主动询问缺失信息。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    asked_for_info = False
    called_create_directly = False

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])

            if role == "assistant":
                for item in content:
                    if isinstance(item, dict):
                        # 检查是否直接调用了创建 API
                        if item.get("type") == "toolCall":
                            command = str(item.get("arguments", "")) + str(item.get("toolName", ""))
                            if "task_create" in command and "guidance" in command:
                                called_create_directly = True

                        # 检查文本回复中是否包含询问
                        if item.get("type") == "text":
                            text = str(item.get("text", ""))
                            # 检查是否包含问号或询问关键词
                            ask_indicators = ["?", "？", "楼宇", "站点", "area", "station",
                                              "ID", "id", "哪个", "哪些", "请提供", "需要",
                                              "告诉我", "指定"]
                            if any(indicator in text for indicator in ask_indicators):
                                asked_for_info = True

    scores["asked_for_missing_info"] = 1.0 if asked_for_info else 0.0
    scores["did_not_call_blindly"] = 0.0 if called_create_directly else 1.0

    return scores
```
