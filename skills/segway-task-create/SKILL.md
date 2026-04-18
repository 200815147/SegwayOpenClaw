---
name: segway-task-create
description: 下发 Segway 配送机器人运单，支持创建引领任务、特殊引领任务和取送配送任务。可指定目标站点、机器人、优先级等参数来创建任务。支持通过楼宇名称、站点名称、机器人名称自动解析 ID，无需手动查询。
---

# Segway 运单创建

下发配送机器人运单，支持引领运单和取送运单的创建。所有 ID 参数均支持通过名称自动解析。

## 完成判断规则
- 当脚本输出包含 `[TASK_COMPLETE]` 时，表示运单已创建成功，将运单 ID 告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示创建失败，将错误信息告知用户，不要重试。
- 当脚本输出包含 `[ACTION_PENDING]` 时，表示操作需要用户确认。将操作摘要展示给用户，等用户说"确认"后，用相同参数加 --confirm <token> 再次执行。

## 安全机制：两步确认
所有运单创建操作必须经过两步：
1. 第一步：加 `--dry-run` 参数运行，脚本验证参数后输出操作摘要和确认 token
2. 第二步：将摘要展示给用户，用户确认后，用相同参数加 `--confirm <token>` 执行

示例流程：
```bash
# 第一步：dry-run
task_create.py guidance --area-name "测试楼宇A" --station-name "1楼大厅" --dry-run
# 输出操作摘要和 token

# 第二步：用户确认后执行
task_create.py guidance --area-name "测试楼宇A" --station-name "1楼大厅" --confirm <token>
```

## 操作手册

### 创建引领运单的步骤
如果你已经知道楼宇名称和站点名称：
```bash
# 第一步：dry-run
task_create.py guidance --area-name "测试楼宇A" --station-name "1楼大厅" --dry-run
# 第二步：用户确认后
task_create.py guidance --area-name "测试楼宇A" --station-name "1楼大厅" --confirm <token>
```

### 创建取送运单的步骤
```bash
# 第一步：dry-run
task_create.py take-deliver --area-name "测试楼宇A" --take-station-name "前台" --take-open-code 1234 --deliver-station-name "302房间" --dry-run
# 第二步：用户确认后
task_create.py take-deliver --area-name "测试楼宇A" --take-station-name "前台" --take-open-code 1234 --deliver-station-name "302房间" --confirm <token>
```

### 如果用户没有提供足够信息
1. 缺楼宇名称 → 询问用户"请问是哪个楼宇？"
2. 缺站点名称 → 询问用户"请问送到哪个站点？"
3. 缺开箱码 → 询问用户"请提供取件开箱码"
4. 不要猜测或编造这些参数

## guidance - 创建引领运单

下发引领任务，机器人将引领用户前往指定站点。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py guidance --area-id <楼宇ID> --station-id <站点ID> [--priority-level <优先级>] [--out-id <外部ID>] [--callback-url <回调URL>] [--remark <备注>]
# 或使用名称（自动解析）
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py guidance --area-name <楼宇名称> --station-name <站点名称> [--priority-level <优先级>] [--remark <备注>]
```

## special-guidance - 创建特殊引领运单

下发特殊引领任务，指定机器人引领用户前往目标站点，可设置等待时间。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py special-guidance --area-id <楼宇ID> --robot-id <机器人ID> --station-id <站点ID> --guidance-wait-time <等待时间秒>
# 或使用名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py special-guidance --area-name <楼宇名称> --robot-name <机器人名称> --station-name <站点名称> --guidance-wait-time <等待时间秒>
```

## take-deliver - 创建取送运单

下发取送配送任务，机器人前往取件站点取件后送往送件站点。

```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py take-deliver --area-id <楼宇ID> --take-station-id <取件站点ID> --take-open-code <取件开箱码> --deliver-station-id <送件站点ID>
# 或使用名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py take-deliver --area-name <楼宇名称> --take-station-name <取件站点名称> --take-open-code <取件开箱码> --deliver-station-name <送件站点名称>
```