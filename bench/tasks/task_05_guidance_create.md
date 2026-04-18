---
id: task_05_guidance_create
name: 创建引领运单
category: task_create
grading_type: automated
timeout_seconds: 180
workspace_files: []
api_safety_level: mock_required
fixtures:
  area_id: "area-001"
  station_id: "station-101"
  area_name: "测试楼宇A"
  station_name: "1楼大厅"
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-guidance-001"
    message: "success"
---

## Prompt

请在楼宇"测试楼宇A"（ID: area-001）创建一个引领运单，目标站点为"1楼大厅"（ID: station-101）。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-task-create skill 的 guidance 操作
2. 执行 `task_create.py guidance --area-id area-001 --station-id station-101` 命令创建引领运单
3. Mock 层将拦截写操作并返回模拟的成功响应（taskId: mock-guidance-001）
4. Agent 向用户确认运单创建成功并展示运单 ID

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-task-create 的 guidance 操作）
- [ ] Agent 使用了正确的 area-id 参数（area-001）
- [ ] Agent 使用了正确的 station-id 参数（station-101）
- [ ] Mock 层成功拦截了写操作 API 调用

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分引领运单创建任务 - 检查 skill 调用、参数正确性和 Mock 拦截。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    import json
    from pathlib import Path

    scores = {}

    called_guidance = False
    correct_area_id = False
    correct_station_id = False
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
                        if "task_create" in command and "guidance" in command:
                            called_guidance = True
                        if "area-001" in command or "area_001" in command:
                            correct_area_id = True
                        if "station-101" in command or "station_101" in command:
                            correct_station_id = True

                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_guidance else 0.0
    scores["area_id_correct"] = 1.0 if correct_area_id else 0.0
    scores["station_id_correct"] = 1.0 if correct_station_id else 0.0

    # 检查 Mock 调用日志
    mock_intercepted = False
    mock_log_path = Path(workspace_path) / "_mock_call_log.json"
    if mock_log_path.exists():
        try:
            mock_log = json.loads(mock_log_path.read_text())
            for call in mock_log:
                if call.get("path") == "/api/transport/task/create" and call.get("intercepted"):
                    mock_intercepted = True
                    break
        except (json.JSONDecodeError, KeyError):
            pass

    scores["mock_intercepted"] = 1.0 if mock_intercepted else 0.0

    return scores
```
