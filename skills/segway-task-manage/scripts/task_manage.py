#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 运单管理脚本
支持操作: cancel, priority, status, history, redeliver
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


def main():
    parser = argparse.ArgumentParser(description='Segway 运单管理')
    parser.add_argument('action', choices=['cancel', 'priority', 'status', 'history', 'redeliver'],
                        help='操作类型')
    parser.add_argument('--task-id', help='运单 ID')
    parser.add_argument('--priority-level', type=int, help='优先级 (40-60)')
    parser.add_argument('--start-time', help='开始时间（毫秒时间戳）')
    parser.add_argument('--end-time', help='结束时间（毫秒时间戳）')
    parser.add_argument('--robot-id', help='机器人 ID')
    parser.add_argument('--robot-name', help='机器人名称（支持模糊匹配，自动解析为 robot-id）')
    parser.add_argument('--task-ids', help='运单 ID 列表（逗号分隔）')
    parser.add_argument('--dry-run', action='store_true', help='仅验证参数并生成确认 token，不真正执行')
    parser.add_argument('--confirm', help='确认 token（由 --dry-run 生成）')
    args = parser.parse_args()

    WRITE_ACTIONS = {'cancel', 'priority', 'redeliver'}

    if args.action == 'cancel':
        if not args.task_id:
            segway_output.print_param_error(
                '运单 ID (--task-id)',
                'task_manage.py cancel --task-id xxx')
            sys.exit(1)
        body = {'taskId': args.task_id}
        api_method, api_path = 'POST', '/api/transport/task/cancel'

    elif args.action == 'priority':
        missing = []
        if not args.task_id:
            missing.append('运单 ID (--task-id)')
        if args.priority_level is None:
            missing.append('优先级数值 40-60 (--priority-level)')
        if missing:
            segway_output.print_param_error(
                '、'.join(missing),
                'task_manage.py priority --task-id xxx --priority-level 50')
            sys.exit(1)
        body = {'taskId': args.task_id, 'priorityLevel': args.priority_level}
        api_method, api_path = 'POST', '/api/transport/task/priority'

    elif args.action == 'status':
        if not args.task_id:
            segway_output.print_param_error(
                '运单 ID (--task-id)',
                'task_manage.py status --task-id xxx')
            sys.exit(1)
        result = segway_auth.call_api('GET', f'/api/transport/task/{args.task_id}/status')
        segway_output.handle_result(result, '已查询运单状态，请将结果告知用户。')
        return

    elif args.action == 'history':
        missing = []
        if not args.start_time:
            missing.append('开始时间毫秒时间戳 (--start-time)')
        if not args.end_time:
            missing.append('结束时间毫秒时间戳 (--end-time)')
        if missing:
            segway_output.print_param_error(
                '、'.join(missing),
                'task_manage.py history --start-time 1711929600000 --end-time 1712016000000')
            sys.exit(1)
        result = segway_auth.call_api('GET', '/api/transport/task/history',
                                      query_params={'startTime': args.start_time,
                                                    'endTime': args.end_time})
        segway_output.handle_result(result, '已查询历史运单，请将结果告知用户。')
        return

    elif args.action == 'redeliver':
        robot_id = segway_resolve.resolve_robot_id(args)
        missing = []
        if not robot_id:
            missing.append('机器人 ID 或名称 (--robot-id 或 --robot-name)')
        if not args.task_ids:
            missing.append('运单 ID 列表 (--task-ids，逗号分隔)')
        if missing:
            segway_output.print_param_error(
                '、'.join(missing),
                'task_manage.py redeliver --robot-name "小蓝" --task-ids id1,id2')
            sys.exit(1)
        task_id_list = [tid.strip() for tid in args.task_ids.split(',')]
        body = {'robotId': robot_id, 'taskIds': task_id_list}
        api_method, api_path = 'POST', '/api/transport/delay/redeliver'

    # 写操作的 dry-run / confirm 门控
    action_name = f'task_manage.{args.action}'

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

    result = segway_auth.call_api(api_method, api_path, body=body)

    SUMMARIES = {
        'cancel': '运单已取消，请告知用户。任务已完成，无需再做其他操作。',
        'priority': '运单优先级已修改，请告知用户。任务已完成，无需再做其他操作。',
        'redeliver': '滞留件重新配送已发起，请告知用户。任务已完成，无需再做其他操作。',
    }
    segway_output.handle_result(result, SUMMARIES.get(args.action))


if __name__ == '__main__':
    main()
