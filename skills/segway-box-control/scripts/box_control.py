#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 箱门控制脚本
支持操作: open, close, info, put-verify, take-verify
写操作需要 --dry-run + --confirm 两步确认。
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


def parse_box_indexes(value):
    """将逗号分隔的字符串解析为整数列表，如 '1,2,3' -> [1, 2, 3]"""
    try:
        return [int(x.strip()) for x in value.split(',')]
    except ValueError:
        raise argparse.ArgumentTypeError(f'boxIndexes 必须是逗号分隔的整数列表，收到: {value}')


def main():
    parser = argparse.ArgumentParser(description='Segway 箱门控制')
    parser.add_argument('action', choices=['open', 'close', 'info', 'put-verify', 'take-verify'],
                        help='操作类型')
    parser.add_argument('--robot-id', help='机器人 ID')
    parser.add_argument('--robot-name', help='机器人名称（支持模糊匹配，自动解析为 robot-id）')
    parser.add_argument('--box-indexes', help='箱门编号列表（逗号分隔的整数，如 1,2,3）')
    parser.add_argument('--task-id', help='运单 ID')
    parser.add_argument('--dry-run', action='store_true', help='仅验证参数并生成确认 token，不真正执行')
    parser.add_argument('--confirm', help='确认 token（由 --dry-run 生成）')
    args = parser.parse_args()

    # info 是读操作，不需要确认
    if args.action == 'info':
        robot_id = segway_resolve.resolve_robot_id(args)
        if not robot_id:
            segway_output.print_param_error(
                '机器人 ID 或名称 (--robot-id 或 --robot-name)',
                'box_control.py info --robot-name "小蓝"')
            sys.exit(1)
        result = segway_auth.call_api('GET', f'/api/transport/robot/{robot_id}/box/size')
        segway_output.handle_result(result, '已查询箱门部署信息，请将结果告知用户。')
        return

    # 写操作：构造 body 和 API 路径
    robot_id = segway_resolve.resolve_robot_id(args)

    if args.action in ('open', 'close'):
        missing = []
        if not robot_id:
            missing.append('机器人 ID 或名称 (--robot-id 或 --robot-name)')
        if not args.box_indexes:
            missing.append('箱门编号 (--box-indexes，如 1,2)')
        if missing:
            segway_output.print_param_error(
                '、'.join(missing),
                f'box_control.py {args.action} --robot-name "小蓝" --box-indexes 1,2')
            sys.exit(1)
        indexes = parse_box_indexes(args.box_indexes)
        body = {'robotId': robot_id, 'boxIndexes': indexes}
        api_path = f'/api/transport/robot/boxs/{args.action}'

    elif args.action in ('put-verify', 'take-verify'):
        missing = []
        if not robot_id:
            missing.append('机器人 ID 或名称 (--robot-id 或 --robot-name)')
        if not args.task_id:
            missing.append('运单 ID (--task-id)')
        if missing:
            segway_output.print_param_error(
                '、'.join(missing),
                f'box_control.py {args.action} --robot-name "小蓝" --task-id xxx')
            sys.exit(1)
        body = {'robotId': robot_id, 'taskId': args.task_id}
        verify_type = 'put' if args.action == 'put-verify' else 'take'
        api_path = f'/api/transport/task/{verify_type}/verify'

    # dry-run / confirm 门控
    action_name = f'box_control.{args.action}'

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

    if not args.confirm:
        print(f'错误: 写操作 {args.action} 需要先用 --dry-run 生成确认 token。')
        print(f'\n[TASK_FAILED] 安全机制：写操作必须经过 dry-run + confirm 两步确认。请先加 --dry-run 参数运行。')
        sys.exit(1)

    valid, err = segway_confirm.verify_token(args.confirm, action_name, body)
    if not valid:
        print(f'错误: confirm token 验证失败 - {err}')
        print(f'\n[TASK_FAILED] token 验证失败: {err}。请重新用 --dry-run 生成新的 token。')
        sys.exit(1)

    result = segway_auth.call_api('POST', api_path, body=body)

    SUMMARIES = {
        'open': '箱门已打开，请告知用户。任务已完成，无需再做其他操作。',
        'close': '箱门已关闭，请告知用户。任务已完成，无需再做其他操作。',
        'put-verify': '取物确认成功，请告知用户。任务已完成，无需再做其他操作。',
        'take-verify': '取件确认成功，请告知用户。任务已完成，无需再做其他操作。',
    }
    segway_output.handle_result(result, SUMMARIES.get(args.action))


if __name__ == '__main__':
    main()
