---
name: segway-area-map
description: 查询 Segway 配送机器人的楼宇列表、站点信息、运力服务状态和地图数据。支持获取楼宇详情、楼宇下的站点列表、楼宇运力可用状态、楼层地图列表和地图详细信息。
---

# Segway 楼宇与地图查询
查询配送机器人的楼宇、站点、运力状态和地图信息。

## 完成判断规则
- 当脚本输出包含 `[TASK_COMPLETE]` 时，表示操作已成功完成，直接将结果告知用户即可，不要再调用任何 skill。
- 当脚本输出包含 `[TASK_FAILED]` 时，表示操作失败，将错误信息告知用户，不要重试。

## 操作手册

### 用户只是想查询信息
调用对应命令后，看到 `[TASK_COMPLETE]` 就将结果告知用户，任务结束。

### 用户想查询后再做其他操作（如创建运单）
1. 先调用查询命令（如 `areas` 或 `stations`）
2. 将查询结果告知用户，等待用户的下一步指示
3. 不要自动假设用户想做什么，除非用户明确说了

### 提示
- 如果用户想直接创建运单，推荐使用 `segway-delivery` skill，它会自动完成查询和匹配
- 如果用户想查询后手动选择，用本 skill 查询后等待用户指示
- 本 skill 全部为读操作（查询），不涉及写操作，无需 --dry-run / --confirm 确认

## areas - 获取楼宇列表
查询所有可用的楼宇（配送区域），返回 areaId、楼宇名称、经纬度等信息。
```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py areas
```

## stations - 获取站点列表
查询指定楼宇下的所有站点信息，需要提供楼宇 ID 或楼宇名称。
```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py stations --area-id <楼宇ID>
# 或使用楼宇名称（自动解析）
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py stations --area-name <楼宇名称>
```

## service - 查询运力服务状态
查询指定楼宇的运力可用状态，了解该区域是否有可用的配送机器人。
```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py service --area-id <楼宇ID>
# 或使用楼宇名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py service --area-name <楼宇名称>
```

## map-list - 获取楼层地图列表
查询指定楼宇的楼层和地图信息列表。
```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py map-list --area-id <楼宇ID>
# 或使用楼宇名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py map-list --area-name <楼宇名称>
```

## map-info - 获取地图详细信息
根据楼宇 ID（或名称）和地图 ID 查询地图的详细数据。
```bash
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py map-info --area-id <楼宇ID> --map-id <地图ID>
# 或使用楼宇名称
/root/miniconda3/envs/openclaw/bin/python3 /root/.openclaw/workspace/skills/segway-area-map/scripts/area_map.py map-info --area-name <楼宇名称> --map-id <地图ID>
```
