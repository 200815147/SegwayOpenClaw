#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robot.py 单元测试
Validates: Requirements 3.9, 8.4

测试覆盖:
- 各操作的参数解析 (list, status, location, locations, sort-list, robot-info, robots-info)
- 缺少必要参数时的错误输出
- API 返回错误码时的输出格式
- API 返回成功时的输出格式
- POST 操作的请求体构造
"""

import io
import json
import os
import sys
from unittest.mock import patch

import pytest

# 将 skills 目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# 将 robot 脚本目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'segway-robot', 'scripts'))

import robot


# ── 辅助函数 ──────────────────────────────────────────────

def run_main(args, mock_return=None):
    """
    用给定的 sys.argv 运行 robot.main()，mock 掉 segway_auth.call_api。
    返回 (captured_stdout, call_api_call_args_list, exit_code)。
    """
    captured = io.StringIO()
    with patch('robot.segway_auth.call_api', return_value=mock_return) as mock_api, \
         patch('sys.argv', ['robot.py'] + args), \
         patch('sys.stdout', captured):
        try:
            robot.main()
        except SystemExit as e:
            return captured.getvalue(), mock_api.call_args_list, e.code
        return captured.getvalue(), mock_api.call_args_list, None


# ── list 操作测试 ─────────────────────────────────────────

class TestListAction:
    """测试 list 操作"""

    def test_list_calls_correct_api(self):
        """list 操作应调用 GET /api/transport/robots"""
        api_response = {'code': 200, 'data': [{'robotId': 'R1', 'nickname': '小白'}]}
        output, calls, exit_code = run_main(['list'], api_response)
        assert exit_code is None
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args == ('GET', '/api/transport/robots')

    def test_list_success_output(self):
        """list 成功时应输出格式化的 JSON data"""
        data = [{'robotId': 'R1', 'nickname': '小白'}]
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['list'], api_response)
        parsed = json.loads(output)
        assert parsed == data


# ── status 操作测试 ───────────────────────────────────────

class TestStatusAction:
    """测试 status 操作"""

    def test_status_requires_robot_id(self):
        """status 操作缺少 --robot-id 时应报错退出"""
        output, _, exit_code = run_main(['status'])
        assert exit_code == 1
        assert '--robot-id' in output

    def test_status_calls_correct_api(self):
        """status 操作应调用 GET /api/transport/robot/{robotId}/status"""
        api_response = {'code': 200, 'data': {'status': 'idle'}}
        output, calls, _ = run_main(['status', '--robot-id', 'R100'], api_response)
        args, kwargs = calls[0]
        assert args == ('GET', '/api/transport/robot/R100/status')


# ── location 操作测试 ─────────────────────────────────────

class TestLocationAction:
    """测试 location 操作"""

    def test_location_requires_both_ids(self):
        """location 操作缺少 --area-id 和 --robot-id 时应报错退出"""
        output, _, exit_code = run_main(['location'])
        assert exit_code == 1
        assert '--area-id' in output and '--robot-id' in output

    def test_location_requires_robot_id(self):
        """location 操作仅有 --area-id 缺少 --robot-id 时应报错退出"""
        output, _, exit_code = run_main(['location', '--area-id', 'A1'])
        assert exit_code == 1
        assert '--robot-id' in output

    def test_location_requires_area_id(self):
        """location 操作仅有 --robot-id 缺少 --area-id 时应报错退出"""
        output, _, exit_code = run_main(['location', '--robot-id', 'R1'])
        assert exit_code == 1
        assert '--area-id' in output

    def test_location_calls_correct_api(self):
        """location 操作应调用正确的 API 路径并传递 areaId 和 robotId 查询参数"""
        api_response = {'code': 200, 'data': {'x': 10.5, 'y': 20.3}}
        output, calls, _ = run_main(['location', '--area-id', 'A1', '--robot-id', 'R1'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'GET'
        assert args[1] == '/business-robot-area/api/transport/customer/robot/current/location/info'
        assert kwargs.get('query_params') == {'areaId': 'A1', 'robotId': 'R1'}


# ── locations 操作测试 ────────────────────────────────────

class TestLocationsAction:
    """测试 locations 操作"""

    def test_locations_requires_area_id_and_robot_ids(self):
        """locations 操作缺少参数时应报错退出"""
        output, _, exit_code = run_main(['locations'])
        assert exit_code == 1
        assert '--area-id' in output and '--robot-ids' in output

    def test_locations_calls_correct_api_with_body(self):
        """locations 操作应调用 POST 并传递正确的请求体"""
        api_response = {'code': 200, 'data': []}
        output, calls, _ = run_main(
            ['locations', '--area-id', 'A1', '--robot-ids', 'R1,R2,R3'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'POST'
        assert args[1] == '/business-robot-area/api/transport/customer/robots/current/location/info'
        assert kwargs.get('body') == {'areaId': 'A1', 'robotIds': ['R1', 'R2', 'R3']}

    def test_locations_splits_robot_ids(self):
        """locations 操作应将逗号分隔的 robotIds 拆分为列表"""
        api_response = {'code': 200, 'data': []}
        _, calls, _ = run_main(
            ['locations', '--area-id', 'A1', '--robot-ids', 'R1, R2'], api_response)
        body = calls[0][1].get('body')
        assert body['robotIds'] == ['R1', 'R2']


# ── sort-list 操作测试 ────────────────────────────────────

class TestSortListAction:
    """测试 sort-list 操作"""

    def test_sort_list_requires_area_id(self):
        """sort-list 操作缺少 --area-id 时应报错退出"""
        output, _, exit_code = run_main(['sort-list'])
        assert exit_code == 1
        assert '--area-id' in output

    def test_sort_list_calls_correct_api(self):
        """sort-list 操作应调用正确的 API 路径并传递 areaId"""
        api_response = {'code': 200, 'data': []}
        output, calls, _ = run_main(['sort-list', '--area-id', 'A1'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'GET'
        assert args[1] == '/business-robot-area/api/transport/customer/robot/sort/list'
        assert kwargs.get('query_params') == {'areaId': 'A1'}


# ── robot-info 操作测试 ───────────────────────────────────

class TestRobotInfoAction:
    """测试 robot-info 操作"""

    def test_robot_info_requires_robot_id(self):
        """robot-info 操作缺少 --robot-id 时应报错退出"""
        output, _, exit_code = run_main(['robot-info'])
        assert exit_code == 1
        assert '--robot-id' in output

    def test_robot_info_calls_correct_api_with_body(self):
        """robot-info 操作应调用 POST 并传递正确的请求体"""
        api_response = {'code': 200, 'data': {'robotId': 'R1', 'status': 'idle'}}
        output, calls, _ = run_main(['robot-info', '--robot-id', 'R1'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'POST'
        assert args[1] == '/business-order/api/transport/customer/robot/current/info'
        assert kwargs.get('body') == {'robotId': 'R1'}


# ── robots-info 操作测试 ──────────────────────────────────

class TestRobotsInfoAction:
    """测试 robots-info 操作"""

    def test_robots_info_requires_robot_ids(self):
        """robots-info 操作缺少 --robot-ids 时应报错退出"""
        output, _, exit_code = run_main(['robots-info'])
        assert exit_code == 1
        assert '--robot-ids' in output

    def test_robots_info_calls_correct_api_with_body(self):
        """robots-info 操作应调用 POST 并传递正确的请求体"""
        api_response = {'code': 200, 'data': []}
        output, calls, _ = run_main(['robots-info', '--robot-ids', 'R1,R2'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'POST'
        assert args[1] == '/business-order/api/transport/customer/robots/current/info'
        assert kwargs.get('body') == {'robotIds': ['R1', 'R2']}

    def test_robots_info_splits_robot_ids(self):
        """robots-info 操作应将逗号分隔的 robotIds 拆分为列表"""
        api_response = {'code': 200, 'data': []}
        _, calls, _ = run_main(['robots-info', '--robot-ids', 'R1, R2, R3'], api_response)
        body = calls[0][1].get('body')
        assert body['robotIds'] == ['R1', 'R2', 'R3']


# ── 错误响应格式测试 (需求 3.9, 8.4) ────────────────────

class TestErrorResponseFormatting:
    """测试 API 返回错误码时的输出格式"""

    def test_error_code_with_message(self):
        """API 返回非200 code 时应输出 '错误码: {code}, 错误信息: {message}'"""
        api_response = {'code': 9012, 'message': '无可用机器人'}
        output, _, exit_code = run_main(['list'], api_response)
        assert '错误码: 9012' in output
        assert '无可用机器人' in output
        assert exit_code is None

    def test_api_returns_none(self):
        """API 返回 None 时应输出 'API 请求失败' 并退出"""
        output, _, exit_code = run_main(['list'], None)
        assert 'API 请求失败' in output
        assert exit_code == 1

    def test_error_missing_message_shows_default(self):
        """API 返回错误码但无 message 字段时应显示 '未知错误'"""
        api_response = {'code': 999}
        output, _, _ = run_main(['list'], api_response)
        assert '未知错误' in output


# ── 成功响应格式测试 (需求 8.3) ──────────────────────────

class TestSuccessResponseFormatting:
    """测试 API 返回成功时的输出格式"""

    def test_success_outputs_formatted_json(self):
        """成功时应以格式化 JSON 输出 data 字段"""
        data = {'robotId': 'R1', 'nickname': '小白', 'battery': 85}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['list'], api_response)
        parsed = json.loads(output)
        assert parsed == data

    def test_success_chinese_characters_not_escaped(self):
        """输出中文字符时不应被 unicode 转义"""
        data = {'nickname': '配送小白'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['list'], api_response)
        assert '配送小白' in output
        assert '\\u' not in output
