#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway Webhook 回调服务
接收 Segway API 的运单状态变更推送，记录事件日志。
支持后台运行、事件查询、服务状态检查。
"""

import argparse
import json
import os
import signal
import sys
import time
import importlib.util
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 数据目录
DATA_DIR = Path(__file__).parent.parent / 'data'
EVENTS_FILE = DATA_DIR / 'events.jsonl'
PID_FILE = DATA_DIR / 'webhook.pid'
LOG_FILE = DATA_DIR / 'webhook.log'

# Segway 运单状态码映射
TASK_STATUS_MAP = {
    0: '待分配',
    1: '已分配/待执行',
    2: '执行中',
    3: '已完成',
    4: '已取消',
    5: '异常',
    10: '待取件',
    11: '取件中',
    12: '已取件/配送中',
    13: '待送件',
    14: '送件中',
    15: '已送达',
}


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_event(event):
    """追加事件到 JSONL 日志"""
    ensure_data_dir()
    event['received_at'] = datetime.now().isoformat()
    with open(EVENTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def read_events(task_id=None, limit=20):
    """读取事件日志"""
    if not EVENTS_FILE.exists():
        return []
    events = []
    with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if task_id and ev.get('taskId') != task_id:
                    continue
                events.append(ev)
            except json.JSONDecodeError:
                continue
    # 返回最近的 N 条
    return events[-limit:]


# === 任务审批执行逻辑（大模型不参与）===

# stage skill 的任务文件路径
STAGE_TASKS_FILE = Path(__file__).parent.parent.parent / 'segway-stage' / 'data' / 'pending_tasks.json'

# 导入认证模块路径
import importlib.util
_auth_path = Path(__file__).parent.parent.parent / 'segway_auth.py'


def _load_segway_auth():
    """动态加载 segway_auth 模块"""
    spec = importlib.util.spec_from_file_location('segway_auth', _auth_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_staged_tasks():
    """加载 staged 任务列表"""
    if not STAGE_TASKS_FILE.exists():
        return []
    try:
        return json.loads(STAGE_TASKS_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return []


def _save_staged_tasks(tasks):
    """保存 staged 任务列表"""
    STAGE_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAGE_TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


def execute_staged_task(task_id):
    """
    批准并执行一个 staged 任务。
    直接调用 Segway API，大模型完全不参与。
    """
    tasks = _load_staged_tasks()
    task = None
    for t in tasks:
        if t['task_id'] == task_id:
            task = t
            break

    if not task:
        return {'code': 404, 'message': f'任务 {task_id} 不存在'}

    if task['status'] != 'pending':
        return {'code': 409, 'message': f'任务 {task_id} 状态为 {task["status"]}，无法执行'}

    # 执行 API 调用
    try:
        auth = _load_segway_auth()
        method = task['method']
        api_path = task['api_path']
        params = task['params']

        result = auth.call_api(method, api_path, body=params)

        # 更新任务状态
        task['status'] = 'executed'
        task['executed_at'] = time.time()
        task['executed_at_str'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task['api_result'] = result
        _save_staged_tasks(tasks)

        # 记录到事件日志
        append_event({
            'taskId': task_id,
            'taskStatus': 'approved_and_executed',
            'statusText': f'审批通过并执行: {task["action_name"]}',
            'api_result': result,
        })

        return {
            'code': 200,
            'message': f'任务 {task_id} 已批准并执行',
            'action': task['action_name'],
            'api_result': result,
        }
    except Exception as e:
        task['status'] = 'error'
        task['error'] = str(e)
        _save_staged_tasks(tasks)
        return {'code': 500, 'message': f'执行失败: {str(e)}'}


def reject_staged_task(task_id):
    """拒绝一个 staged 任务"""
    tasks = _load_staged_tasks()
    task = None
    for t in tasks:
        if t['task_id'] == task_id:
            task = t
            break

    if not task:
        return {'code': 404, 'message': f'任务 {task_id} 不存在'}

    if task['status'] != 'pending':
        return {'code': 409, 'message': f'任务 {task_id} 状态为 {task["status"]}，无法拒绝'}

    task['status'] = 'rejected'
    task['rejected_at'] = time.time()
    _save_staged_tasks(tasks)

    return {'code': 200, 'message': f'任务 {task_id} 已拒绝', 'action': task['action_name']}


def list_pending_tasks():
    """列出所有 pending 任务"""
    tasks = _load_staged_tasks()
    pending = [t for t in tasks if t['status'] == 'pending']
    return {
        'code': 200,
        'count': len(pending),
        'tasks': [{'task_id': t['task_id'], 'action': t['action_name'],
                   'params': t['params'], 'created_at': t.get('created_at_str', '')}
                  for t in pending],
    }


class WebhookHandler(BaseHTTPRequestHandler):
    """处理 Segway 回调请求"""

    def do_POST(self):
        """接收 POST 回调"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"code": 400, "message": "Invalid JSON"}')
            return

        # 提取关键字段
        task_id = data.get('taskId', data.get('task_id', ''))
        task_status = data.get('taskStatus', data.get('status', ''))
        status_text = TASK_STATUS_MAP.get(task_status, f'未知状态({task_status})')

        event = {
            'taskId': task_id,
            'taskStatus': task_status,
            'statusText': status_text,
            'path': self.path,
            'raw': data,
        }
        append_event(event)

        # 写日志
        log_msg = f'[{datetime.now().isoformat()}] 运单 {task_id} 状态变更: {status_text}\n'
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg)

        # 返回成功
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'code': 200, 'message': 'ok'}).encode())

    def do_GET(self):
        """健康检查 + 审批端点"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'running',
                'events_count': len(read_events(limit=999999)),
                'uptime': time.time() - SERVER_START_TIME if 'SERVER_START_TIME' in globals() else 0,
            }).encode())
        elif self.path.startswith('/approve/'):
            task_id = self.path.split('/approve/', 1)[1]
            result = execute_staged_task(task_id)
            self._send_json(result)
        elif self.path.startswith('/reject/'):
            task_id = self.path.split('/reject/', 1)[1]
            result = reject_staged_task(task_id)
            self._send_json(result)
        elif self.path == '/pending':
            result = list_pending_tasks()
            self._send_json(result)
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        """发送 JSON 响应"""
        code = data.get('code', 200)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        """静默日志，避免刷屏"""
        pass


SERVER_START_TIME = 0


def cmd_start(args):
    """启动 webhook 服务（后台模式）"""
    ensure_data_dir()
    host = args.host
    port = args.port

    # 检查是否已在运行
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)  # 检查进程是否存在
            print(f'Webhook 服务已在运行 (PID: {pid}, 端口: {port})')
            return
        except (ProcessLookupError, ValueError):
            PID_FILE.unlink(missing_ok=True)

    # Fork 到后台
    pid = os.fork()
    if pid > 0:
        # 父进程
        print(f'Webhook 服务已启动 (PID: {pid}, 监听: {host}:{port})')
        print(f'回调 URL: http://<你的IP>:{port}/callback')
        print(f'事件日志: {EVENTS_FILE}')
        return

    # 子进程：脱离终端
    os.setsid()
    # 重定向标准输出
    sys.stdout = open(LOG_FILE, 'a')
    sys.stderr = sys.stdout

    # 写 PID 文件
    PID_FILE.write_text(str(os.getpid()))

    global SERVER_START_TIME
    SERVER_START_TIME = time.time()

    def cleanup(signum, frame):
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    server = HTTPServer((host, port), WebhookHandler)
    print(f'[{datetime.now().isoformat()}] Webhook 服务启动: {host}:{port}')
    server.serve_forever()


def cmd_stop(args):
    """停止 webhook 服务"""
    if not PID_FILE.exists():
        print('Webhook 服务未在运行')
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f'已停止 Webhook 服务 (PID: {pid})')
    except ProcessLookupError:
        print('Webhook 服务进程已不存在')
    except ValueError:
        print('PID 文件格式错误')

    PID_FILE.unlink(missing_ok=True)


def cmd_status(args):
    """查看服务状态"""
    if not PID_FILE.exists():
        print('Webhook 服务: 未运行')
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        print(f'Webhook 服务: 运行中 (PID: {pid})')

        # 统计事件数
        events = read_events(limit=999999)
        print(f'已接收事件: {len(events)} 条')

        if events:
            last = events[-1]
            print(f'最近事件: 运单 {last.get("taskId", "?")} - {last.get("statusText", "?")} ({last.get("received_at", "")})')
    except ProcessLookupError:
        print('Webhook 服务: 已停止（PID 文件残留，已清理）')
        PID_FILE.unlink(missing_ok=True)


def cmd_events(args):
    """查看事件历史"""
    events = read_events(task_id=args.task_id, limit=args.limit)
    if not events:
        if args.task_id:
            print(f'运单 {args.task_id} 没有回调事件记录')
        else:
            print('暂无回调事件记录')
        return

    print(f'共 {len(events)} 条事件:\n')
    for ev in events:
        task_id = ev.get('taskId', '?')
        status = ev.get('statusText', '?')
        ts = ev.get('received_at', '?')
        print(f'  [{ts}] 运单 {task_id}: {status}')

    # 如果查询特定运单，输出完整最新事件
    if args.task_id and events:
        print(f'\n最新事件详情:')
        print(json.dumps(events[-1].get('raw', {}), ensure_ascii=False, indent=2))


def cmd_callback_url(args):
    """获取回调 URL"""
    port = args.port
    # 尝试获取本机 IP
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'

    print(f'Webhook 回调 URL:')
    print(f'  本地: http://127.0.0.1:{port}/callback')
    print(f'  局域网: http://{ip}:{port}/callback')
    print(f'\n在创建运单时使用 --callback-url 参数传入此 URL')


def main():
    parser = argparse.ArgumentParser(description='Segway Webhook 回调服务')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'events', 'callback-url'],
                        help='操作类型')
    parser.add_argument('--port', type=int, default=18800, help='监听端口 (默认 18800)')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址 (默认 0.0.0.0)')
    parser.add_argument('--task-id', help='运单 ID（events 操作用）')
    parser.add_argument('--limit', type=int, default=20, help='事件数量限制 (默认 20)')
    args = parser.parse_args()

    if args.action == 'start':
        cmd_start(args)
    elif args.action == 'stop':
        cmd_stop(args)
    elif args.action == 'status':
        cmd_status(args)
    elif args.action == 'events':
        cmd_events(args)
    elif args.action == 'callback-url':
        cmd_callback_url(args)


if __name__ == '__main__':
    main()
