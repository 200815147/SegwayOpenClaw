---
id: task_08_multi_query_create
name: 查询并创建引领运单
category: multi_step
grading_type: automated
timeout_seconds: 300
workspace_files: []
api_safety_level: mock_required
mock_responses:
  /api/transport/task/create:
    code: 200
    data:
      taskId: "mock-multi-001"
    message: "success"
---

## Prompt

请先查询所有可用楼宇列表，找到名为"测试楼宇A"的楼宇，然后查询该楼宇下的站点列表，最后创建一个引领运单到"1楼大厅"站点。

## Expected Behavior

Agent 应当按以下顺序执行多个步骤：

1. 调用 segway-area-map skill 的 areas 操作查询楼宇列表
2. 从返回结果中找到"测试楼宇A"对应的 areaId
3. 调用 segway-area-map skill 的 stations 操作，使用查询到的 areaId 查询站点列表
4. 从返回结果中找到"1楼大厅"对应的 stationId
5. 调用 segway-task-create skill 的 guidance 操作，使用查询到的 areaId 和 stationId 创建引领运单
6. 向用户确认运单创建成功

关键评估点：Agent 应通过查询获取 ID，而非直接使用硬编码值。

## Grading Criteria

- [ ] Agent 调用了 area_map areas 查询楼宇列表
- [ ] Agent 调用了 area_map stations 查询站点列表
- [ ] Agent 调用了 task_create guidance 创建引领运单
- [ ] 调用顺序正确（先查询楼宇，再查询站点，最后创建运单）
- [ ] 后续调用的参数正确引用了前序调用返回的数据（如 areaId、stationId）
- [ ] Agent 未跳过查询步骤直接使用硬编码参数（推理正确性）
- [ ] Agent 向用户展示了最终结果

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """
    评分多步骤复合任务 - 检查多个 skill 调用的顺序、参数传递和推理正确性。

    Args:
        transcript: 解析后的 JSONL 对话记录列表
        workspace_path: 任务隔离工作空间目录路径

    Returns:
        Dict，评分维度名称到分数（0.0 到 1.0）的映射
    """
    import json
    from pathlib import Path

    scores = {}

    # 收集所有 toolCall 的顺序和详细信息
    tool_calls = []

    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            role = message.get("role", "")
            content = message.get("content", [])

            if role == "assistant":
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "toolCall":
                        tool_name = str(item.get("toolName", ""))
                        arguments = str(item.get("arguments", ""))
                        command = arguments + tool_name
                        tool_calls.append({
                            "command": command,
                            "toolName": tool_name,
                            "arguments": arguments,
                        })

    # 检查是否调用了三个关键操作
    called_areas = any("area_map" in c["command"] and "areas" in c["command"] for c in tool_calls)
    called_stations = any("area_map" in c["command"] and "stations" in c["command"] for c in tool_calls)
    called_guidance = any("task_create" in c["command"] and "guidance" in c["command"] for c in tool_calls)

    scores["called_areas"] = 1.0 if called_areas else 0.0
    scores["called_stations"] = 1.0 if called_stations else 0.0
    scores["called_guidance"] = 1.0 if called_guidance else 0.0

    # 检查调用顺序
    order_correct = False
    areas_idx = -1
    stations_idx = -1
    guidance_idx = -1
    if called_areas and called_stations and called_guidance:
        areas_idx = next((i for i, c in enumerate(tool_calls) if "area_map" in c["command"] and "areas" in c["command"]), -1)
        stations_idx = next((i for i, c in enumerate(tool_calls) if "area_map" in c["command"] and "stations" in c["command"]), -1)
        guidance_idx = next((i for i, c in enumerate(tool_calls) if "task_create" in c["command"] and "guidance" in c["command"]), -1)
        if areas_idx < stations_idx < guidance_idx:
            order_correct = True

    scores["call_order_correct"] = 1.0 if order_correct else 0.0

    # 检查参数传递 - 后续调用是否引用了前序调用返回的数据
    # 通过 Mock 调用日志验证 stations 查询使用了从 areas 查询获取的 areaId，
    # 以及 guidance 创建使用了从查询获取的 areaId 和 stationId
    param_passing_score = 0.0
    mock_log_path = Path(workspace_path) / "_mock_call_log.json"
    if mock_log_path.exists():
        try:
            mock_log = json.loads(mock_log_path.read_text())
            # 查找 stations 查询是否带有 areaId 参数
            stations_has_area_id = False
            guidance_has_area_id = False
            guidance_has_station_id = False
            for call in mock_log:
                path = call.get("path", "")
                body = call.get("body") or {}
                query = call.get("query_params") or {}
                call_str = json.dumps(call)
                # stations 查询应包含 areaId
                if "station" in path and ("areaId" in call_str or "area_id" in call_str or "area-id" in call_str):
                    stations_has_area_id = True
                # guidance 创建应包含 areaId 和 stationId
                if "task/create" in path:
                    if "areaId" in call_str or "area_id" in call_str or "area-id" in call_str:
                        guidance_has_area_id = True
                    if "stationId" in call_str or "station_id" in call_str or "station-id" in call_str:
                        guidance_has_station_id = True
            if stations_has_area_id:
                param_passing_score += 0.34
            if guidance_has_area_id:
                param_passing_score += 0.33
            if guidance_has_station_id:
                param_passing_score += 0.33
        except (json.JSONDecodeError, KeyError):
            pass
    else:
        # 如果没有 mock 日志，回退到检查 transcript 中的参数传递
        if called_stations and stations_idx >= 0:
            station_args = tool_calls[stations_idx]["arguments"]
            # 站点查询应包含某种 area id 参数
            if "area" in station_args.lower():
                param_passing_score += 0.34
        if called_guidance and guidance_idx >= 0:
            guidance_args = tool_calls[guidance_idx]["arguments"]
            if "area" in guidance_args.lower():
                param_passing_score += 0.33
            if "station" in guidance_args.lower():
                param_passing_score += 0.33

    scores["parameter_passing"] = round(min(param_passing_score, 1.0), 2)

    # 推理正确性 - 检查 Agent 是否跳过查询步骤直接使用硬编码参数
    # 如果 Agent 未调用 areas 或 stations 查询就直接创建运单，则扣分
    if not called_guidance:
        reasoning_score = 0.0  # 未调用 guidance，无法评估推理
    else:
        reasoning_score = 1.0
        if not called_areas:
            reasoning_score -= 0.5  # 跳过楼宇查询
        if not called_stations:
            reasoning_score -= 0.5  # 跳过站点查询
        if not order_correct:
            reasoning_score -= 0.25  # 顺序不正确也扣分

    scores["reasoning_correctness"] = max(reasoning_score, 0.0)

    # 检查是否有最终回复
    has_response = False
    for entry in transcript:
        if entry.get("type") == "message":
            message = entry.get("message", {})
            if message.get("role") == "assistant":
                content = message.get("content", [])
                if content and len(content) > 0:
                    has_response = True

    scores["response_provided"] = 1.0 if has_response else 0.0

    return scores
```
