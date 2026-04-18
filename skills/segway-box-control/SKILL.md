---
name: segway-box-control
description: 控制 Segway 配送机器人的箱门操作，包括开箱、关箱、查询箱门部署信息、取物确认和取件确认。支持指定箱门编号进行开关操作，查询箱格数量和剩余箱格，以及物品放入和取出的确认操作。支持通过机器人名称自动解析 ID。
---

# Segway 箱门控制

控制配送机器人的箱门开关、查询箱门信息、取物和取件确认操作。所有 robot-id 参数均支持通过 --robot-name 自动解析。

## 完成判断规则
- 当脚本输出包含 `[TASK_COMPLETE]` 时，表示操作已成功完成，直接将结果告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示操作失败，将错误信息告知用户，不要重试。
- 当脚本输出包含 `[ACTION_PENDING]` 时，表示写操作需要用户确认。将操作摘要展示给用户，等用户确认后，用相同参数加 --confirm <token> 再次执行。

## 安全机制：两步确认
写操作（open、close、put-verify、take-verify）必须经过 --dry-run + --confirm 两步。读操作（info）直接执行。

## open - 打开箱门

打开指定机器人的一个或多个箱门。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py open --robot-id <机器人ID> --box-indexes <箱门编号,多个用逗号分隔>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py open --robot-name <机器人名称> --box-indexes <箱门编号>
```

## close - 关闭箱门

关闭指定机器人的一个或多个箱门。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py close --robot-id <机器人ID> --box-indexes <箱门编号,多个用逗号分隔>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py close --robot-name <机器人名称> --box-indexes <箱门编号>
```

## info - 查询箱门部署信息

查询指定机器人的箱门部署信息，返回箱格数、剩余箱格数和预占箱格数。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py info --robot-id <机器人ID>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py info --robot-name <机器人名称>
```

## put-verify - 取物确认

确认物品已放入机器人箱门。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py put-verify --robot-id <机器人ID> --task-id <运单ID>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py put-verify --robot-name <机器人名称> --task-id <运单ID>
```

## take-verify - 取件确认

确认物品已从机器人箱门取出。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py take-verify --robot-id <机器人ID> --task-id <运单ID>
# 或使用机器人名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py take-verify --robot-name <机器人名称> --task-id <运单ID>
```
