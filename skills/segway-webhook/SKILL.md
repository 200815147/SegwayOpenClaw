---
name: segway-webhook
description: Segway 配送机器人运单回调事件处理。启动 webhook 服务接收 Segway API 的运单状态变更推送，记录事件日志，查询运单事件历史。支持运单状态变更通知、配送完成提醒、异常告警。适用于"查看运单事件"、"运单回调"、"配送进度"、"启动webhook"等场景。
---

# Segway Webhook 事件处理

接收和管理 Segway 配送机器人的运单状态回调事件。

## start - 启动 Webhook 服务

启动 HTTP 服务监听 Segway 运单状态回调。服务运行在后台，接收到回调后将事件写入日志文件。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/webhook_server.py start [--port <端口>] [--host <地址>]
```

参数说明：
- `--port`: 监听端口，默认 18800
- `--host`: 监听地址，默认 0.0.0.0

## stop - 停止 Webhook 服务

停止正在运行的 webhook 服务。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/webhook_server.py stop
```

## status - 查看服务状态

查看 webhook 服务是否在运行。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/webhook_server.py status
```

## events - 查看运单事件历史

查询指定运单或全部运单的回调事件记录。

```bash
# 查看所有事件（最近 20 条）
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/webhook_server.py events [--limit <数量>]

# 查看指定运单的事件
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/webhook_server.py events --task-id <运单ID>
```

## callback-url - 获取回调 URL

获取当前 webhook 服务的回调 URL，用于创建运单时传入 callbackUrl 参数。

```bash
/root/miniconda3/envs/openclaw/bin/python3 {baseDir}/scripts/webhook_server.py callback-url [--port <端口>]
```

## 完成判断规则
- 本 skill 全部为服务管理和事件查询操作，不涉及机器人写操作，无需 --dry-run / --confirm 确认。
- 当操作成功时直接将结果告知用户。
- 当操作失败时将错误信息告知用户。
