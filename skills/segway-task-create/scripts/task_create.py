#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 运单创建脚本
支持操作: guidance, special-guidance, take-deliver
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import segway_auth
import segway_resolve
import segway_output
import segway_confirm


def build_guidance_body(args):
    """构造引领运单请求体"""
    body = {
        'areaId': args.area_id,
        'taskType': 'Guidance',
        'stationId': args.station_id,
    }
    if args.priority_level is not None:
        body['priorityLevel'] = args.priority_level
    if args.out_id:
        body['outId'] = args.out_id
    if args.callback_url:
        body['callbackUrl'] = args.callback_url
    if args.remark:
        body['remark'] = args.remark
    return body


def build_special_guidance_body(args):
    """构造特殊引领运单请求体"""
    body = build_guidance_body(args)
    body['robotId'] = args.robot_id
    body['guidanceWaitTime'] = args.guidance_wait_time
    return body


def build_take_deliver_body(args):
    """构造取送运单请求体"""
    take_pair = {
        'stationId': args.take_station_id,
        'openCode': args.take_open_code,
        'action': 'TAKE',
    }

    deliver_pair = {
        'stationId': args.deliver_station_id,
        'action': 'DELIVER',
    }
    if args.verify:
        deliver_pair['verify'] = True
    if args.deliver_open_code:
        deliver_pair['openCode'] = args.deliver_open_code

    body = {
        'areaId': args.area_id,
        'taskType': 'TakeAndDeliver',
        'stationPairList': [take_pair, deliver_pair],
    }
    if args.priority_level is not None:
        body['priorityLevel'] = args.priority_level
    if args.wait_time is not None:
        body['waitTime'] = args.wait_time
    if args.verify_timeout is not None:
        body['verifyTimeout'] = args.verify_timeout
    if args.phone_num:
        body['phoneNum'] = args.phone_num
    if args.out_id:
        body['outId'] = args.out_id
    if args.callback_url:
        body['callbackUrl'] = args.callback_url
    if args.remark:
        body['remark'] = args.remark
    return body


