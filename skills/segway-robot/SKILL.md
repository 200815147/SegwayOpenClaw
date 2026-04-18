---
name: segway-robot
description: 查询 Segway 配送机器人的列表、运行状态、实时位置、电量信息和当前订单。支持获取单个或多个机器人的位置数据、状态详情和实时订单信息。支持通过机器人名称或楼宇名称自动解析 ID。
---

# Segway 机器人信息查询

查询配送机器人的列表、状态、位置、电量和实时订单信息。所有需要 ID 的参数均支持通过名称自动解析。

## 完成判断规则
- 当脚本输出包含 `[TASK_COMPLETE]` 时，表示操作已成功完成，直接将结果告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示操作失败，将错误信息告知用户，不要重试。
- 本 skill 全部为读操作（查询），不涉及写操作，无需 --dry-run / --confirm 确认。

## list - 获取机器人列表

查询所有可用的机器人，返回 robotId、昵称、所属楼宇等信息。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py list
```

## status - 获取机器人状态

查询指定机器人的当前状态。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py status --robot-id <机器人ID>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py status --robot-name <机器人名称>
```

## location - 获取单个机器人位置

查询指定机器人的实时位置信息。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py location --area-id <楼宇ID> --robot-id <机器人ID>
# 或使用名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py location --area-name <楼宇名称> --robot-name <机器人名称>
```

## locations - 获取多个机器人位置

批量查询多个机器人的实时位置信息，需要提供多个机器人 ID（逗号分隔）。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py locations --area-id <楼宇ID> --robot-ids <机器人ID1,机器人ID2,...>
# 或使用楼宇名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py locations --area-name <楼宇名称> --robot-ids <机器人ID1,机器人ID2,...>
```

## sort-list - 获取楼宇下有序机器人列表

查询指定楼宇下的机器人排序列表。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py sort-list --area-id <楼宇ID>
# 或使用楼宇名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py sort-list --area-name <楼宇名称>
```

## robot-info - 获取机器人实时状态及订单

查询指定机器人的实时状态和当前订单信息。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py robot-info --robot-id <机器人ID>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py robot-info --robot-name <机器人名称>
```

## robots-info - 获取多个机器人实时状态及订单

批量查询多个机器人的实时状态和当前订单信息，需要提供多个机器人 ID（逗号分隔）。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-robot/scripts/robot.py robots-info --robot-ids <机器人ID1,机器人ID2,...>
```
