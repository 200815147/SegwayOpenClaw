#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Segway 统一输出模块
为所有 skill 脚本提供标准化的输出格式，帮助 agent 明确判断任务是否完成。

输出格式：
  成功: [TASK_COMPLETE] <中文摘要>
  失败: [TASK_FAILED] <错误描述>

agent 看到 [TASK_COMPLETE] 或 [TASK_FAILED] 后应立即停止操作，
将结果/错误信息转述给用户，不需要再调用任何 skill。
"""

import json
import sys


def print_success(data, summary=None):
    """
    输出成功结果。
    data: API 返回的 data 字段（dict/list/None）
    summary: 可选的中文摘要
    """
    if data is not None:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    if summary:
        print(f'\n[TASK_COMPLETE] {summary}')
    else:
        print('\n[TASK_COMPLETE] 操作成功，请将以上结果告知用户。')


def print_error(code, message, suggestion=None):
    """
    输出 API 错误信息。
    code: 错误码
    message: 错误消息
    suggestion: 可选的建议操作
    """
    print(f'错误码: {code}, 错误信息: {message}')
    if suggestion:
        print(f'建议: {suggestion}')
    print(f'\n[TASK_FAILED] {message}。请将此错误信息告知用户。不要用相同参数重试，如果你无法确定正确参数，请直接询问用户。')


def print_param_error(missing_params, example=None):
    """
    输出参数缺失/错误信息。专门用于帮助 agent 理解需要什么参数。
    missing_params: 缺失的参数描述（中文）
    example: 正确的调用示例
    """
    print(f'错误: 缺少必要参数: {missing_params}')
    if example:
        print(f'正确用法示例: {example}')
    print(f'\n[TASK_FAILED] 缺少参数: {missing_params}。请向用户询问这些信息，不要猜测或编造参数值。')


def print_api_failure():
    """API 请求本身失败（网络错误等）"""
    print('[TASK_FAILED] API 请求失败，可能是网络问题。请告知用户稍后重试，不要自动重试。')


def handle_result(result, success_summary=None):
    """
    统一处理 API 返回结果。
    result: call_api 返回的 dict
    success_summary: 成功时的中文摘要
    返回: True 表示成功，False 表示失败
    """
    if result is None:
        print_api_failure()
        sys.exit(1)

    code = result.get('code', result.get('resultCode'))
    if code in (200, '200'):
        data = result.get('data')
        print_success(data, success_summary)
        return True
    else:
        message = result.get('message', result.get('resultMessage', '未知错误'))
        suggestion = ERROR_SUGGESTIONS.get(code) or ERROR_SUGGESTIONS.get(str(code))
        print_error(code, message, suggestion)
        sys.exit(1)


# 常见错误码的建议操作
ERROR_SUGGESTIONS = {
    9001: '楼宇 ID 不存在，请确认后重新提供',
    '9001': '楼宇 ID 不存在，请确认后重新提供',
    9002: '运单不存在，请确认运单 ID 是否正确',
    '9002': '运单不存在，请确认运单 ID 是否正确',
    9012: '当前无可用机器人，请稍后重试或尝试其他楼宇',
    '9012': '当前无可用机器人，请稍后重试或尝试其他楼宇',
}
