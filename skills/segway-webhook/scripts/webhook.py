#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway Webhook 事件管理脚本
接收 Segway 配送机器人的回调事件推送，提供事件查询和管理功能。

操作:
  start        - 启动 Webhook HTTP 服务器（后台守护进程）
  stop         - 停止 Webhook 服务器
  status       - 查看服务器状态和事件统计
  events       - 查询回调事件（支持过滤）
  clear        - 清理事件日志
  callback-url - 输出回调 URL
"""

import argparse
import datetime
import fcntl
import json
import os
import signal
import socket
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# 默认配置
DEFAULT_PORT = 18800
DEFAULT_HOST = '0.0.0.0'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DEFAULT_LOG_FILE = os.path.join(DATA_DIR, 'events.jsonl')
PID_FILE = os.path.join(DATA_DIR, 'webhook.pid')


def get_config():
    """读取配置，环境变量优先"""
    port = int(os.environ.get('SEGWAY_WEBHOOK_PORT', DEFAULT_PORT))
    host = os.environ.get('SEGWAY_WEBHOOK_HOST', DEFAULT_HOST)
    log_file = os.environ.get('SEGWAY_WEBHOOK_LOG', DEFAULT_LOG_FILE)
    return host, port, log_file


def ensure_data_dir():
    """确保 data 目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def append_event(log_file, event):
    """追加事件到 JSONL 日志文件（文件锁保证并发安全）"""
    ensure_data_dir()
    with open(log_file, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def read_events(log_file):
    """读取所有事件"""
    if not os.path.exists(log_file):
        return []
    events = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


class WebhookHandler(BaseHTTPRequestHandler):
    """处理 Segway 回调请求的 HTTP Handler"""

    log_file = DEFAULT_LOG_FILE

    def do_POST(self):
        """接收回调事件"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''

        # 解析请求体
        try:
            payload = json.loads(body.decode('utf-8')) if body else {}
        except json.JSONDecodeError:
            payload = {'raw': body.decode('utf-8', errors='replace')}

        # 构造事件记录
        event = {
            'timestamp': datetime.datetime.now().isoformat(),
            'epoch': time.time(),
            'path': self.path,
            'method': 'POST',
            'headers': dict(self.headers),
            'payload': payload,
        }

        # 提取关键字段便于查询
        if isinstance(payload, dict):
            for key in ('taskId', 'task_id', 'robotId', 'robot_id',
                        'type', 'eventType', 'event_type', 'status',
                        'taskStatus', 'task_status'):
                if key in payload:
                    event[key] = payload[key]

        # 写入日志
        append_event(self.log_file, event)

        # 返回 200
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'code': 200, 'message': 'ok'}).encode())

    def do_GET(self):
        """健康检查端点"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'running',
                'timestamp': datetime.datetime.now().isoformat()
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """静默日志，避免污染 stdout"""
        pass


def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def is_server_running():
    """检查服务器是否在运行"""
    if not os.path.exists(PID_FILE):
        return False, None
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        # 检查进程是否存在
        os.kill(pid, 0)
        return True, pid
    except (ValueError, ProcessLookupError, OSError):
        # PID 文件存在但进程不在，清理
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return False, None


def cmd_start(args):
    """启动 Webhook 服务器（后台守护进程）"""
    host, port, log_file = get_config()
    if args.port:
        port = args.port
    if args.host:
        host = args.host

    running, pid = is_server_running()
    if running:
        print(f'Webhook 服务器已在运行 (PID: {pid})')
        return

    ensure_data_dir()

    # Fork 为守护进程
    child_pid = os.fork()
    if child_pid > 0:
        # 父进程：等待子进程启动
        time.sleep(0.5)
        running, pid = is_server_running()
        if running:
            local_ip = get_local_ip()
            print(f'Webhook 服务器已启动')
            print(f'  PID: {pid}')
            print(f'  监听: {host}:{port}')
            print(f'  回调 URL: http://{local_ip}:{port}/callback')
            print(f'  健康检查: http://{local_ip}:{port}/health')
            print(f'  事件日志: {log_file}')
        else:
            print('错误: Webhook 服务器启动失败')
            sys.exit(1)
        return

    # 子进程：成为守护进程
    os.setsid()
    # 二次 fork
    child_pid2 = os.fork()
    if child_pid2 > 0:
        os._exit(0)

    # 写入 PID 文件
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # 重定向标准流
    sys.stdin.close()
    log_path = os.path.join(DATA_DIR, 'server.log')
    sys.stdout = open(log_path, 'a')
    sys.stderr = sys.stdout

    # 设置 Handler 的日志文件
    WebhookHandler.log_file = log_file

    # 启动服务器
    try:
        server = HTTPServer((host, port), WebhookHandler)
        print(f'[{datetime.datetime.now().isoformat()}] Webhook server started on {host}:{port}')
        sys.stdout.flush()
        server.serve_forever()
    except Exception as e:
        print(f'[{datetime.datetime.now().isoformat()}] Server error: {e}')
        sys.stdout.flush()
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


def cmd_stop(args):
    """停止 Webhook 服务器"""
    running, pid = is_server_running()
    if not running:
        print('Webhook 服务器未在运行')
        return

    try:
        os.kill(pid, signal.SIGTERM)
        # 等待进程退出
        for _ in range(10):
            time.sleep(0.3)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        print(f'Webhook 服务器已停止 (PID: {pid})')
    except OSError as e:
        print(f'停止服务器失败: {e}')

    # 清理 PID 文件
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def cmd_status(args):
    """查看服务器状态"""
    _, port, log_file = get_config()
    running, pid = is_server_running()

    if running:
        local_ip = get_local_ip()
        print(f'状态: 运行中')
        print(f'PID: {pid}')
        print(f'回调 URL: http://{local_ip}:{port}/callback')
    else:
        print(f'状态: 未运行')

    # 事件统计
    events = read_events(log_file)
    if events:
        print(f'\n事件统计:')
        print(f'  总事件数: {len(events)}')
        # 按类型统计
        type_counts = {}
        for e in events:
            etype = e.get('type', e.get('eventType', e.get('event_type', '未知')))
            type_counts[etype] = type_counts.get(etype, 0) + 1
        if type_counts:
            print(f'  按类型:')
            for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
                print(f'    {t}: {c}')
        # 最近事件时间
        last = events[-1]
        print(f'  最近事件: {last.get("timestamp", "未知")}')
    else:
        print(f'\n暂无事件记录')


def cmd_events(args):
    """查询回调事件"""
    _, _, log_file = get_config()
    events = read_events(log_file)

    if not events:
        print('暂无事件记录')
        return

    # 按 task_id 过滤
    if args.task_id:
        events = [e for e in events if e.get('taskId') == args.task_id
                  or e.get('task_id') == args.task_id
                  or (isinstance(e.get('payload'), dict)
                      and (e['payload'].get('taskId') == args.task_id
                           or e['payload'].get('task_id') == args.task_id))]

    # 按事件类型过滤
    if args.type:
        events = [e for e in events
                  if e.get('type') == args.type
                  or e.get('eventType') == args.type
                  or e.get('event_type') == args.type
                  or (isinstance(e.get('payload'), dict)
                      and (e['payload'].get('type') == args.type
                           or e['payload'].get('eventType') == args.type))]

    # 按时间过滤
    if args.since:
        try:
            if len(args.since) == 10:  # YYYY-MM-DD
                since_dt = datetime.datetime.fromisoformat(args.since)
            else:
                since_dt = datetime.datetime.fromisoformat(args.since)
            since_epoch = since_dt.timestamp()
            events = [e for e in events if e.get('epoch', 0) >= since_epoch]
        except ValueError:
            print(f'警告: 无法解析时间 "{args.since}"，忽略时间过滤')

    # 限制数量（取最近的）
    limit = args.limit or 20
    if len(events) > limit:
        events = events[-limit:]

    if not events:
        print('没有匹配的事件')
        return

    print(f'共 {len(events)} 条事件:\n')
    for e in events:
        ts = e.get('timestamp', '未知时间')
        task_id = e.get('taskId', e.get('task_id', ''))
        etype = e.get('type', e.get('eventType', e.get('event_type', '')))
        status = e.get('status', e.get('taskStatus', e.get('task_status', '')))
        path = e.get('path', '')

        # 摘要行
        parts = [ts]
        if etype:
            parts.append(f'类型={etype}')
        if task_id:
            parts.append(f'运单={task_id}')
        if status:
            parts.append(f'状态={status}')
        print(f'  [{" | ".join(parts)}]')

        # 详细 payload（缩进显示）
        payload = e.get('payload', {})
        if payload and isinstance(payload, dict):
            compact = json.dumps(payload, ensure_ascii=False)
            if len(compact) > 200:
                compact = compact[:200] + '...'
            print(f'    {compact}')
        print()


def cmd_clear(args):
    """清理事件日志"""
    _, _, log_file = get_config()

    if args.all:
        if os.path.exists(log_file):
            os.remove(log_file)
            print('已清理所有事件日志')
        else:
            print('事件日志文件不存在')
        return

    if args.before:
        try:
            before_dt = datetime.datetime.fromisoformat(args.before)
            before_epoch = before_dt.timestamp()
        except ValueError:
            print(f'错误: 无法解析时间 "{args.before}"')
            sys.exit(1)

        events = read_events(log_file)
        kept = [e for e in events if e.get('epoch', 0) >= before_epoch]
        removed = len(events) - len(kept)

        # 重写文件
        ensure_data_dir()
        with open(log_file, 'w') as f:
            for e in kept:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')

        print(f'已清理 {removed} 条事件，保留 {len(kept)} 条')
    else:
        print('请指定 --before <时间> 或 --all')


def cmd_callback_url(args):
    """输出回调 URL"""
    _, port, _ = get_config()
    if args.port:
        port = args.port
    local_ip = get_local_ip()
    print(f'http://{local_ip}:{port}/callback')


def main():
    parser = argparse.ArgumentParser(description='Segway Webhook 事件管理')
    parser.add_argument('action',
                        choices=['start', 'stop', 'status', 'events', 'clear', 'callback-url'],
                        help='操作类型')
    parser.add_argument('--port', type=int, help=f'监听端口（默认 {DEFAULT_PORT}）')
    parser.add_argument('--host', help=f'监听地址（默认 {DEFAULT_HOST}）')
    # events 参数
    parser.add_argument('--task-id', help='按运单 ID 过滤')
    parser.add_argument('--type', help='按事件类型过滤')
    parser.add_argument('--limit', type=int, help='返回最近 N 条事件（默认 20）')
    parser.add_argument('--since', help='只返回指定时间之后的事件')
    # clear 参数
    parser.add_argument('--before', help='清理指定时间之前的事件')
    parser.add_argument('--all', action='store_true', help='清理所有事件')

    args = parser.parse_args()

    if args.action == 'start':
        cmd_start(args)
    elif args.action == 'stop':
        cmd_stop(args)
    elif args.action == 'status':
        cmd_status(args)
    elif args.action == 'events':
        cmd_events(args)
    elif args.action == 'clear':
        cmd_clear(args)
    elif args.action == 'callback-url':
        cmd_callback_url(args)


if __name__ == '__main__':
    main()
