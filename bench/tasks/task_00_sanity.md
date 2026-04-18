---
id: task_00_sanity
name: 健全性检查
category: basic
grading_type: automated
timeout_seconds: 60
workspace_files: []
api_safety_level: read_only
---

## Prompt

请说"你好，我已准备就绪！"来确认你可以正常响应。

## Expected Behavior

Agent 应当：

1. 回复一条确认消息或问候语
2. 表明它能够正常处理和响应简单指令

这是一个基本的健全性检查，用于确保评测系统正常运行。

## Grading Criteria

- [ ] Agent 成功响应（任何回复即可得分）

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分健全性检查任务 - 仅验证 Agent 是否做出了响应。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    has_response = False
    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            if message.get("role") == "assistant":
                content = message.get("content", [])
                if content and len(content) > 0:
                    has_response = True
                    break

    scores["agent_responded"] = 1.0 if has_response else 0.0

    return scores
```