def main():
    parser = argparse.ArgumentParser(description='Segway 运单创建')
    parser.add_argument('action', choices=['guidance', 'special-guidance', 'take-deliver'],
                        help='操作类型')
    parser.add_argument('--area-id', help='楼宇 ID')
    parser.add_argument('--area-name', help='楼宇名称（支持模糊匹配，自动解析为 area-id）')
    parser.add_argument('--station-id', help='站点 ID')
    parser.add_argument('--station-name', help='站点名称（支持模糊匹配，自动解析为 station-id）')
    parser.add_argument('--robot-id', help='机器人 ID')
    parser.add_argument('--robot-name', help='机器人名称（支持模糊匹配，自动解析为 robot-id）')
    parser.add_argument('--guidance-wait-time', type=int, help='引领等待时间（秒）')
    parser.add_argument('--take-station-id', help='取件站点 ID')
    parser.add_argument('--take-station-name', help='取件站点名称（支持模糊匹配）')
    parser.add_argument('--take-open-code', help='取件开箱码')
    parser.add_argument('--deliver-station-id', help='送件站点 ID')
    parser.add_argument('--deliver-station-name', help='送件站点名称（支持模糊匹配）')
    parser.add_argument('--deliver-open-code', help='送件开箱码')
    parser.add_argument('--verify', action='store_true', help='送件是否需要验证')
    parser.add_argument('--priority-level', type=int, help='优先级 (40-60)')
    parser.add_argument('--wait-time', type=int, help='等待时间（秒）')
    parser.add_argument('--verify-timeout', type=int, help='验证超时时间（秒）')
    parser.add_argument('--phone-num', help='手机号')
    parser.add_argument('--out-id', help='外部 ID')
    parser.add_argument('--callback-url', help='回调 URL')
    parser.add_argument('--remark', help='备注')
    parser.add_argument('--dry-run', action='store_true', help='仅验证参数并生成确认 token，不真正执行')
    parser.add_argument('--confirm', help='确认 token（由 --dry-run 生成）')
    args = parser.parse_args()

    # 解析 area_id（所有操作都需要）
    area_id = segway_resolve.resolve_area_id(args)

    if args.action == 'guidance':
        station_id = segway_resolve.resolve_station_id(args, area_id)
        if not area_id or not station_id:
            missing = []
            if not area_id:
                missing.append('楼宇 (--area-name 或 --area-id)')
            if not station_id:
                missing.append('站点 (--station-name 或 --station-id)')
            segway_output.print_param_error(
                '、'.join(missing),
                'task_create.py guidance --area-name "测试楼宇A" --station-name "1楼大厅"')
            sys.exit(1)
        args.area_id = area_id
        args.station_id = station_id
        body = build_guidance_body(args)

    elif args.action == 'special-guidance':
        station_id = segway_resolve.resolve_station_id(args, area_id)
        robot_id = segway_resolve.resolve_robot_id(args)
        if not area_id or not robot_id or not station_id or args.guidance_wait_time is None:
            missing = []
            if not area_id:
                missing.append('楼宇 (--area-name)')
            if not robot_id:
                missing.append('机器人 (--robot-name)')
            if not station_id:
                missing.append('站点 (--station-name)')
            if args.guidance_wait_time is None:
                missing.append('等待时间秒数 (--guidance-wait-time)')
            segway_output.print_param_error(
                '、'.join(missing),
                'task_create.py special-guidance --area-name "测试楼宇A" --robot-name "小蓝" --station-name "1楼大厅" --guidance-wait-time 60')
            sys.exit(1)
        args.area_id = area_id
        args.station_id = station_id
        args.robot_id = robot_id
        body = build_special_guidance_body(args)

    elif args.action == 'take-deliver':
        take_station_id = segway_resolve.resolve_station_id(
            args, area_id, id_attr='take_station_id', name_attr='take_station_name')
        deliver_station_id = segway_resolve.resolve_station_id(
            args, area_id, id_attr='deliver_station_id', name_attr='deliver_station_name')
        if not area_id or not take_station_id or not args.take_open_code or not deliver_station_id:
            missing = []
            if not area_id:
                missing.append('楼宇 (--area-name)')
            if not take_station_id:
                missing.append('取件站点 (--take-station-name)')
            if not args.take_open_code:
                missing.append('取件开箱码 (--take-open-code)')
            if not deliver_station_id:
                missing.append('送件站点 (--deliver-station-name)')
            segway_output.print_param_error(
                '、'.join(missing),
                'task_create.py take-deliver --area-name "测试楼宇A" --take-station-name "前台" --take-open-code 1234 --deliver-station-name "302房间"')
            sys.exit(1)
        args.area_id = area_id
        args.take_station_id = take_station_id
        args.deliver_station_id = deliver_station_id
        body = build_take_deliver_body(args)

    action_name = f'task_create.{args.action}'

    # dry-run 模式：验证参数，输出摘要和 confirm token
    if args.dry_run:
        segway_confirm.cleanup_expired_tokens()
        token = segway_confirm.generate_token(action_name, body)
        print('=== 操作预览（dry-run）===')
        print(f'操作: {args.action}')
        print(f'请求体:')
        print(json.dumps(body, ensure_ascii=False, indent=2))
        print(f'\n确认 token: {token}')
        print(f'\n[ACTION_PENDING] 请将以上操作摘要展示给用户确认。用户确认后，使用相同参数加 --confirm {token} 执行。')
        return

    # 正常执行模式：必须提供有效的 confirm token
    if not args.confirm:
        print('错误: 写操作需要先用 --dry-run 生成确认 token，再用 --confirm <token> 执行。')
        print(f'示例: task_create.py {args.action} ... --dry-run')
        print(f'\n[TASK_FAILED] 安全机制：写操作必须经过 dry-run + confirm 两步确认。请先加 --dry-run 参数运行，将操作摘要展示给用户确认后，再用 --confirm 执行。')
        sys.exit(1)

    # 验证 confirm token
    valid, err = segway_confirm.verify_token(args.confirm, action_name, body)
    if not valid:
        print(f'错误: confirm token 验证失败 - {err}')
        print(f'\n[TASK_FAILED] token 验证失败: {err}。请重新用 --dry-run 生成新的 token。')
        sys.exit(1)

    result = segway_auth.call_api('POST', '/api/transport/task/create', body=body)

    SUMMARIES = {
        'guidance': '引领运单创建成功，请将运单 ID 告知用户。任务已完成，无需再做其他操作。',
        'special-guidance': '特殊引领运单创建成功，请将运单 ID 告知用户。任务已完成，无需再做其他操作。',
        'take-deliver': '取送运单创建成功，请将运单 ID 告知用户。任务已完成，无需再做其他操作。',
    }
    segway_output.handle_result(result, SUMMARIES.get(args.action))


if __name__ == '__main__':
    main()
