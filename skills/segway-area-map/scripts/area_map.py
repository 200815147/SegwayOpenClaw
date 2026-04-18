#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 楼宇与地图查询脚本
支持操作: areas, stations, service, map-list, map-info
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import segway_auth
import segway_resolve
import segway_output


def main():
    parser = argparse.ArgumentParser(description='Segway 楼宇与地图查询')
    parser.add_argument('action', choices=['areas', 'stations', 'service', 'map-list', 'map-info'],
                        help='操作类型')
    parser.add_argument('--area-id', help='楼宇 ID')
    parser.add_argument('--area-name', help='楼宇名称（支持模糊匹配，自动解析为 area-id）')
    parser.add_argument('--map-id', help='地图 ID')
    args = parser.parse_args()

    if args.action == 'areas':
        result = segway_auth.call_api('GET', '/api/transport/areas')

    elif args.action == 'stations':
        area_id = segway_resolve.resolve_area_id(args)
        if not area_id:
            segway_output.print_param_error(
                '楼宇 ID 或楼宇名称',
                'area_map.py stations --area-name "测试楼宇A"  或  area_map.py stations --area-id xxx')
            sys.exit(1)
        result = segway_auth.call_api('GET', f'/api/transport/area/{area_id}/stations')

    elif args.action == 'service':
        area_id = segway_resolve.resolve_area_id(args)
        if not area_id:
            segway_output.print_param_error(
                '楼宇 ID 或楼宇名称',
                'area_map.py service --area-name "测试楼宇A"')
            sys.exit(1)
        result = segway_auth.call_api('GET', '/api/transport/area/service',
                                      query_params={'areaId': area_id})

    elif args.action == 'map-list':
        area_id = segway_resolve.resolve_area_id(args)
        if not area_id:
            segway_output.print_param_error(
                '楼宇 ID 或楼宇名称',
                'area_map.py map-list --area-name "测试楼宇A"')
            sys.exit(1)
        result = segway_auth.call_api('GET',
                                      '/business-robot-area/api/transport/customer/area/map/list',
                                      query_params={'areaId': area_id})

    elif args.action == 'map-info':
        area_id = segway_resolve.resolve_area_id(args)
        if not area_id or not args.map_id:
            missing = []
            if not area_id:
                missing.append('楼宇 ID 或楼宇名称')
            if not args.map_id:
                missing.append('地图 ID (--map-id)')
            segway_output.print_param_error(
                '、'.join(missing),
                'area_map.py map-info --area-name "测试楼宇A" --map-id xxx')
            sys.exit(1)
        result = segway_auth.call_api('GET',
                                      '/business-robot-area/api/transport/customer/map/info',
                                      query_params={'areaId': area_id, 'mapId': args.map_id})

    SUMMARIES = {
        'areas': '已获取楼宇列表，请将结果告知用户。',
        'stations': '已获取站点列表，请将结果告知用户。',
        'service': '已查询运力服务状态，请将结果告知用户。',
        'map-list': '已获取楼层地图列表，请将结果告知用户。',
        'map-info': '已获取地图详细信息，请将结果告知用户。',
    }
    segway_output.handle_result(result, SUMMARIES.get(args.action))


if __name__ == '__main__':
    main()
