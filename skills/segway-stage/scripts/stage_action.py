#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 任务起草脚本
agent 调用此脚本"起草"写操作任务，任务进入 pending 状态等待人工审批。
审批通过后由 webhook server 的 /approve 端点直接执行，大模型不参与。
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 任务存储文件
DATA_DIR = Path(__file__).parent.parent / 'data'
TASKS_FILE = DATA_DIR / 'pending_tasks.json'

# 支持的操作类型 → API 映射
ACTION_MAP = {
    'task.create.guidance': ('POST', '/api/transport/task/create'),
    'task.create.take-deliver': ('POST', '/api/transport/task/create'),
    'task.cancel': ('POST', '/api/transport/task/cancel'),
    'task.priority': ('POST', '/api/transport/task/priority'),
    'task.redeliver': ('POST', '/api/transport/delay/redeliver'),
    'box.open': ('POST', '/api/transport/robot/boxs/open'),
    'box.close': ('POST', '/api/transport/robot/boxs/close'),
    'box.put-verify': ('POST', '/api/transport/task/put/verify'),
    'box.take-verify': ('POST', '/api/transport/task/take/verify'),
}

# 操作中文名
ACTION_NAMES = {
    'task.create.guidance': '创建引领运单',
    'task.create.take-deliver': '创建取送运单',
    'task.cancel': '取消运单',
    'task.priority': '修改运单优先级',
    'task.redeliver': '重新配送',
    'box.open': '打开箱门',
    'box.close': '关闭箱门',
    'box.put-verify': '取物确认',
    'box.take-verify': '取件确认',
}


def load_tasks():
    """加载任务列表"""
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return []


def save_tasks(tasks):
    """保存任务列表"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


def get_approve_url(task_id, port=18800):
    """生成审批 URL"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
    return f'http://{ip}:{port}/approve/{task_id}'


def get_reject_url(task_id, port=18800):
    """生成拒绝 URL"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
    return f'http://{ip}:{port}/reject/{task_id}'


def cmd_stage(args):
    """起草任务"""
    action = args.action_type
    if action not in ACTION_MAP:
        print(f'错误: 不支持的操作类型 "{action}"')
        print(f'支持的类型: {", ".join(ACTION_MAP.keys())}')
        print(f'\n[TASK_FAILED] 不支持的操作类型。')
        sys.exit(1)

    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f'错误: params 不是有效的 JSON: {e}')
        print(f'\n[TASK_FAILED] 参数格式错误，需要有效的 JSON。')
        sys.exit(1)

    # 生成任务
    task_id = f'task_{int(time.time())}_{uuid.uuid4().hex[:6]}'
    method, api_path = ACTION_MAP[action]
    action_name = ACTION_NAMES.get(action, action)

    task = {
        'task_id': task_id,
        'action': action,
        'action_name': action_name,
        'method': method,
        'api_path': api_path,
        'params': params,
        'status': 'pending',
        'created_at': time.time(),
        'created_at_str': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    # 保存
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)

    # 输出审批信息
    approve_url = get_approve_url(task_id)
    reject_url = get_reject_url(task_id)

    print(f'任务已起草，等待人工审批。')
    print(f'')
    print(f'任务 ID: {task_id}')
    print(f'操作: {action_name}')
    print(f'参数:')
    print(json.dumps(params, ensure_ascii=False, indent=2))
    print(f'')
    print(f'审批方式:')
    print(f'  批准: {approve_url}')
    print(f'  拒绝: {reject_url}')
    print(f'  或在企微回复: approve:{task_id}')
    print(f'')
    print(f'[ACTION_STAGED] 任务已起草并等待审批。请将以上信息告知用户，用户批准后将自动执行。不要再调用任何 skill。')


def cmd_list(args):
    """列出任务"""
    tasks = load_tasks()
    status_filter = args.status

    if status_filter:
        tasks = [t for t in tasks if t.get('status') == status_filter]

    if not tasks:
        print(f'没有{"状态为 " + status_filter + " 的" if status_filter else ""}任务')
        return

    print(f'共 {len(tasks)} 个任务:\n')
    for t in tasks[-20:]:  # 最近 20 个
        status_icon = {'pending': '⏳', 'approved': '✅', 'rejected': '❌', 'executed': '🟢'}.get(t['status'], '?')
        print(f'  {status_icon} [{t["task_id"]}] {t["action_name"]} - {t["status"]} ({t.get("created_at_str", "")})')


def main():
    parser = argparse.ArgumentParser(description='Segway 任务起草')
    parser.add_argument('command', choices=['stage', 'list'], help='命令')
    parser.add_argument('--action', dest='action_type', help='操作类型')
    parser.add_argument('--params', help='操作参数（JSON 格式）')
    parser.add_argument('--status', help='筛选状态（list 命令用）')
    args = parser.parse_args()

    if args.command == 'stage':
        if not args.action_type or not args.params:
            print('错误: stage 命令需要 --action 和 --params 参数')
            print(f'\n[TASK_FAILED] 缺少参数。请提供 --action 操作类型和 --params JSON参数。')
            sys.exit(1)
        cmd_stage(args)
    elif args.command == 'list':
        cmd_list(args)


if __name__ == '__main__':
    main()
