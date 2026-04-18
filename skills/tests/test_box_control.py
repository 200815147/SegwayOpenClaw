#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
box_control.py 单元测试
Validates: Requirements 6.7, 8.4

测试覆盖:
- 各操作的参数解析 (open, close, info, put-verify, take-verify)
- 缺少必要参数时的错误输出
- boxIndexes 逗号分隔字符串解析为整数列表
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
# 将 box_control 脚本目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'segway-box-control', 'scripts'))

import box_control


# ── 辅助函数 ──────────────────────────────────────────────

def run_main(args, mock_return=None):
    """
    用给定的 sys.argv 运行 box_control.main()，mock 掉 segway_auth.call_api。
    返回 (captured_stdout, call_api_call_args_list, exit_code)。
    """
    captured = io.StringIO()
    with patch('box_control.segway_auth.call_api', return_value=mock_return) as mock_api, \
         patch('sys.argv', ['box_control.py'] + args), \
         patch('sys.stdout', captured):
        try:
            box_control.main()
        except SystemExit as e:
            return captured.getvalue(), mock_api.call_args_list, e.code
        return captured.getvalue(), mock_api.call_args_list, None


# ── open 操作测试 ─────────────────────────────────────────

class TestOpenAction:
    """测试 open 操作"""

    def test_open_requires_robot_id_and_box_indexes(self):
        """open 操作缺少 --robot-id 和 --box-indexes 时应报错退出"""
        output, _, exit_code = run_main(['open'])
        assert exit_code == 1
        assert '--robot-id' in output and '--box-indexes' in output

    def test_open_calls_correct_api(self):
        """open 操作应调用 POST /api/transport/robot/boxs/open"""
        api_response = {'code': 200, 'data': None}
        output, calls, _ = run_main(['open', '--robot-id', 'R1', '--box-indexes', '1,2'], api_response)
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args == ('POST', '/api/transport/robot/boxs/open')
        assert kwargs.get('body') == {'robotId': 'R1', 'boxIndexes': [1, 2]}

    def test_open_single_box_index(self):
        """open 操作单个箱门编号应正确解析"""
        api_response = {'code': 200, 'data': None}
        _, calls, _ = run_main(['open', '--robot-id', 'R1', '--box-indexes', '3'], api_response)
        _, kwargs = calls[0]
        assert kwargs.get('body')['boxIndexes'] == [3]


# ── close 操作测试 ────────────────────────────────────────

class TestCloseAction:
    """测试 close 操作"""

    def test_close_requires_robot_id_and_box_indexes(self):
        """close 操作缺少参数时应报错退出"""
        output, _, exit_code = run_main(['close'])
        assert exit_code == 1
        assert '--robot-id' in output and '--box-indexes' in output

    def test_close_calls_correct_api(self):
        """close 操作应调用 POST /api/transport/robot/boxs/close"""
        api_response = {'code': 200, 'data': None}
        _, calls, _ = run_main(['close', '--robot-id', 'R1', '--box-indexes', '1,2,3'], api_response)
        args, kwargs = calls[0]
        assert args == ('POST', '/api/transport/robot/boxs/close')
        assert kwargs.get('body') == {'robotId': 'R1', 'boxIndexes': [1, 2, 3]}


# ── info 操作测试 ─────────────────────────────────────────

class TestInfoAction:
    """测试 info 操作"""

    def test_info_requires_robot_id(self):
        """info 操作缺少 --robot-id 时应报错退出"""
        output, _, exit_code = run_main(['info'])
        assert exit_code == 1
        assert '--robot-id' in output

    def test_info_calls_correct_api(self):
        """info 操作应调用 GET /api/transport/robot/{robotId}/box/size"""
        api_response = {'code': 200, 'data': {'boxSize': 4, 'remainBoxSize': 2, 'preBoxSize': 1}}
        output, calls, _ = run_main(['info', '--robot-id', 'R100'], api_response)
        args, kwargs = calls[0]
        assert args == ('GET', '/api/transport/robot/R100/box/size')

    def test_info_success_output(self):
        """info 成功时应输出格式化的 JSON data"""
        data = {'boxSize': 4, 'remainBoxSize': 2, 'preBoxSize': 1}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['info', '--robot-id', 'R100'], api_response)
        parsed = json.loads(output)
        assert parsed == data


