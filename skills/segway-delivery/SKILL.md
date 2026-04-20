---
name: segway-delivery
description: 一站式配送任务编排。通过楼宇名称和站点名称查询楼宇和站点信息，然后通过 segway-stage 起草配送任务等待人工审批。适用于"送东西到3楼大厅"、"带我去前台"、"从仓库取件送到302"等自然语言指令。读操作（status、list-areas）直接执行，写操作（guidance、take-deliver）必须通过 segway-stage 起草。
---

# Segway 一站式配送

通过楼宇名称和站点名称查询信息，然后起草配送任务等待审批。

⚠️ **写操作（guidance、take-deliver）的正确流程：**
1. 用本 skill 的 `list-areas` 或 `status` 查询楼宇/站点信息
2. 用 `segway-stage` skill 起草任务：`stage_action.py stage --action task.create.guidance --params '...'`
3. 告知用户任务已起草，等待审批

读操作（status、list-areas）可以直接使用本 skill。

# Segway 一站式配送

通过楼宇名称和站点名称直接下发配送任务，自动完成查询和匹配，无需手动提供 ID。

## 完成判断规则
- 当脚本输出包含 `[TASK_COMPLETE]` 时，表示配送任务已创建成功，将运单 ID 告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示创建失败，将错误信息告知用户，不要重试。
- 当脚本输出包含 `[ACTION_PENDING]` 时，表示操作需要用户确认。将操作摘要展示给用户，等用户说"确认"后，用相同参数加 --confirm <token> 再次执行。

## 安全机制：两步确认
写操作（guidance、take-deliver）必须经过两步：
1. 第一步：加 `--dry-run` 参数运行，脚本会自动查询楼宇和站点，验证参数后输出操作摘要和确认 token
2. 第二步：将摘要展示给用户，用户确认后，用相同参数加 `--confirm <token>` 执行

读操作（status、list-areas）直接执行，不需要确认。

示例流程：
```bash
# 第一步：dry-run（自动查询楼宇和站点）
delivery.py guidance --area-name "测试楼宇A" --station-name "1楼大厅" --dry-run
# 输出：操作摘要 + 确认 token

# 第二步：用户确认后执行
delivery.py guidance --area-name "测试楼宇A" --station-name "1楼大厅" --confirm <token>
```

## 常见多步骤场景操作手册

### 场景1：用户说"送东西到某个地方"
1. 用 `guidance --area-name "xxx" --station-name "xxx" --dry-run` 运行
2. 脚本自动查询楼宇和站点，输出操作摘要和 token
3. 将摘要展示给用户："即将创建引领运单，楼宇: xxx，站点: xxx，确认吗？"
4. 用户确认后，用相同参数加 `--confirm <token>` 执行
5. 看到 `[TASK_COMPLETE]` 后告知用户运单 ID

### 场景2：用户说"查一下有哪些楼宇，然后送到某个站点"
1. 先用 `list-areas` 查楼宇列表（读操作，直接执行），将结果告知用户
2. 等用户选择楼宇后，用 `guidance --dry-run` 生成操作摘要
3. 用户确认后用 `--confirm` 执行

### 场景3：用户说"查一下楼宇状态"
直接用 `status` 命令（读操作，直接执行），一次性返回运力、站点、机器人信息。

### 重要提醒
- 每次调用脚本后，看到 `[TASK_COMPLETE]` 或 `[TASK_FAILED]` 就停下来
- 不要在没有用户明确指示的情况下连续调用多个 skill
- 如果缺少参数，直接询问用户，不要猜测

## guidance - 引领配送

指定楼宇和目标站点，自动查询匹配后创建引领运单。机器人将引领用户前往目标站点。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/delivery.py guidance --area-name <楼宇名称> --station-name <站点名称> [--priority-level <优先级>] [--remark <备注>]
```

参数说明：
- `--area-name`: 楼宇名称（支持模糊匹配，如"测试楼宇"可匹配"测试楼宇A"）
- `--station-name`: 目标站点名称（支持模糊匹配）
- `--priority-level`: 可选，优先级 40-60
- `--remark`: 可选，备注信息

示例：
```bash
# 带我去1楼大厅
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/delivery.py guidance --area-name "测试楼宇A" --station-name "1楼大厅"
```

## take-deliver - 取送配送

指定楼宇、取件站点和送件站点，自动查询匹配后创建取送运单。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/delivery.py take-deliver --area-name <楼宇名称> --take-station-name <取件站点名称> --take-open-code <取件开箱码> --deliver-station-name <送件站点名称> [--deliver-open-code <送件开箱码>] [--verify] [--priority-level <优先级>] [--remark <备注>]
```

参数说明：
- `--area-name`: 楼宇名称
- `--take-station-name`: 取件站点名称（支持模糊匹配）
- `--take-open-code`: 取件开箱码
- `--deliver-station-name`: 送件站点名称（支持模糊匹配）
- `--deliver-open-code`: 可选，送件开箱码
- `--verify`: 可选，送件是否需要验证
- `--priority-level`: 可选，优先级 40-60
- `--remark`: 可选，备注信息

示例：
```bash
# 从前台取件送到302房间
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/delivery.py take-deliver --area-name "测试楼宇A" --take-station-name "前台" --take-open-code 1234 --deliver-station-name "302房间"
```

## status - 配送状态总览

查询指定楼宇的配送状态总览，包括运力状态、可用机器人数量和站点列表。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/delivery.py status --area-name <楼宇名称>
```

## list-areas - 列出所有可用楼宇

列出所有可用楼宇及其站点数量，帮助用户了解可配送范围。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/delivery.py list-areas
```
