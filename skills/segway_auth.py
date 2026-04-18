#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Segway API 共享认证模块
所有 Segway API skill 共享此模块，提供 HMAC-SHA256 签名认证和 HTTP 请求功能。
"""

import hashlib
import hmac
import base64
import datetime
import json
import os
import sys

import pytz
import requests
from urllib.parse import urlparse, urlencode


def gmt_time():
    """生成 GMT 格式时间字符串"""
    date_format = "%a, %d %b %Y %H:%M:%S %Z"
    gmt = pytz.timezone('GMT')
    return datetime.datetime.now(gmt).strftime(date_format)


def gen_authorization(access_name, access_key, date, url, method):
    """
    使用 HMAC-SHA256 生成 Authorization 头
    返回格式: SEGWAY {access_name}:{signature}
    """
    url_path = urlparse(url).path
    string_to_sign = method + " " + url_path + "\\n" + date
    message = bytes(string_to_sign, 'utf-8')
    secret = bytes(access_key, 'utf-8')
    signature = base64.b64encode(hmac.new(secret, message, digestmod=hashlib.sha256).digest())
    return 'SEGWAY ' + access_name + ':' + str(signature, "utf-8")


def get_config():
    """
    从环境变量读取配置
    返回: (access_name, access_key, domain)
    缺失必要变量时输出错误并终止
    """
    access_name = os.environ.get('SEGWAY_ACCESS_NAME')
    access_key = os.environ.get('SEGWAY_ACCESS_KEY')
    domain = os.environ.get('SEGWAY_API_DOMAIN', 'https://api-gate-delivery.loomo.com')

    if not access_name or not access_key:
        print("错误: 请设置环境变量 SEGWAY_ACCESS_NAME 和 SEGWAY_ACCESS_KEY")
        if not access_name:
            print("  缺少: SEGWAY_ACCESS_NAME")
        if not access_key:
            print("  缺少: SEGWAY_ACCESS_KEY")
        sys.exit(1)

    return access_name, access_key, domain


def send_request(method, url, date, authorization, body=None):
    """
    发送 HTTP 请求，支持 GET 和 POST
    POST 请求以 JSON 格式携带请求体，禁用代理
    """
    headers = {
        "Date": date,
        "Authorization": authorization,
    }

    proxies = {"http": None, "https": None}

    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, proxies=proxies)
        elif method.upper() == 'POST':
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=body, proxies=proxies)
        else:
            print(f"错误: 不支持的 HTTP 方法: {method}")
            return None

        return response.json()
    except Exception as e:
        print(f"请求发生错误: {e}")
        return None


def call_api(method, path, body=None, query_params=None):
    """
    高层封装：自动完成签名 + 请求 + 返回响应
    method: HTTP 方法 (GET/POST)
    path: API 路径 (如 /api/transport/areas)
    body: POST 请求体 (dict)
    query_params: GET 查询参数 (dict)
    """
    access_name, access_key, domain = get_config()

    url = domain + path
    if query_params:
        url = url + '?' + urlencode(query_params)

    date = gmt_time()
    authorization = gen_authorization(access_name, access_key, date, url, method.upper())

    return send_request(method.upper(), url, date, authorization, body)
