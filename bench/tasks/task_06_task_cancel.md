---
id: task_06_task_cancel
name: 运单取消
category: task_manage
grading_type: automated
timeout_seconds: 120
workspace_files: []
api_safety_level: mock_required
fixtures:
  task_id: "mock-task-001"
---

## Prompt

请取消运单 ID 为 mock-task-001 的配送任务。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-task-manage skill 的 cancel 操作
2. 执行 `task_manage.py cancel --task-id mock-task-001` 命令取消运单
3. Mock 层将拦截写操作并返回模拟的成功响应
4. Agent 向用户确认运单已成功取消

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-task-manage 的 cancel 操作）
- [ ] Agent 使用了正确的 task-id 参数（mock-task-001）
- [ ] Agent 向用户确认了取消结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分运单取消任务 - 检查 Agent 是否调用了 task_manage cancel 并传入正确的 task-id。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    scores = {}

    called_cancel = False
    correct_task_id = False
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
                        if "task_manage" in command and "cancel" in command:
                            called_cancel = True
                        if "mock-task-001" in command or "mock_task_001" in command:
                            correct_task_id = True

                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_cancel else 0.0
    scores["parameter_correctness"] = 1.0 if correct_task_id else 0.0
    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
