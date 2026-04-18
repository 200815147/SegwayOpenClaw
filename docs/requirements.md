# 需求文档

## 简介

将 Segway Robotics 配送机器人的云端 API 文档转化为 openclaw skills，使用户能够通过自然语言描述意图，由 openclaw 匹配并调用对应的 skill，最终转化为实际的 Segway API 调用。每个 skill 对应一组功能内聚的 API 操作，底层共享 HMAC-SHA256 签名认证逻辑，使用 Python 实现。

## 术语表

- **Skill**: openclaw 中的功能模块，包含 `SKILL.md` 描述文件和可执行脚本，用于将自然语言映射为具体操作。
- **Segway_API**: Segway Robotics 配送机器人统一运力服务的 HTTPS API 接口集合。
- **Auth_Module**: 共享的 Python 认证模块，实现 HMAC-SHA256 签名算法，供所有 skill 脚本复用。
- **Area（楼宇）**: 机器人可执行任务的区域范围，通过 areaId 唯一标识。
- **Station（站点）**: 机器人可到达的目标地点，通过 stationId 唯一标识。
- **Task（运单）**: 机器人执行任务的最小单位，通过 taskId 唯一标识。
- **Robot（机器人）**: 楼宇中执行任务的主体，通过 robotId 唯一标识。
- **openclaw**: 一个通过自然语言调用 skill 的代理框架，skill 通过 SKILL.md 中的描述进行匹配。

## 需求

### 需求 1：共享认证模块

**用户故事：** 作为开发者，我希望所有 Segway API skill 共享同一套认证逻辑，以便避免代码重复并统一管理 access_name 和 access_key。

#### 验收标准

1. THE Auth_Module SHALL 提供 `gmt_time()` 函数，生成符合 `%a, %d %b %Y %H:%M:%S %Z` 格式的 GMT 时间字符串。
2. THE Auth_Module SHALL 提供 `gen_authorization(access_name, access_key, date, url, method)` 函数，使用 HMAC-SHA256 算法生成 `SEGWAY {access_name}:{signature}` 格式的 Authorization 头。
3. THE Auth_Module SHALL 提供 `send_request(method, url, date, authorization, body=None)` 函数，支持 GET 和 POST 请求，POST 请求以 JSON 格式携带请求体。
4. THE Auth_Module SHALL 从环境变量 `SEGWAY_ACCESS_NAME` 和 `SEGWAY_ACCESS_KEY` 读取认证凭据。
5. IF 环境变量 `SEGWAY_ACCESS_NAME` 或 `SEGWAY_ACCESS_KEY` 未设置，THEN THE Auth_Module SHALL 输出明确的错误提示信息并终止执行。
6. THE Auth_Module SHALL 将 API 域名 `https://api-gate-delivery.loomo.com` 作为默认值，并支持通过环境变量 `SEGWAY_API_DOMAIN` 覆盖。

### 需求 2：楼宇与地图信息查询 Skill

**用户故事：** 作为用户，我希望通过自然语言查询楼宇列表、站点信息、运力状态和地图数据，以便了解配送区域的基本情况。

#### 验收标准

1. WHEN 用户请求获取楼宇列表时，THE Skill 脚本 SHALL 调用 `GET /api/transport/areas` 并返回包含 areaId、areaName、经纬度的楼宇列表。
2. WHEN 用户请求获取指定楼宇的站点信息时，THE Skill 脚本 SHALL 接受 areaId 参数并调用 `GET /api/transport/area/{areaId}/stations`，返回站点详细信息。
3. WHEN 用户请求查询楼宇运力服务状态时，THE Skill 脚本 SHALL 接受 areaId 参数并调用 `GET /api/transport/area/service`，返回运力可用状态。
4. WHEN 用户请求获取楼宇楼层信息时，THE Skill 脚本 SHALL 接受 areaId 参数并调用 `GET /business-robot-area/api/transport/customer/area/map/list`，返回楼层和地图信息。
5. WHEN 用户请求根据地图 ID 获取地图数据时，THE Skill 脚本 SHALL 接受 areaId 和 mapId 参数并调用 `GET /business-robot-area/api/transport/customer/map/info`，返回地图详细数据。
6. THE Skill 的 SKILL.md SHALL 包含中文描述，涵盖"楼宇"、"站点"、"地图"、"运力"等关键词，使 openclaw 能够从自然语言中匹配到该 skill。
7. IF API 返回错误码（非200），THEN THE Skill 脚本 SHALL 输出错误码和错误消息内容。

### 需求 3：机器人信息查询 Skill

