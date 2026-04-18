# 实施计划：Segway API Skills 拆分

## 概述

将现有单一的 segway-api skill 拆分为 5 个功能内聚的独立 skill，共享一个认证模块。实现语言为 Python，脚本部署在 `/root/.openclaw/workspace/skills/` 目录下。每个任务增量构建，确保前序任务完成后后续任务可正常运行。

## 任务

- [x] 1. 创建共享认证模块 `segway_auth.py`
  - [x] 1.1 创建 `/root/.openclaw/workspace/skills/segway_auth.py`
    - 实现 `gmt_time()` 函数，生成 GMT 格式时间字符串
    - 实现 `gen_authorization(access_name, access_key, date, url, method)` 函数，使用 HMAC-SHA256 生成 Authorization 头
    - 实现 `get_config()` 函数，从环境变量 `SEGWAY_ACCESS_NAME`、`SEGWAY_ACCESS_KEY`、`SEGWAY_API_DOMAIN` 读取配置，缺失时输出错误并终止
    - 实现 `send_request(method, url, date, authorization, body=None)` 函数，支持 GET/POST，禁用代理
    - 实现 `call_api(method, path, body=None, query_params=None)` 高层封装函数
    - 保持与现有 `/root/tmp/main.py` 的认证逻辑一致
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 8.1, 8.6_

  - [x] 1.2 为认证模块编写单元测试
    - 测试 `gmt_time()` 返回格式正确
    - 测试 `gen_authorization()` 签名结果与已知输入匹配
    - 测试 `get_config()` 在环境变量缺失时抛出错误
    - _需求: 1.1, 1.2, 1.5_

- [-] 2. 创建楼宇与地图查询 Skill (`segway-area-map`)
  - [x] 2.1 创建 `/root/.openclaw/workspace/skills/segway-area-map/SKILL.md`
    - 包含 YAML frontmatter（name、description 字段）
    - description 使用中文，包含"楼宇"、"站点"、"地图"、"运力"等关键词
    - 列出所有操作命令：areas、stations、service、map-list、map-info
    - 使用 `{baseDir}` 占位符引用脚本路径
    - 说明依赖的环境变量
    - _需求: 2.6, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 2.2 创建 `/root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py`
    - 通过 `sys.path` 导入共享认证模块 `segway_auth`
    - 使用 argparse 解析命令行参数（action + 各操作所需参数）
    - 实现 `areas` 操作：调用 `GET /api/transport/areas`
    - 实现 `stations` 操作：接受 areaId，调用 `GET /api/transport/area/{areaId}/stations`
    - 实现 `service` 操作：接受 areaId，调用 `GET /api/transport/area/service`
    - 实现 `map-list` 操作：接受 areaId，调用 `GET /business-robot-area/api/transport/customer/area/map/list`
    - 实现 `map-info` 操作：接受 areaId 和 mapId，调用 `GET /business-robot-area/api/transport/customer/map/info`
    - 成功时格式化输出 JSON data 字段，失败时输出 code 和 message
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 8.2, 8.3, 8.4, 8.5_

  - [x] 2.3 为 area_map.py 编写单元测试
    - 测试各操作的参数解析
    - 测试错误响应的输出格式
    - _需求: 2.7, 8.4_

- [x] 3. 创建机器人信息查询 Skill (`segway-robot`)
  - [x] 3.1 创建 `/root/.openclaw/workspace/skills/segway-robot/SKILL.md`
    - 包含 YAML frontmatter（name、description 字段）
    - description 使用中文，包含"机器人"、"状态"、"位置"、"电量"等关键词
    - 列出所有操作命令：list、status、location、locations、sort-list、robot-info、robots-info
    - 使用 `{baseDir}` 占位符，说明环境变量依赖
    - _需求: 3.8, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 3.2 创建 `/root/.openclaw/workspace/skills/segway-robot/scripts/robot.py`
    - 导入共享认证模块，使用 argparse 解析参数
    - 实现 `list` 操作：调用 `GET /api/transport/robots`
    - 实现 `status` 操作：接受 robotId，调用 `GET /api/transport/robot/{robotId}/status`
    - 实现 `location` 操作：接受 areaId 和 robotId，调用 `GET /business-robot-area/api/transport/customer/robot/current/location/info`
    - 实现 `locations` 操作：接受 areaId 和 robotIds，调用 `POST /business-robot-area/api/transport/customer/robots/current/location/info`
    - 实现 `sort-list` 操作：接受 areaId，调用 `GET /business-robot-area/api/transport/customer/robot/sort/list`
    - 实现 `robot-info` 操作：接受 robotId，调用 `POST /business-order/api/transport/customer/robot/current/info`
    - 实现 `robots-info` 操作：接受 robotIds，调用 `POST /business-order/api/transport/customer/robots/current/info`
    - 统一错误处理和 JSON 格式化输出
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9, 8.2, 8.3, 8.4_

  - [x] 3.3 为 robot.py 编写单元测试
    - 测试各操作的参数解析和请求构造
    - _需求: 3.9, 8.4_

- [x] 4. 检查点 - 验证认证模块和查询类 Skill
  - 确保所有测试通过，如有问题请向用户确认。
  - 验证 segway_auth.py 可被各 skill 脚本正确导入
  - 验证 SKILL.md 格式符合 openclaw 规范

