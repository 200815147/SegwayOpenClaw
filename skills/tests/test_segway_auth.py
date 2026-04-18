#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
segway_auth.py 单元测试
Validates: Requirements 1.1, 1.2, 1.5
"""

import os
import re
import sys

import pytest

# 将 skills 目录加入 path 以导入 segway_auth
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from segway_auth import gmt_time, gen_authorization, get_config


class TestGmtTime:
    """测试 gmt_time() 返回格式正确 (需求 1.1)"""

    def test_format_matches_expected_pattern(self):
        """gmt_time() 应返回 '%a, %d %b %Y %H:%M:%S %Z' 格式的 GMT 时间字符串"""
        result = gmt_time()
        # 例: "Mon, 14 Jul 2025 08:30:00 GMT"
        pattern = r'^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$'
        assert re.match(pattern, result), f"格式不匹配: {result}"

    def test_ends_with_gmt(self):
        """时间字符串应以 GMT 结尾"""
        result = gmt_time()
        assert result.endswith('GMT')

    def test_returns_string(self):
        """gmt_time() 应返回字符串类型"""
        assert isinstance(gmt_time(), str)


class TestGenAuthorization:
    """测试 gen_authorization() 签名结果与已知输入匹配 (需求 1.2)"""

    def test_known_input_path_only(self):
        """使用已知输入验证 HMAC-SHA256 签名结果（路径输入）"""
        result = gen_authorization(
            'test_name', 'test_key',
            'Fri, 17 Feb 2012 23:34:53 GMT',
            '/user', 'GET'
        )
        assert result == 'SEGWAY test_name:1nZUqYnT3cdH3Vxt020Z69pKm579h4YBuT/uZdN0y8g='

    def test_known_input_full_url(self):
        """使用完整 URL 输入验证签名（应自动提取路径部分）"""
        result = gen_authorization(
            'test_name', 'test_key',
            'Fri, 17 Feb 2012 23:34:53 GMT',
            'https://api-gate-delivery.loomo.com/api/transport/areas', 'GET'
        )
        assert result == 'SEGWAY test_name:tmXB1yayf2rbN+LgRRPL9KCe+W1R4dZ1dl3Hzit1kwc='

    def test_output_format(self):
        """返回值应以 'SEGWAY ' 开头，包含 access_name 和 base64 签名"""
        result = gen_authorization('myname', 'mykey', 'some-date', '/path', 'POST')
        assert result.startswith('SEGWAY myname:')
        # 冒号后面应该是 base64 编码的签名
        signature_part = result.split(':')[1]
        assert len(signature_part) > 0

    def test_different_methods_produce_different_signatures(self):
        """不同 HTTP 方法应产生不同签名"""
        args = ('name', 'key', 'date', '/path')
        sig_get = gen_authorization(*args, 'GET')
        sig_post = gen_authorization(*args, 'POST')
        assert sig_get != sig_post


class TestGetConfig:
    """测试 get_config() 在环境变量缺失时终止执行 (需求 1.5)"""

    def test_missing_both_vars_exits(self):
        """两个必要环境变量都缺失时应调用 sys.exit(1)"""
        old_name = os.environ.pop('SEGWAY_ACCESS_NAME', None)
        old_key = os.environ.pop('SEGWAY_ACCESS_KEY', None)
        try:
            with pytest.raises(SystemExit) as exc_info:
                get_config()
            assert exc_info.value.code == 1
        finally:
            if old_name is not None:
                os.environ['SEGWAY_ACCESS_NAME'] = old_name
            if old_key is not None:
                os.environ['SEGWAY_ACCESS_KEY'] = old_key

    def test_missing_access_name_exits(self):
        """仅缺少 SEGWAY_ACCESS_NAME 时应终止"""
        old_name = os.environ.pop('SEGWAY_ACCESS_NAME', None)
        old_key = os.environ.get('SEGWAY_ACCESS_KEY')
        os.environ['SEGWAY_ACCESS_KEY'] = 'some_key'
        try:
            with pytest.raises(SystemExit) as exc_info:
                get_config()
            assert exc_info.value.code == 1
        finally:
            if old_name is not None:
                os.environ['SEGWAY_ACCESS_NAME'] = old_name
            else:
                os.environ.pop('SEGWAY_ACCESS_NAME', None)
            if old_key is not None:
                os.environ['SEGWAY_ACCESS_KEY'] = old_key
            else:
                os.environ.pop('SEGWAY_ACCESS_KEY', None)

    def test_missing_access_key_exits(self):
        """仅缺少 SEGWAY_ACCESS_KEY 时应终止"""
        old_key = os.environ.pop('SEGWAY_ACCESS_KEY', None)
        old_name = os.environ.get('SEGWAY_ACCESS_NAME')
        os.environ['SEGWAY_ACCESS_NAME'] = 'some_name'
        try:
            with pytest.raises(SystemExit) as exc_info:
                get_config()
            assert exc_info.value.code == 1
        finally:
            if old_key is not None:
                os.environ['SEGWAY_ACCESS_KEY'] = old_key
            else:
                os.environ.pop('SEGWAY_ACCESS_KEY', None)
            if old_name is not None:
                os.environ['SEGWAY_ACCESS_NAME'] = old_name
            else:
                os.environ.pop('SEGWAY_ACCESS_NAME', None)

    def test_valid_config_returns_tuple(self):
        """环境变量齐全时应返回 (access_name, access_key, domain) 元组"""
        old_name = os.environ.get('SEGWAY_ACCESS_NAME')
        old_key = os.environ.get('SEGWAY_ACCESS_KEY')
        old_domain = os.environ.get('SEGWAY_API_DOMAIN')
        os.environ['SEGWAY_ACCESS_NAME'] = 'test_name'
        os.environ['SEGWAY_ACCESS_KEY'] = 'test_key'
        os.environ.pop('SEGWAY_API_DOMAIN', None)
        try:
            name, key, domain = get_config()
            assert name == 'test_name'
            assert key == 'test_key'
            assert domain == 'https://api-gate-delivery.loomo.com'
        finally:
            if old_name is not None:
                os.environ['SEGWAY_ACCESS_NAME'] = old_name
            else:
                os.environ.pop('SEGWAY_ACCESS_NAME', None)
            if old_key is not None:
                os.environ['SEGWAY_ACCESS_KEY'] = old_key
            else:
                os.environ.pop('SEGWAY_ACCESS_KEY', None)
            if old_domain is not None:
                os.environ['SEGWAY_API_DOMAIN'] = old_domain

    def test_custom_domain_override(self):
        """设置 SEGWAY_API_DOMAIN 时应覆盖默认域名"""
        old_name = os.environ.get('SEGWAY_ACCESS_NAME')
        old_key = os.environ.get('SEGWAY_ACCESS_KEY')
        old_domain = os.environ.get('SEGWAY_API_DOMAIN')
        os.environ['SEGWAY_ACCESS_NAME'] = 'n'
        os.environ['SEGWAY_ACCESS_KEY'] = 'k'
        os.environ['SEGWAY_API_DOMAIN'] = 'https://custom.example.com'
        try:
            _, _, domain = get_config()
            assert domain == 'https://custom.example.com'
        finally:
            if old_name is not None:
                os.environ['SEGWAY_ACCESS_NAME'] = old_name
            else:
                os.environ.pop('SEGWAY_ACCESS_NAME', None)
            if old_key is not None:
                os.environ['SEGWAY_ACCESS_KEY'] = old_key
            else:
                os.environ.pop('SEGWAY_ACCESS_KEY', None)
            if old_domain is not None:
                os.environ['SEGWAY_API_DOMAIN'] = old_domain
            else:
                os.environ.pop('SEGWAY_API_DOMAIN', None)
