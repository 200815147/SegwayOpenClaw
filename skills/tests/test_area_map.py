#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
area_map.py 单元测试
Validates: Requirements 2.7, 8.4

测试覆盖:
- 各操作的参数解析 (areas, stations, service, map-list, map-info)
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
# 将 area_map 脚本目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'segway-area-map', 'scripts'))

import area_map


# ── 辅助函数 ──────────────────────────────────────────────

def run_main(args, mock_return=None):
    """
    用给定的 sys.argv 运行 area_map.main()，mock 掉 segway_auth.call_api。
    返回 (captured_stdout, call_api_call_args_list, exit_code)。
    """
    captured = io.StringIO()
    with patch('area_map.segway_auth.call_api', return_value=mock_return) as mock_api, \
         patch('sys.argv', ['area_map.py'] + args), \
         patch('sys.stdout', captured):
        try:
            area_map.main()
        except SystemExit as e:
            return captured.getvalue(), mock_api.call_args_list, e.code
        return captured.getvalue(), mock_api.call_args_list, None


# ── 参数解析测试 ──────────────────────────────────────────

class TestAreasAction:
    """测试 areas 操作"""

    def test_areas_calls_correct_api(self):
        """areas 操作应调用 GET /api/transport/areas"""
        api_response = {'code': 200, 'data': [{'areaId': '1', 'areaName': '测试楼宇'}]}
        output, calls, exit_code = run_main(['areas'], api_response)
        assert exit_code is None
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args == ('GET', '/api/transport/areas')

    def test_areas_success_output(self):
        """areas 成功时应输出格式化的 JSON data"""
        data = [{'areaId': '1', 'areaName': '测试楼宇'}]
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['areas'], api_response)
        parsed = json.loads(output)
        assert parsed == data


class TestStationsAction:
    """测试 stations 操作"""

    def test_stations_requires_area_id(self):
        """stations 操作缺少 --area-id 时应报错退出"""
        output, _, exit_code = run_main(['stations'])
        assert exit_code == 1
        assert '--area-id' in output

    def test_stations_calls_correct_api(self):
        """stations 操作应调用 GET /api/transport/area/{areaId}/stations"""
        api_response = {'code': 200, 'data': []}
        output, calls, _ = run_main(['stations', '--area-id', 'A100'], api_response)
        args, kwargs = calls[0]
        assert args == ('GET', '/api/transport/area/A100/stations')


