#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Segway 名称解析模块
提供楼宇名称→areaId、站点名称→stationId、机器人名称→robotId 的自动解析。
所有 Segway skill 脚本可通过此模块将自然语言名称转换为 API 所需的 ID。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import segway_auth


def fuzzy_match(name, candidates, key):
    """
    模糊匹配：精确 > 包含 > 反向包含。
    多个匹配时返回 (None, 候选名称列表)。
    无匹配时返回 (None, 全部名称列表)。
    成功时返回 (matched_dict, None)。
    """
    name = name.strip()
    # 精确匹配
    for c in candidates:
        if c.get(key, '') == name:
            return c, None
    # 包含匹配（输入包含在候选中）
    matches = [c for c in candidates if name in c.get(key, '')]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, [c.get(key, '') for c in matches]
    # 反向包含（候选包含在输入中）
    matches = [c for c in candidates if c.get(key, '') in name and c.get(key, '')]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, [c.get(key, '') for c in matches]
    return None, [c.get(key, '') for c in candidates]


def resolve_area_name(area_name):
    """
    通过楼宇名称解析 areaId。
    返回 areaId 字符串，失败时打印错误并返回 None。
    """
    result = segway_auth.call_api('GET', '/api/transport/areas')
    if not result or result.get('code') not in (200, '200'):
        msg = result.get('message', '未知错误') if result else 'API 请求失败'
        print(f'解析楼宇名称失败: {msg}')
        return None

    areas = result.get('data', [])
    if not areas:
        print('当前没有可用的楼宇')
        return None

    matched, names = fuzzy_match(area_name, areas, 'areaName')
    if matched:
        return matched['areaId']

    if names and len(names) <= 10:
        print(f'未找到楼宇 "{area_name}"，可用: {", ".join(names)}')
    else:
        print(f'未找到楼宇 "{area_name}"')
    return None


def resolve_station_name(area_id, station_name):
    """
    通过站点名称解析 stationId。
    返回 stationId 字符串，失败时打印错误并返回 None。
    """
    result = segway_auth.call_api('GET', f'/api/transport/area/{area_id}/stations')
    if not result or result.get('code') not in (200, '200'):
        msg = result.get('message', '未知错误') if result else 'API 请求失败'
        print(f'解析站点名称失败: {msg}')
        return None

    stations = result.get('data', [])
    if not stations:
        print(f'该楼宇下没有可用站点')
        return None

    matched, names = fuzzy_match(station_name, stations, 'stationName')
    if matched:
        return matched['stationId']

    if names and len(names) <= 20:
        print(f'未找到站点 "{station_name}"，可用: {", ".join(names)}')
    else:
        print(f'未找到站点 "{station_name}"')
    return None


def resolve_robot_name(robot_name):
    """
    通过机器人昵称解析 robotId。
    返回 robotId 字符串，失败时打印错误并返回 None。
    """
    result = segway_auth.call_api('GET', '/api/transport/robots')
    if not result or result.get('code') not in (200, '200'):
        msg = result.get('message', '未知错误') if result else 'API 请求失败'
        print(f'解析机器人名称失败: {msg}')
        return None

    robots = result.get('data', [])
    if not robots:
        print('当前没有可用的机器人')
        return None

    # 尝试用 robotNickName 匹配
    matched, names = fuzzy_match(robot_name, robots, 'robotNickName')
    if matched:
        return matched['robotId']

    # 回退：尝试用 robotName 匹配
    matched2, names2 = fuzzy_match(robot_name, robots, 'robotName')
    if matched2:
        return matched2['robotId']

    display_names = names or names2 or []
    if display_names and len(display_names) <= 10:
        print(f'未找到机器人 "{robot_name}"，可用: {", ".join(display_names)}')
    else:
        print(f'未找到机器人 "{robot_name}"')
    return None


def resolve_area_id(args):
    """
    从 args 中解析 area_id：优先用 --area-id，其次用 --area-name 自动解析。
    返回 area_id 或 None。
    """
    area_id = getattr(args, 'area_id', None)
    area_name = getattr(args, 'area_name', None)
    if area_id:
        return area_id
    if area_name:
        return resolve_area_name(area_name)
    return None


def resolve_station_id(args, area_id, id_attr='station_id', name_attr='station_name'):
    """
    从 args 中解析 station_id：优先用 ID 参数，其次用名称参数自动解析。
    """
    sid = getattr(args, id_attr, None)
    sname = getattr(args, name_attr, None)
    if sid:
        return sid
    if sname and area_id:
        return resolve_station_name(area_id, sname)
    return None


def resolve_robot_id(args):
    """
    从 args 中解析 robot_id：优先用 --robot-id，其次用 --robot-name 自动解析。
    """
    rid = getattr(args, 'robot_id', None)
    rname = getattr(args, 'robot_name', None)
    if rid:
        return rid
    if rname:
        return resolve_robot_name(rname)
    return None
