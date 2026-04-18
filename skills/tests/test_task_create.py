#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_create.py 单元测试
Validates: Requirements 4.8, 8.4

测试覆盖:
- 各运单类型的请求体构造 (guidance, special-guidance, take-deliver)
- 可选参数的正确传递
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
# 将 task_create 脚本目录加入 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'segway-task-create', 'scripts'))

import task_create


# ── 辅助函数 ──────────────────────────────────────────────

def run_main(args, mock_return=None):
    """
    用给定的 sys.argv 运行 task_create.main()，mock 掉 segway_auth.call_api。
    返回 (captured_stdout, call_api_call_args_list, exit_code)。
    """
    captured = io.StringIO()
    with patch('task_create.segway_auth.call_api', return_value=mock_return) as mock_api, \
         patch('sys.argv', ['task_create.py'] + args), \
         patch('sys.stdout', captured):
        try:
            task_create.main()
        except SystemExit as e:
            return captured.getvalue(), mock_api.call_args_list, e.code
        return captured.getvalue(), mock_api.call_args_list, None


# ── guidance 操作测试 ─────────────────────────────────────

class TestGuidanceAction:
    """测试 guidance 操作"""

    def test_guidance_requires_area_id_and_station_id(self):
        """guidance 操作缺少必要参数时应报错退出"""
        output, _, exit_code = run_main(['guidance'])
        assert exit_code == 1
        assert '--area-id' in output and '--station-id' in output

    def test_guidance_calls_correct_api(self):
        """guidance 操作应调用 POST /api/transport/task/create"""
        api_response = {'code': 200, 'data': {'taskId': 'T001'}}
        output, calls, exit_code = run_main(
            ['guidance', '--area-id', 'A1', '--station-id', 'S1'], api_response)
        assert exit_code is None
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args == ('POST', '/api/transport/task/create')

    def test_guidance_body_structure(self):
        """guidance 请求体应包含 areaId、taskType=Guidance、stationId"""
        api_response = {'code': 200, 'data': {'taskId': 'T001'}}
        _, calls, _ = run_main(
            ['guidance', '--area-id', 'A1', '--station-id', 'S1'], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert body['areaId'] == 'A1'
        assert body['taskType'] == 'Guidance'
        assert body['stationId'] == 'S1'

    def test_guidance_without_optional_params(self):
        """guidance 不传可选参数时，请求体不应包含可选字段"""
        api_response = {'code': 200, 'data': {'taskId': 'T001'}}
        _, calls, _ = run_main(
            ['guidance', '--area-id', 'A1', '--station-id', 'S1'], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert 'priorityLevel' not in body
        assert 'outId' not in body
        assert 'callbackUrl' not in body
        assert 'remark' not in body

    def test_guidance_with_optional_params(self):
        """guidance 传入可选参数时，请求体应正确包含"""
        api_response = {'code': 200, 'data': {'taskId': 'T001'}}
        _, calls, _ = run_main([
            'guidance', '--area-id', 'A1', '--station-id', 'S1',
            '--priority-level', '55', '--out-id', 'EXT001',
            '--callback-url', 'https://example.com/cb', '--remark', '测试备注'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert body['priorityLevel'] == 55
        assert body['outId'] == 'EXT001'
        assert body['callbackUrl'] == 'https://example.com/cb'
        assert body['remark'] == '测试备注'


# ── special-guidance 操作测试 ─────────────────────────────

class TestSpecialGuidanceAction:
    """测试 special-guidance 操作"""

    def test_special_guidance_requires_all_params(self):
        """special-guidance 缺少必要参数时应报错退出"""
        output, _, exit_code = run_main(['special-guidance', '--area-id', 'A1'])
        assert exit_code == 1

    def test_special_guidance_body_structure(self):
        """special-guidance 请求体应包含 robotId 和 guidanceWaitTime"""
        api_response = {'code': 200, 'data': {'taskId': 'T002'}}
        _, calls, _ = run_main([
            'special-guidance', '--area-id', 'A1', '--robot-id', 'R1',
            '--station-id', 'S1', '--guidance-wait-time', '60'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert body['areaId'] == 'A1'
        assert body['taskType'] == 'Guidance'
        assert body['stationId'] == 'S1'
        assert body['robotId'] == 'R1'
        assert body['guidanceWaitTime'] == 60

    def test_special_guidance_with_optional_params(self):
        """special-guidance 传入可选参数时应正确包含"""
        api_response = {'code': 200, 'data': {'taskId': 'T002'}}
        _, calls, _ = run_main([
            'special-guidance', '--area-id', 'A1', '--robot-id', 'R1',
            '--station-id', 'S1', '--guidance-wait-time', '60',
            '--priority-level', '45', '--remark', '特殊引领'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert body['priorityLevel'] == 45
        assert body['remark'] == '特殊引领'


# ── take-deliver 操作测试 ─────────────────────────────────

class TestTakeDeliverAction:
    """测试 take-deliver 操作"""

    def test_take_deliver_requires_params(self):
        """take-deliver 缺少必要参数时应报错退出"""
        output, _, exit_code = run_main(['take-deliver', '--area-id', 'A1'])
        assert exit_code == 1

    def test_take_deliver_body_structure(self):
        """take-deliver 请求体应包含正确的 stationPairList 结构"""
        api_response = {'code': 200, 'data': {'taskId': 'T003'}}
        _, calls, _ = run_main([
            'take-deliver', '--area-id', 'A1',
            '--take-station-id', 'S1', '--take-open-code', '1234',
            '--deliver-station-id', 'S2'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert body['areaId'] == 'A1'
        assert body['taskType'] == 'TakeAndDeliver'
        assert len(body['stationPairList']) == 2
        take_pair = body['stationPairList'][0]
        assert take_pair['stationId'] == 'S1'
        assert take_pair['openCode'] == '1234'
        assert take_pair['action'] == 'TAKE'
        deliver_pair = body['stationPairList'][1]
        assert deliver_pair['stationId'] == 'S2'
        assert deliver_pair['action'] == 'DELIVER'

    def test_take_deliver_with_verify(self):
        """take-deliver 传入 --verify 时，送件 pair 应包含 verify=True"""
        api_response = {'code': 200, 'data': {'taskId': 'T003'}}
        _, calls, _ = run_main([
            'take-deliver', '--area-id', 'A1',
            '--take-station-id', 'S1', '--take-open-code', '1234',
            '--deliver-station-id', 'S2', '--verify'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        deliver_pair = body['stationPairList'][1]
        assert deliver_pair['verify'] is True

    def test_take_deliver_with_deliver_open_code(self):
        """take-deliver 传入送件开箱码时应正确设置"""
        api_response = {'code': 200, 'data': {'taskId': 'T003'}}
        _, calls, _ = run_main([
            'take-deliver', '--area-id', 'A1',
            '--take-station-id', 'S1', '--take-open-code', '1234',
            '--deliver-station-id', 'S2', '--deliver-open-code', '5678'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        deliver_pair = body['stationPairList'][1]
        assert deliver_pair['openCode'] == '5678'

    def test_take_deliver_without_optional_params(self):
        """take-deliver 不传可选参数时，请求体不应包含可选字段"""
        api_response = {'code': 200, 'data': {'taskId': 'T003'}}
        _, calls, _ = run_main([
            'take-deliver', '--area-id', 'A1',
            '--take-station-id', 'S1', '--take-open-code', '1234',
            '--deliver-station-id', 'S2'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert 'priorityLevel' not in body
        assert 'waitTime' not in body
        assert 'verifyTimeout' not in body
        assert 'phoneNum' not in body
        deliver_pair = body['stationPairList'][1]
        assert 'verify' not in deliver_pair
        assert 'openCode' not in deliver_pair

    def test_take_deliver_with_all_optional_params(self):
        """take-deliver 传入所有可选参数时应正确包含"""
        api_response = {'code': 200, 'data': {'taskId': 'T003'}}
        _, calls, _ = run_main([
            'take-deliver', '--area-id', 'A1',
            '--take-station-id', 'S1', '--take-open-code', '1234',
            '--deliver-station-id', 'S2', '--verify', '--deliver-open-code', '5678',
            '--priority-level', '50', '--wait-time', '120',
            '--verify-timeout', '300', '--phone-num', '13800138000',
            '--out-id', 'EXT003', '--callback-url', 'https://example.com/cb',
            '--remark', '取送测试'
        ], api_response)
        _, kwargs = calls[0]
        body = kwargs.get('body')
        assert body['priorityLevel'] == 50
        assert body['waitTime'] == 120
        assert body['verifyTimeout'] == 300
        assert body['phoneNum'] == '13800138000'
        assert body['outId'] == 'EXT003'
        assert body['callbackUrl'] == 'https://example.com/cb'
        assert body['remark'] == '取送测试'


# ── 错误响应格式测试 (需求 4.8, 8.4) ────────────────────

class TestErrorResponseFormatting:
    """测试 API 返回错误码时的输出格式"""

    def test_error_code_with_message(self):
        """API 返回非200 code 时应输出错误码和错误信息"""
        api_response = {'code': 9012, 'message': '无可用机器人'}
        output, _, exit_code = run_main(
            ['guidance', '--area-id', 'A1', '--station-id', 'S1'], api_response)
        assert '错误码: 9012' in output
        assert '无可用机器人' in output

    def test_api_returns_none(self):
        """API 返回 None 时应输出错误并退出"""
        output, _, exit_code = run_main(
            ['guidance', '--area-id', 'A1', '--station-id', 'S1'], None)
        assert 'API 请求失败' in output
        assert exit_code == 1


# ── 成功响应格式测试 (需求 8.3) ──────────────────────────

class TestSuccessResponseFormatting:
    """测试 API 返回成功时的输出格式"""

    def test_success_outputs_task_id(self):
        """成功时应以格式化 JSON 输出 data 字段"""
        data = {'taskId': 'T001'}
        api_response = {'code': 200, 'data': data}
        output, _, _ = run_main(
            ['guidance', '--area-id', 'A1', '--station-id', 'S1'], api_response)
        parsed = json.loads(output)
        assert parsed == data
