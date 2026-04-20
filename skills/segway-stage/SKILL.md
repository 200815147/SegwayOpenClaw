---
name: segway-stage
description: 起草 Segway 机器人写操作任务并挂起等待人工审批。用于创建运单、取消运单、开箱、关箱等危险操作。agent 调用后任务进入 pending 状态，用户通过审批链接批准后由服务端直接执行，大模型不参与执行过程。适用于"创建运单"、"开箱"、"取消"等需要人工确认的操作。
---

# Segway 任务起草（Stage Action）

起草写操作任务并挂起等待人工审批。大模型只负责"起草"，不负责"执行"。

## 完成判断规则
- 当脚本输出包含 `[ACTION_STAGED]` 时，表示任务已成功起草并等待审批。将审批信息告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示起草失败，将错误信息告知用户。

## 安全机制
- 本 skill 只起草任务，不执行任何写操作
- 执行由独立的 HTTP 服务完成，大模型完全不参与
- 用户通过审批链接（或企微回复）批准后才会执行

## stage - 起草任务

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/stage_action.py stage --action <操作类型> --params '<JSON参数>'
```

支持的操作类型：
- `task.create.guidance` — 创建引领运单
- `task.create.take-deliver` — 创建取送运单
- `task.cancel` — 取消运单
- `task.priority` — 修改运单优先级
- `task.redeliver` — 重新配送
- `box.open` — 打开箱门
- `box.close` — 关闭箱门
- `box.put-verify` — 取物确认
- `box.take-verify` — 取件确认

参数为 JSON 格式，即 Segway API 的请求体。

示例：
```bash
# 起草一个引领运单
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/stage_action.py stage --action task.create.guidance --params '{"areaId":"area-001","taskType":"Guidance","stationId":"station-101"}'
```

## list - 查看待审批任务

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/stage_action.py list [--status pending|approved|rejected|executed]
```

## 操作手册

### 用户说"送东西到1楼大厅"
1. 先用 segway-area-map 或 segway-resolve 查询楼宇和站点 ID
2. 构造好请求参数后，调用本 skill 的 `stage` 命令起草任务
3. 告知用户"任务已起草，请通过审批链接确认"
4. 结束。不要等待，不要轮询，不要再调用任何 skill