class TestServiceAction:
    """测试 service 操作"""

    def test_service_requires_area_id(self):
        """service 操作缺少 --area-id 时应报错退出"""
        output, _, exit_code = run_main(['service'])
        assert exit_code == 1
        assert '--area-id' in output

    def test_service_calls_correct_api(self):
        """service 操作应调用 GET /api/transport/area/service 并传递 areaId 查询参数"""
        api_response = {'code': 200, 'data': {'available': True}}
        output, calls, _ = run_main(['service', '--area-id', 'A200'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'GET'
        assert args[1] == '/api/transport/area/service'
        assert kwargs.get('query_params') == {'areaId': 'A200'}


class TestMapListAction:
    """测试 map-list 操作"""

    def test_map_list_requires_area_id(self):
        """map-list 操作缺少 --area-id 时应报错退出"""
        output, _, exit_code = run_main(['map-list'])
        assert exit_code == 1
        assert '--area-id' in output

    def test_map_list_calls_correct_api(self):
        """map-list 操作应调用正确的 API 路径并传递 areaId"""
        api_response = {'code': 200, 'data': []}
        output, calls, _ = run_main(['map-list', '--area-id', 'A300'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'GET'
        assert args[1] == '/business-robot-area/api/transport/customer/area/map/list'
        assert kwargs.get('query_params') == {'areaId': 'A300'}


class TestMapInfoAction:
    """测试 map-info 操作"""

    def test_map_info_requires_both_ids(self):
        """map-info 操作缺少 --area-id 和 --map-id 时应报错退出"""
        output, _, exit_code = run_main(['map-info'])
        assert exit_code == 1
        assert '--area-id' in output and '--map-id' in output

    def test_map_info_requires_map_id(self):
        """map-info 操作仅有 --area-id 缺少 --map-id 时应报错退出"""
        output, _, exit_code = run_main(['map-info', '--area-id', 'A1'])
        assert exit_code == 1
        assert '--map-id' in output

    def test_map_info_requires_area_id(self):
        """map-info 操作仅有 --map-id 缺少 --area-id 时应报错退出"""
        output, _, exit_code = run_main(['map-info', '--map-id', 'M1'])
        assert exit_code == 1
        assert '--area-id' in output

    def test_map_info_calls_correct_api(self):
        """map-info 操作应调用正确的 API 路径并传递 areaId 和 mapId"""
        api_response = {'code': 200, 'data': {'mapId': 'M1', 'mapName': '1F'}}
        output, calls, _ = run_main(['map-info', '--area-id', 'A1', '--map-id', 'M1'], api_response)
        args, kwargs = calls[0]
        assert args[0] == 'GET'
        assert args[1] == '/business-robot-area/api/transport/customer/map/info'
        assert kwargs.get('query_params') == {'areaId': 'A1', 'mapId': 'M1'}


# ── 错误响应格式测试 (需求 2.7, 8.4) ────────────────────

class TestErrorResponseFormatting:
    """测试 API 返回错误码时的输出格式"""

    def test_error_code_with_message(self):
        """API 返回非200 code 时应输出 '错误码: {code}, 错误信息: {message}'"""
        api_response = {'code': 9012, 'message': '无可用机器人'}
        output, _, exit_code = run_main(['areas'], api_response)
        assert '错误码: 9012' in output
        assert '无可用机器人' in output
        assert exit_code is None

    def test_error_with_result_code_format(self):
        """API 使用 resultCode/resultMessage 格式时也应正确输出"""
        api_response = {'resultCode': 500, 'resultMessage': '服务器内部错误'}
        output, _, _ = run_main(['areas'], api_response)
        assert '错误码: 500' in output
        assert '服务器内部错误' in output

    def test_error_with_string_code(self):
        """API 返回字符串类型的 code 时也应正确处理"""
        api_response = {'code': '400', 'message': '参数错误'}
        output, _, _ = run_main(['areas'], api_response)
        assert '错误码: 400' in output
        assert '参数错误' in output

    def test_api_returns_none(self):
        """API 返回 None 时应输出 'API 请求失败' 并退出"""
        output, _, exit_code = run_main(['areas'], None)
        assert 'API 请求失败' in output
        assert exit_code == 1

    def test_error_missing_message_shows_default(self):
        """API 返回错误码但无 message 字段时应显示 '未知错误'"""
        api_response = {'code': 999}
        output, _, _ = run_main(['areas'], api_response)
        assert '未知错误' in output


# ── 成功响应格式测试 (需求 8.3) ──────────────────────────

class TestSuccessResponseFormatting:
    """测试 API 返回成功时的输出格式"""

    def test_success_outputs_formatted_json(self):
        """成功时应以格式化 JSON 输出 data 字段"""
        data = {'areaId': 'A1', 'areaName': '总部大楼', 'lat': 39.9, 'lng': 116.4}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['areas'], api_response)
        parsed = json.loads(output)
        assert parsed == data

    def test_success_with_string_200_code(self):
        """code 为字符串 '200' 时也应视为成功"""
        data = [{'stationId': 'S1'}]
        api_response = {'code': '200', 'data': data}
        output, _, _ = run_main(['stations', '--area-id', 'A1'], api_response)
        parsed = json.loads(output)
        assert parsed == data

    def test_success_chinese_characters_not_escaped(self):
        """输出中文字符时不应被 unicode 转义"""
        data = {'name': '一楼大厅'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(['areas'], api_response)
        assert '一楼大厅' in output
        assert '\\u' not in output

    def test_success_null_data(self):
        """data 为 None 时应输出 null"""
        api_response = {'code': 200, 'data': None}
        output, _, _ = run_main(['areas'], api_response)
        assert output.strip() == 'null'
