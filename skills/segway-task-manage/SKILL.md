---
name: segway-task-manage
description: 管理 Segway 配送机器人的运单，支持取消运单、查询运单状态、修改运单优先级、查询历史订单和滞留件重新配送。
---

# Segway 运单管理

管理配送机器人的运单，包括取消、优先级调整、状态查询、历史记录和重新配送。

## 完成判断规则
- 当脚本输出包含 `[TASK_COMPLETE]` 时，表示操作已成功完成，直接将结果告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示操作失败，将错误信息告知用户，不要重试。
- 当脚本输出包含 `[ACTION_PENDING]` 时，表示写操作需要用户确认。将操作摘要展示给用户，等用户确认后，用相同参数加 --confirm <token> 再次执行。

## 安全机制：两步确认
写操作（cancel、priority、redeliver）必须经过 --dry-run + --confirm 两步。读操作（status、history）直接执行。

## cancel - 取消运单

取消指定的运单任务。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py cancel --task-id <运单ID>
```

## priority - 修改运单优先级

修改指定运单的优先级，优先级范围 40-60。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py priority --task-id <运单ID> --priority-level <优先级>
```

## status - 查询运单状态

查询指定运单的当前状态。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py status --task-id <运单ID>
```

## history - 查询历史订单

根据时间范围查询历史运单列表，时间参数为毫秒时间戳。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py history --start-time <开始时间戳> --end-time <结束时间戳>
```

## redeliver - 滞留件重新配送

对滞留在机器人上的运单进行重新配送，支持多个运单 ID（逗号分隔）。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py redeliver --robot-id <机器人ID> --task-ids <运单ID1,运单ID2,...>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py redeliver --robot-name <机器人名称> --task-ids <运单ID1,运单ID2,...>
```
