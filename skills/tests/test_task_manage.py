#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_manage.py 单元测试
Validates: Requirements 5.7, 8.4

测试覆盖:
- 各操作的参数解析 (cancel, priority, status, history, redeliver)
- 缺少必要参数时的错误输出
- API 返回错误码时的输出格式
- API 返回成功时的输出格式
"""

import io
import json
import os
import sys
from unittest.mock import patch

import pytest

# 将 skills 目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# 将 task_manage 脚本目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'segway-task-manage', 'scripts'))

import task_manage


# ── 辅助函数 ──────────────────────────────────────────────

def run_main(args, mock_return=None):
    """
    用给定的 sys.argv 运行 task_manage.main()，mock 掉 segway_auth.call_api。
    返回 (captured_stdout, call_api_call_args_list, exit_code)。
    """
    captured = io.StringIO()
    with patch('task_manage.segway_auth.call_api', return_value=mock_return) as mock_api, \
         patch('sys.argv', ['task_manage.py'] + args), \
         patch('sys.stdout', captured):
        try:
            task_manage.main()
        except SystemExit as e:
            return captured.getvalue(), mock_api.call_args_list, e.code
        return captured.getvalue(), mock_api.call_args_list, None


# ── cancel 操作测试 ───────────────────────────────────────

class TestCancelAction:
    """测试 cancel 操作"""

    def test_cancel_requires_task_id(self):
        """cancel 操作缺少 --task-id 时应报错退出"""
        output, _, exit_code = run_main(['cancel'])
        assert exit_code == 1
        assert '--task-id' in output

    def test_cancel_calls_correct_api(self):
        """cancel 操作应调用 POST /api/transport/task/cancel"""
        api_response = {'code': 200, 'data': None}
        output, calls, exit_code = run_main(['cancel', '--task-id', 'T001'], api_response)
        assert exit_code is None
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args[0] == 'POST'
        assert args[1] == '/api/transport/task/cancel'
        assert kwargs.get('body') == {'taskId': 'T001'}

    def test_cancel_success_output(self):
        """cancel 成功时应输出 data 字段"""
        api_response = {'code': 200, 'data': None}
        output, _, _ = run_main(['cancel', '--task-id', 'T001'], api_response)
        assert output.strip() == 'null'


# ── priority 操作测试 ─────────────────────────────────────

class TestPriorityAction:
    """测试 priority 操作"""

    def test_priority_requires_task_id(self):
        """priority 操作缺少 --task-id 时应报错退出"""
        output, _, exit_code = run_main(['priority', '--priority-level', '50'])
        assert exit_code == 1
        assert '--task-id' in output

    def test_priority_requires_priority_level(self):
        """priority 操作缺少 --priority-level 时应报错退出"""
        output, _, exit_code = run_main(['priority', '--task-id', 'T001'])
        assert exit_code == 1
        assert '--priority-level' in output

    def test_priority_calls_correct_api(self):
        """priority 操作应调用 POST /api/transport/task/priority"""
        api_response = {'code': 200, 'data': None}
        output, calls, _ = run_main(['priority', '--task-id', 'T001', '--priority-level', '50'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'POST'
        assert args[1] == '/api/transport/task/priority'
        assert kwargs.get('body') == {'taskId': 'T001', 'priorityLevel': 50}


# ── status 操作测试 ───────────────────────────────────────

class TestStatusAction:
    """测试 status 操作"""

    def test_status_requires_task_id(self):
        """status 操作缺少 --task-id 时应报错退出"""
        output, _, exit_code = run_main(['status'])
        assert exit_code == 1
        assert '--task-id' in output

    def test_status_calls_correct_api(self):
        """status 操作应调用 GET /api/transport/task/{taskId}/status"""
        api_response = {'code': 200, 'data': {'status': 'Running'}}
        output, calls, _ = run_main(['status', '--task-id', 'T001'], api_response)
        args, kwargs = calls[0]
        assert args == ('GET', '/api/transport/task/T001/status')

    def test_status_success_output(self):
        """status 成功时应输出格式化的 JSON data"""
        data = {'status': 'Running', 'taskId': 'T001'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['status', '--task-id', 'T001'], api_response)
        parsed = json.loads(output)
        assert parsed == data


# ── history 操作测试 ──────────────────────────────────────

class TestHistoryAction:
    """测试 history 操作"""

    def test_history_requires_both_times(self):
        """history 操作缺少时间参数时应报错退出"""
        output, _, exit_code = run_main(['history'])
        assert exit_code == 1
        assert '--start-time' in output and '--end-time' in output

    def test_history_requires_end_time(self):
        """history 操作仅有 --start-time 缺少 --end-time 时应报错退出"""
        output, _, exit_code = run_main(['history', '--start-time', '1700000000000'])
        assert exit_code == 1
        assert '--end-time' in output

    def test_history_requires_start_time(self):
        """history 操作仅有 --end-time 缺少 --start-time 时应报错退出"""
        output, _, exit_code = run_main(['history', '--end-time', '1700100000000'])
        assert exit_code == 1
        assert '--start-time' in output

    def test_history_calls_correct_api(self):
        """history 操作应调用 GET /api/transport/task/history 并传递时间参数"""
        api_response = {'code': 200, 'data': []}
        output, calls, _ = run_main(
            ['history', '--start-time', '1700000000000', '--end-time', '1700100000000'],
            api_response)
        args, kwargs = calls[0]
        assert args[0] == 'GET'
        assert args[1] == '/api/transport/task/history'
        assert kwargs.get('query_params') == {'startTime': '1700000000000', 'endTime': '1700100000000'}


# ── redeliver 操作测试 ────────────────────────────────────

class TestRedeliverAction:
    """测试 redeliver 操作"""

    def test_redeliver_requires_robot_id(self):
        """redeliver 操作缺少 --robot-id 时应报错退出"""
        output, _, exit_code = run_main(['redeliver', '--task-ids', 'T001,T002'])
        assert exit_code == 1
        assert '--robot-id' in output

    def test_redeliver_requires_task_ids(self):
        """redeliver 操作缺少 --task-ids 时应报错退出"""
        output, _, exit_code = run_main(['redeliver', '--robot-id', 'R001'])
        assert exit_code == 1
        assert '--task-ids' in output

    def test_redeliver_calls_correct_api(self):
        """redeliver 操作应调用 POST /api/transport/delay/redeliver"""
        api_response = {'code': 200, 'data': None}
        output, calls, _ = run_main(
            ['redeliver', '--robot-id', 'R001', '--task-ids', 'T001,T002'],
            api_response)
        args, kwargs = calls[0]
        assert args[0] == 'POST'
        assert args[1] == '/api/transport/delay/redeliver'
        assert kwargs.get('body') == {'robotId': 'R001', 'taskIds': ['T001', 'T002']}

    def test_redeliver_single_task_id(self):
        """redeliver 操作传入单个 taskId 时也应正确解析为列表"""
        api_response = {'code': 200, 'data': None}
        output, calls, _ = run_main(
            ['redeliver', '--robot-id', 'R001', '--task-ids', 'T001'],
            api_response)
        args, kwargs = calls[0]
        assert kwargs.get('body') == {'robotId': 'R001', 'taskIds': ['T001']}


# ── 错误响应格式测试 (需求 5.7, 8.4) ────────────────────

class TestErrorResponseFormatting:
    """测试 API 返回错误码时的输出格式"""

    def test_error_code_with_message(self):
        """API 返回非200 code 时应输出 '错误码: {code}, 错误信息: {message}'"""
        api_response = {'code': 9012, 'message': '运单不存在'}
        output, _, exit_code = run_main(['cancel', '--task-id', 'T999'], api_response)
        assert '错误码: 9012' in output
        assert '运单不存在' in output
        assert exit_code is None

    def test_api_returns_none(self):
        """API 返回 None 时应输出 'API 请求失败' 并退出"""
        output, _, exit_code = run_main(['cancel', '--task-id', 'T001'], None)
        assert 'API 请求失败' in output
        assert exit_code == 1

    def test_error_missing_message_shows_default(self):
        """API 返回错误码但无 message 字段时应显示 '未知错误'"""
        api_response = {'code': 999}
        output, _, _ = run_main(['cancel', '--task-id', 'T001'], api_response)
        assert '未知错误' in output


# ── 成功响应格式测试 (需求 8.3) ──────────────────────────

class TestSuccessResponseFormatting:
    """测试 API 返回成功时的输出格式"""

    def test_success_outputs_formatted_json(self):
        """成功时应以格式化 JSON 输出 data 字段"""
        data = {'taskId': 'T001', 'status': 'Cancelled'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['cancel', '--task-id', 'T001'], api_response)
        parsed = json.loads(output)
        assert parsed == data

    def test_success_chinese_characters_not_escaped(self):
        """输出中文字符时不应被 unicode 转义"""
        data = {'status': '已完成'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['status', '--task-id', 'T001'], api_response)
        assert '已完成' in output
        assert '\\u' not in output
