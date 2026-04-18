# Segway OpenClaw

通过 [OpenClaw](https://openclaw.com) 自然语言控制 Segway 配送机器人。

## 功能

- 7 个 Segway skill，覆盖楼宇查询、机器人管理、运单创建/管理、箱门控制、一站式配送、Webhook 回调
- 自然语言参数解析：支持通过楼宇名称、站点名称、机器人名称自动解析 ID
- 写操作两步确认（dry-run + confirm token）：防止模型幻觉导致误操作
- SegwayBench 评测系统：22 个任务，评估 AI agent 操作机器人的能力

## 快速开始

```bash
git clone <repo-url> segway-openclaw
cd segway-openclaw

# 安装到 openclaw workspace
./scripts/install.sh

# 编辑凭据
vim ~/.openclaw/workspace/.env

# 重启 openclaw
openclaw restart
```

## 目录结构

```
skills/                 Segway skill 代码（核心）
workspace/              OpenClaw workspace 模板
bench/                  SegwayBench 评测系统
docs/                   设计文档
scripts/                部署脚本
```

## Skills 一览

| Skill | 类型 | 说明 |
|-------|------|------|
| segway-area-map | 读 | 楼宇、站点、运力、地图查询 |
| segway-robot | 读 | 机器人列表、状态、位置查询 |
| segway-task-create | 写 | 创建引领/取送运单 |
| segway-task-manage | 读+写 | 运单状态查询、取消、优先级修改 |
| segway-box-control | 读+写 | 箱门开关、查询、取物确认 |
| segway-delivery | 写 | 一站式配送编排（自动查询+创建） |
| segway-webhook | 服务 | 运单状态回调接收 |

## 安全机制

所有写操作（创建运单、取消运单、开箱等）必须经过两步确认：

1. `--dry-run`：验证参数，输出操作摘要和一次性 confirm token
2. `--confirm <token>`：用户确认后执行

token 基于 HMAC-SHA256 签名，5 分钟有效，一次性使用。模型无法绕过。

## Benchmark

```bash
cd bench
python3 scripts/benchmark.py --model nvidia/deepseek-ai/deepseek-v3.2 --suite all
```

详见 [bench/README.md](bench/README.md)。

## 共享模块

| 模块 | 说明 |
|------|------|
| segway_auth.py | HMAC-SHA256 认证 + HTTP 请求 |
| segway_resolve.py | 名称→ID 模糊匹配解析 |
| segway_output.py | 统一输出格式（[TASK_COMPLETE]/[TASK_FAILED]） |
| segway_confirm.py | 写操作 dry-run + confirm token |

## License

MIT