- [x] 5. 创建运单创建 Skill (`segway-task-create`)
  - [x] 5.1 创建 `/root/.openclaw/workspace/skills/segway-task-create/SKILL.md`
    - 包含 YAML frontmatter（name、description 字段）
    - description 使用中文，包含"下发运单"、"引领"、"取送"、"配送任务"、"创建任务"等关键词
    - 列出所有操作命令：guidance、special-guidance、take-deliver
    - 使用 `{baseDir}` 占位符，说明环境变量依赖
    - _需求: 4.7, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 5.2 创建 `/root/.openclaw/workspace/skills/segway-task-create/scripts/task_create.py`
    - 导入共享认证模块，使用 argparse 解析参数
    - 实现 `guidance` 操作：接受 areaId、stationId 及可选参数（priorityLevel、outId、callbackUrl、remark），构造 taskType=Guidance 请求体，调用 `POST /api/transport/task/create`
    - 实现 `special-guidance` 操作：接受 areaId、robotId、stationId、guidanceWaitTime 及可选参数，构造带 robotId 的 Guidance 请求体
    - 实现 `take-deliver` 操作：接受 areaId、取件 stationId、取件 openCode、送件 stationId 及可选参数（verify、送件 openCode、priorityLevel、waitTime、verifyTimeout、phoneNum、outId、callbackUrl、remark），构造 taskType=TakeAndDeliver 请求体
    - 统一错误处理，返回 taskId 或错误信息
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 8.2, 8.3, 8.4_

  - [x] 5.3 为 task_create.py 编写单元测试
    - 测试各运单类型的请求体构造
    - 测试可选参数的正确传递
    - _需求: 4.8, 8.4_

- [x] 6. 创建运单管理 Skill (`segway-task-manage`)
  - [x] 6.1 创建 `/root/.openclaw/workspace/skills/segway-task-manage/SKILL.md`
    - 包含 YAML frontmatter（name、description 字段）
    - description 使用中文，包含"取消运单"、"运单状态"、"优先级"、"历史订单"、"重新配送"等关键词
    - 列出所有操作命令：cancel、priority、status、history、redeliver
    - 使用 `{baseDir}` 占位符，说明环境变量依赖
    - _需求: 5.6, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 6.2 创建 `/root/.openclaw/workspace/skills/segway-task-manage/scripts/task_manage.py`
    - 导入共享认证模块，使用 argparse 解析参数
    - 实现 `cancel` 操作：接受 taskId，调用 `POST /api/transport/task/cancel`
    - 实现 `priority` 操作：接受 taskId 和 priorityLevel（40-60），调用 `POST /api/transport/task/priority`
    - 实现 `status` 操作：接受 taskId，调用 `GET /api/transport/task/{taskId}/status`
    - 实现 `history` 操作：接受 startTime 和 endTime（毫秒时间戳），调用 `GET /api/transport/task/history`
    - 实现 `redeliver` 操作：接受 robotId 和 taskIds，调用 `POST /api/transport/delay/redeliver`
    - 统一错误处理和 JSON 格式化输出
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7, 8.2, 8.3, 8.4_

  - [x] 6.3 为 task_manage.py 编写单元测试
    - 测试各操作的参数解析和请求构造
    - _需求: 5.7, 8.4_

- [ ] 7. 创建箱门控制 Skill (`segway-box-control`)
  - [x] 7.1 创建 `/root/.openclaw/workspace/skills/segway-box-control/SKILL.md`
    - 包含 YAML frontmatter（name、description 字段）
    - description 使用中文，包含"箱门"、"开箱"、"关箱"、"取物"、"取件"等关键词
    - 列出所有操作命令：open、close、info、put-verify、take-verify
    - 使用 `{baseDir}` 占位符，说明环境变量依赖
    - _需求: 6.6, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 7.2 创建 `/root/.openclaw/workspace/skills/segway-box-control/scripts/box_control.py`
    - 导入共享认证模块，使用 argparse 解析参数
    - 实现 `open` 操作：接受 robotId 和 boxIndexes，调用 `POST /api/transport/robot/boxs/open`
    - 实现 `close` 操作：接受 robotId 和 boxIndexes，调用 `POST /api/transport/robot/boxs/close`
    - 实现 `info` 操作：接受 robotId，调用 `GET /api/transport/robot/{robotId}/box/size`
    - 实现 `put-verify` 操作：接受 robotId 和 taskId，调用 `POST /api/transport/task/put/verify`
    - 实现 `take-verify` 操作：接受 robotId 和 taskId，调用 `POST /api/transport/task/take/verify`
    - 统一错误处理和 JSON 格式化输出
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 8.2, 8.3, 8.4_

  - [x] 7.3 为 box_control.py 编写单元测试
    - 测试各操作的参数解析和请求构造
    - _需求: 6.7, 8.4_

- [x] 8. 检查点 - 验证所有 Skill 完整性
  - 确保所有测试通过，如有问题请向用户确认。
  - 验证 5 个 skill 的 SKILL.md 格式统一
  - 验证所有脚本可通过命令行正确执行

- [x] 9. 清理旧 Skill 并完成集成
  - [x] 9.1 删除旧的 `/root/.openclaw/workspace/skills/segway-api/` 目录
    - 移除旧的 SKILL.md 文件
    - 确认新的 5 个 skill 已完全替代旧 skill 的功能
    - _需求: 2.6, 3.8, 4.7, 5.6, 6.6_

  - [x] 9.2 验证所有 skill 的端到端可用性
    - 确认每个 skill 的 SKILL.md 可被 openclaw 识别
    - 确认脚本使用 `/root/miniconda3/envs/openclaw/bin/python3` 解释器
    - 确认环境变量配置正确
    - _需求: 7.6, 8.5_

- [x] 10. 最终检查点 - 全部完成
  - 确保所有测试通过，如有问题请向用户确认。

## 备注

- 标记 `*` 的任务为可选，可跳过以加速 MVP 交付
- 每个任务引用了具体的需求编号以确保可追溯性
- 检查点任务确保增量验证
- 所有脚本使用 Python 3，解释器路径为 `/root/miniconda3/envs/openclaw/bin/python3`