**用户故事：** 作为用户，我希望通过自然语言查询机器人列表、状态、位置和实时订单信息，以便掌握机器人的运行情况。

#### 验收标准

1. WHEN 用户请求获取机器人列表时，THE Skill 脚本 SHALL 调用 `GET /api/transport/robots` 并返回包含 robotId、昵称、所属楼宇的机器人列表。
2. WHEN 用户请求获取指定机器人状态时，THE Skill 脚本 SHALL 接受 robotId 参数并调用 `GET /api/transport/robot/{robotId}/status`，返回机器人当前状态。
3. WHEN 用户请求获取单个机器人位置时，THE Skill 脚本 SHALL 接受 areaId 和 robotId 参数并调用 `GET /business-robot-area/api/transport/customer/robot/current/location/info`，返回机器人坐标和地图信息。
4. WHEN 用户请求获取多个机器人位置时，THE Skill 脚本 SHALL 接受 areaId 和 robotIds 参数并调用 `POST /business-robot-area/api/transport/customer/robots/current/location/info`，返回多个机器人的位置数据。
5. WHEN 用户请求获取楼宇下有序机器人列表时，THE Skill 脚本 SHALL 接受 areaId 参数并调用 `GET /business-robot-area/api/transport/customer/robot/sort/list`，返回机器人列表。
6. WHEN 用户请求获取机器人实时状态及订单时，THE Skill 脚本 SHALL 接受 robotId 参数并调用 `POST /business-order/api/transport/customer/robot/current/info`，返回机器人状态和订单数据。
7. WHEN 用户请求获取多个机器人实时状态及订单时，THE Skill 脚本 SHALL 接受 robotIds 参数并调用 `POST /business-order/api/transport/customer/robots/current/info`，返回多个机器人的状态和订单数据。
8. THE Skill 的 SKILL.md SHALL 包含中文描述，涵盖"机器人"、"状态"、"位置"、"电量"等关键词。
9. IF API 返回错误码（非200），THEN THE Skill 脚本 SHALL 输出错误码和错误消息内容。

### 需求 4：运单创建 Skill

**用户故事：** 作为用户，我希望通过自然语言下发引领运单、特殊引领运单和取送运单，以便控制机器人执行配送任务。

#### 验收标准

1. WHEN 用户请求创建引领运单时，THE Skill 脚本 SHALL 接受 areaId 和 stationId 参数，构造 taskType 为 `Guidance` 的请求体，调用 `POST /api/transport/task/create`，返回 taskId。
2. WHEN 用户请求创建引领运单并指定可选参数时，THE Skill 脚本 SHALL 支持 priorityLevel、outId、callbackUrl、remark 可选参数。
3. WHEN 用户请求创建特殊引领运单时，THE Skill 脚本 SHALL 接受 areaId、robotId、stationId 和 guidanceWaitTime 参数，构造 taskType 为 `Guidance` 且携带 robotId 的请求体，调用 `POST /api/transport/task/create`，返回 taskId。
4. WHEN 用户请求创建取送运单时，THE Skill 脚本 SHALL 接受 areaId、取件站点 stationId、取件 openCode、送件站点 stationId 参数，构造 taskType 为 `TakeAndDeliver` 的请求体，调用 `POST /api/transport/task/create`，返回 taskId。
5. WHEN 用户请求创建取送运单并指定送件验证时，THE Skill 脚本 SHALL 支持 verify 和送件 openCode 参数。
6. WHEN 用户请求创建取送运单并指定可选参数时，THE Skill 脚本 SHALL 支持 priorityLevel、waitTime、verifyTimeout、phoneNum、outId、callbackUrl、remark 可选参数。
7. THE Skill 的 SKILL.md SHALL 包含中文描述，涵盖"下发运单"、"引领"、"取送"、"配送任务"、"创建任务"等关键词。
8. IF API 返回错误码（如 9012 无可用机器人），THEN THE Skill 脚本 SHALL 输出错误码和错误消息内容。

### 需求 5：运单管理 Skill

**用户故事：** 作为用户，我希望通过自然语言取消运单、修改优先级、查询运单状态和历史记录，以便管理已有的配送任务。

#### 验收标准

