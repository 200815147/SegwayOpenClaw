#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 机器人信息查询脚本
支持操作: list, status, location, locations, sort-list, robot-info, robots-info
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
    parser = argparse.ArgumentParser(description='Segway 机器人信息查询')
    parser.add_argument('action',
                        choices=['list', 'status', 'location', 'locations',
                                 'sort-list', 'robot-info', 'robots-info'],
                        help='操作类型')
    parser.add_argument('--robot-id', help='机器人 ID')
    parser.add_argument('--robot-name', help='机器人名称（支持模糊匹配，自动解析为 robot-id）')
    parser.add_argument('--robot-ids', help='多个机器人 ID（逗号分隔）')
    parser.add_argument('--area-id', help='楼宇 ID')
    parser.add_argument('--area-name', help='楼宇名称（支持模糊匹配，自动解析为 area-id）')
    args = parser.parse_args()

    if args.action == 'list':
        result = segway_auth.call_api('GET', '/api/transport/robots')

    elif args.action == 'status':
        robot_id = segway_resolve.resolve_robot_id(args)
        if not robot_id:
            segway_output.print_param_error(
                '机器人 ID 或机器人名称',
                'robot.py status --robot-name "小蓝"  或  robot.py status --robot-id xxx')
            sys.exit(1)
        result = segway_auth.call_api('GET', f'/api/transport/robot/{robot_id}/status')

    elif args.action == 'location':
        area_id = segway_resolve.resolve_area_id(args)
        robot_id = segway_resolve.resolve_robot_id(args)
        if not area_id or not robot_id:
            missing = []
            if not area_id:
                missing.append('楼宇 ID 或楼宇名称')
            if not robot_id:
                missing.append('机器人 ID 或机器人名称')
            segway_output.print_param_error(
                '、'.join(missing),
                'robot.py location --area-name "测试楼宇A" --robot-name "小蓝"')
            sys.exit(1)
        result = segway_auth.call_api('GET',
                                      '/business-robot-area/api/transport/customer/robot/current/location/info',
                                      query_params={'areaId': area_id, 'robotId': robot_id})

    elif args.action == 'locations':
        area_id = segway_resolve.resolve_area_id(args)
        if not area_id or not args.robot_ids:
            missing = []
            if not area_id:
                missing.append('楼宇 ID 或楼宇名称')
            if not args.robot_ids:
                missing.append('机器人 ID 列表 (--robot-ids，逗号分隔)')
            segway_output.print_param_error(
                '、'.join(missing),
                'robot.py locations --area-name "测试楼宇A" --robot-ids id1,id2')
            sys.exit(1)
        robot_id_list = [rid.strip() for rid in args.robot_ids.split(',')]
        body = {'areaId': area_id, 'robotIds': robot_id_list}
        result = segway_auth.call_api('POST',
                                      '/business-robot-area/api/transport/customer/robots/current/location/info',
                                      body=body)

    elif args.action == 'sort-list':
        area_id = segway_resolve.resolve_area_id(args)
        if not area_id:
            segway_output.print_param_error(
                '楼宇 ID 或楼宇名称',
                'robot.py sort-list --area-name "测试楼宇A"')
            sys.exit(1)
        result = segway_auth.call_api('GET',
                                      '/business-robot-area/api/transport/customer/robot/sort/list',
                                      query_params={'areaId': area_id})

    elif args.action == 'robot-info':
        robot_id = segway_resolve.resolve_robot_id(args)
        if not robot_id:
            segway_output.print_param_error(
                '机器人 ID 或机器人名称',
                'robot.py robot-info --robot-name "小蓝"')
            sys.exit(1)
        body = {'robotId': robot_id}
        result = segway_auth.call_api('POST',
                                      '/business-order/api/transport/customer/robot/current/info',
                                      body=body)

    elif args.action == 'robots-info':
        if not args.robot_ids:
            segway_output.print_param_error(
                '机器人 ID 列表 (--robot-ids，逗号分隔)',
                'robot.py robots-info --robot-ids id1,id2')
            sys.exit(1)
        robot_id_list = [rid.strip() for rid in args.robot_ids.split(',')]
        body = {'robotIds': robot_id_list}
        result = segway_auth.call_api('POST',
                                      '/business-order/api/transport/customer/robots/current/info',
                                      body=body)

    SUMMARIES = {
        'list': '已获取机器人列表，请将结果告知用户。',
        'status': '已获取机器人状态，请将结果告知用户。',
        'location': '已获取机器人位置信息，请将结果告知用户。',
        'locations': '已获取多个机器人位置信息，请将结果告知用户。',
        'sort-list': '已获取楼宇下机器人排序列表，请将结果告知用户。',
        'robot-info': '已获取机器人实时状态及订单信息，请将结果告知用户。',
        'robots-info': '已获取多个机器人实时状态及订单信息，请将结果告知用户。',
    }
    segway_output.handle_result(result, SUMMARIES.get(args.action))


if __name__ == '__main__':
    main()