# ── put-verify 操作测试 ───────────────────────────────────

class TestPutVerifyAction:
    """测试 put-verify 操作"""

    def test_put_verify_requires_robot_id_and_task_id(self):
        """put-verify 操作缺少参数时应报错退出"""
        output, _, exit_code = run_main(['put-verify'])
        assert exit_code == 1
        assert '--robot-id' in output and '--task-id' in output

    def test_put_verify_calls_correct_api(self):
        """put-verify 操作应调用 POST /api/transport/task/put/verify"""
        api_response = {'code': 200, 'data': None}
        _, calls, _ = run_main(['put-verify', '--robot-id', 'R1', '--task-id', 'T100'], api_response)
        args, kwargs = calls[0]
        assert args == ('POST', '/api/transport/task/put/verify')
        assert kwargs.get('body') == {'robotId': 'R1', 'taskId': 'T100'}


# ── take-verify 操作测试 ──────────────────────────────────

class TestTakeVerifyAction:
    """测试 take-verify 操作"""

    def test_take_verify_requires_robot_id_and_task_id(self):
        """take-verify 操作缺少参数时应报错退出"""
        output, _, exit_code = run_main(['take-verify'])
        assert exit_code == 1
        assert '--robot-id' in output and '--task-id' in output

    def test_take_verify_calls_correct_api(self):
        """take-verify 操作应调用 POST /api/transport/task/take/verify"""
        api_response = {'code': 200, 'data': None}
        _, calls, _ = run_main(['take-verify', '--robot-id', 'R1', '--task-id', 'T200'], api_response)
        args, kwargs = calls[0]
        assert args == ('POST', '/api/transport/task/take/verify')
        assert kwargs.get('body') == {'robotId': 'R1', 'taskId': 'T200'}


# ── 错误响应格式测试 (需求 6.7, 8.4) ────────────────────

class TestErrorResponseFormatting:
    """测试 API 返回错误码时的输出格式"""

    def test_error_code_with_message(self):
        """API 返回非200 code 时应输出 '错误码: {code}, 错误信息: {message}'"""
        api_response = {'code': 9012, 'message': '无可用机器人'}
        output, _, _ = run_main(['info', '--robot-id', 'R1'], api_response)
        assert '错误码: 9012' in output
        assert '无可用机器人' in output

    def test_error_with_result_code_format(self):
        """API 使用 resultCode/resultMessage 格式时也应正确输出"""
        api_response = {'resultCode': 500, 'resultMessage': '服务器内部错误'}
        output, _, _ = run_main(['info', '--robot-id', 'R1'], api_response)
        assert '错误码: 500' in output
        assert '服务器内部错误' in output

    def test_api_returns_none(self):
        """API 返回 None 时应输出 'API 请求失败' 并退出"""
        output, _, exit_code = run_main(['info', '--robot-id', 'R1'], None)
        assert 'API 请求失败' in output
        assert exit_code == 1


# ── 成功响应格式测试 (需求 8.3) ──────────────────────────

class TestSuccessResponseFormatting:
    """测试 API 返回成功时的输出格式"""

    def test_success_outputs_formatted_json(self):
        """成功时应以格式化 JSON 输出 data 字段"""
        data = {'boxSize': 4, 'remainBoxSize': 2}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['info', '--robot-id', 'R1'], api_response)
        parsed = json.loads(output)
        assert parsed == data

    def test_success_null_data(self):
        """data 为 None 时应输出 null"""
        api_response = {'code': 200, 'data': None}
        output, _, _ = run_main(['open', '--robot-id', 'R1', '--box-indexes', '1'], api_response)
        assert output.strip() == 'null'

    def test_success_chinese_characters_not_escaped(self):
        """输出中文字符时不应被 unicode 转义"""
        data = {'status': '箱门已打开'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['info', '--robot-id', 'R1'], api_response)
        assert '箱门已打开' in output
        assert '\\u' not in output