1. WHEN 用户请求取消运单时，THE Skill 脚本 SHALL 接受 taskId 参数并调用 `POST /api/transport/task/cancel`。
2. WHEN 用户请求修改运单优先级时，THE Skill 脚本 SHALL 接受 taskId 和 priorityLevel（40-60）参数并调用 `POST /api/transport/task/priority`。
3. WHEN 用户请求查询运单状态时，THE Skill 脚本 SHALL 接受 taskId 参数并调用 `GET /api/transport/task/{taskId}/status`，返回运单当前状态。
4. WHEN 用户请求查询历史运单时，THE Skill 脚本 SHALL 接受 startTime 和 endTime（毫秒时间戳）参数并调用 `GET /api/transport/task/history`，返回历史运单列表。
5. WHEN 用户请求滞留件重新配送时，THE Skill 脚本 SHALL 接受 robotId 和 taskIds 参数并调用 `POST /api/transport/delay/redeliver`。
6. THE Skill 的 SKILL.md SHALL 包含中文描述，涵盖"取消运单"、"运单状态"、"优先级"、"历史订单"、"重新配送"等关键词。
7. IF API 返回错误码（非200），THEN THE Skill 脚本 SHALL 输出错误码和错误消息内容。

### 需求 6：机器人箱门控制 Skill

**用户故事：** 作为用户，我希望通过自然语言控制机器人箱门的开关和查询箱门信息，以及进行取物和物品取出操作。

#### 验收标准

1. WHEN 用户请求打开机器人箱门时，THE Skill 脚本 SHALL 接受 robotId 和 boxIndexes 参数并调用 `POST /api/transport/robot/boxs/open`。
2. WHEN 用户请求关闭机器人箱门时，THE Skill 脚本 SHALL 接受 robotId 和 boxIndexes 参数并调用 `POST /api/transport/robot/boxs/close`。
3. WHEN 用户请求查询机器人箱门部署信息时，THE Skill 脚本 SHALL 接受 robotId 参数并调用 `GET /api/transport/robot/{robotId}/box/size`，返回箱格数、剩余箱格数和预占箱格数。
4. WHEN 用户请求机器人取物确认时，THE Skill 脚本 SHALL 接受 robotId 和 taskId 参数并调用 `POST /api/transport/task/put/verify`。
5. WHEN 用户请求物品取出确认时，THE Skill 脚本 SHALL 接受 robotId 和 taskId 参数并调用 `POST /api/transport/task/take/verify`。
6. THE Skill 的 SKILL.md SHALL 包含中文描述，涵盖"箱门"、"开箱"、"关箱"、"取物"、"取件"等关键词。
7. IF API 返回错误码（非200），THEN THE Skill 脚本 SHALL 输出错误码和错误消息内容。

### 需求 7：Skill 描述文件规范

**用户故事：** 作为 openclaw 用户，我希望每个 skill 的 SKILL.md 文件包含清晰的中文描述和使用示例，以便 openclaw 能准确地将自然语言意图匹配到正确的 skill。

#### 验收标准

1. THE SKILL.md SHALL 包含 YAML frontmatter，定义 `name` 和 `description` 字段。
2. THE SKILL.md 的 `description` 字段 SHALL 使用中文描述该 skill 的功能，包含核心关键词以提高自然语言匹配准确度。
3. THE SKILL.md SHALL 列出该 skill 支持的所有操作命令及其参数说明。
4. THE SKILL.md SHALL 使用 `{baseDir}` 占位符引用脚本路径，使 openclaw 能正确定位脚本文件。
5. THE SKILL.md SHALL 说明该 skill 依赖的环境变量（`SEGWAY_ACCESS_NAME`、`SEGWAY_ACCESS_KEY`）。
6. WHEN 用户使用自然语言描述与某个 skill 功能相关的意图时，THE SKILL.md 的描述 SHALL 包含足够的关键词使 openclaw 能够匹配到该 skill。

### 需求 8：脚本执行与输出规范

**用户故事：** 作为 openclaw 代理，我希望 skill 脚本的输出格式统一且易于解析，以便将 API 响应转化为用户可理解的自然语言回复。

#### 验收标准

1. THE Skill 脚本 SHALL 使用 Python 3 编写，与现有 `/root/tmp/main.py` 的认证逻辑保持一致。
2. THE Skill 脚本 SHALL 通过命令行参数接收操作类型和必要参数。
3. WHEN API 调用成功时，THE Skill 脚本 SHALL 以格式化的 JSON 输出 API 响应的 data 字段内容。
4. IF API 调用失败，THEN THE Skill 脚本 SHALL 输出包含 code 和 message 的错误信息。
5. THE Skill 脚本 SHALL 使用 `/root/miniconda3/envs/openclaw/bin/python3` 作为 Python 解释器路径。
6. THE Skill 脚本 SHALL 禁用代理设置（`proxies={"http": None, "https": None}`），与现有 main.py 行为一致。
