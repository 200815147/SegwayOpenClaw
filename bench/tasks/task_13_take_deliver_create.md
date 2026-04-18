---
id: task_13_take_deliver_create
name: 创建取送运单
category: task_create
grading_type: automated
timeout_seconds: 180
workspace_files: []
api_safety_level: mock_required
fixtures:
  area_id: "area-001"
  take_station_id: "station-101"
  take_station_name: "1楼大厅"
  deliver_station_id: "station-202"
  deliver_station_name: "3楼会议室"
  take_open_code: "8866"
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-deliver-001"
    message: "success"
---

## Prompt

请在楼宇 area-001 创建一个取送运单：从"1楼大厅"（站点 ID: station-101）取件，开箱码为 8866，送到"3楼会议室"（站点 ID: station-202）。

## Expected Behavior

Agent 应当：

1. 识别需要调用 segway-task-create skill 的 take-deliver 操作
2. 执行 `task_create.py take-deliver --area-id area-001 --take-station-id station-101 --take-open-code 8866 --deliver-station-id station-202`
3. Mock 层将拦截写操作并返回模拟的成功响应
4. Agent 向用户确认运单创建成功并展示运单 ID

## Grading Criteria

- [ ] Agent 调用了正确的 skill（segway-task-create 的 take-deliver 操作）
- [ ] Agent 使用了正确的 area-id 参数
- [ ] Agent 使用了正确的取件站点和开箱码参数
- [ ] Agent 使用了正确的送件站点参数
- [ ] Mock 层成功拦截了写操作

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    import json
    from pathlib import Path

    scores = {}
    called_take_deliver = False
    correct_area_id = False
    correct_take_station = False
    correct_deliver_station = False
    correct_open_code = False
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
                        if "task_create" in command and "take-deliver" in command:
                            called_take_deliver = True
                        if "area-001" in command:
                            correct_area_id = True
                        if "station-101" in command:
                            correct_take_station = True
                        if "station-202" in command:
                            correct_deliver_station = True
                        if "8866" in command:
                            correct_open_code = True
                if content and len(content) > 0:
                    has_response = True

    scores["skill_selection"] = 1.0 if called_take_deliver else 0.0
    scores["area_id_correct"] = 1.0 if correct_area_id else 0.0
    scores["take_params_correct"] = 1.0 if (correct_take_station and correct_open_code) else 0.0
    scores["deliver_params_correct"] = 1.0 if correct_deliver_station else 0.0

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
