#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Segway 写操作确认模块
为所有写操作提供 dry-run + confirm token 两阶段执行机制。

流程：
1. 脚本以 --dry-run 模式运行，验证参数，输出操作摘要和 confirm token
2. 用户确认后，脚本以 --confirm <token> 模式运行，验证 token 后真正执行
3. token 基于操作参数 hash + 时间戳生成，5 分钟内有效，一次性使用

模型无法绕过此机制：
- 没有 --dry-run 也没有 --confirm 时，脚本拒绝执行写操作
- 编造的 token 无法通过验证
- 过期的 token 无法使用
- 已使用的 token 无法重放
"""

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

# Token 有效期（秒）
TOKEN_TTL = 300  # 5 分钟

# Token 存储目录
TOKEN_DIR = Path(__file__).parent / '.confirm_tokens'

# 签名密钥（基于机器特征，不需要保密，只需要不可猜测）
def _get_secret():
    machine_id = os.environ.get('HOSTNAME', '') + os.path.abspath(__file__)
    return hashlib.sha256(machine_id.encode()).hexdigest()[:32]


def generate_token(action, params_dict):
    """
    生成 confirm token。
    action: 操作名称（如 'task_create.guidance'）
    params_dict: 操作参数（会被序列化为 JSON 用于签名）
    返回: token 字符串
    """
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time())
    params_json = json.dumps(params_dict, sort_keys=True, ensure_ascii=False)
    
    # 签名 = HMAC(secret, action + params + timestamp)
    payload = f'{action}|{params_json}|{timestamp}'
    sig = hmac.new(
        _get_secret().encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    token = f'{timestamp}:{sig}'
    
    # 保存 token 元数据（用于验证时比对参数）
    token_file = TOKEN_DIR / f'{sig}.json'
    token_file.write_text(json.dumps({
        'action': action,
        'params': params_dict,
        'timestamp': timestamp,
        'used': False,
    }, ensure_ascii=False, indent=2))
    
    return token


def verify_token(token, action, params_dict):
    """
    验证 confirm token。
    返回: (valid: bool, error_message: str)
    """
    if not token or ':' not in token:
        return False, 'token 格式无效'
    
    try:
        timestamp_str, sig = token.split(':', 1)
        timestamp = int(timestamp_str)
    except (ValueError, IndexError):
        return False, 'token 格式无效'
    
    # 检查过期
    now = int(time.time())
    if now - timestamp > TOKEN_TTL:
        return False, f'token 已过期（有效期 {TOKEN_TTL} 秒）'
    
    # 检查签名
    params_json = json.dumps(params_dict, sort_keys=True, ensure_ascii=False)
    payload = f'{action}|{params_json}|{timestamp}'
    expected_sig = hmac.new(
        _get_secret().encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    if not hmac.compare_digest(sig, expected_sig):
        return False, 'token 签名不匹配（参数可能已变更）'
    
    # 检查是否已使用
    token_file = TOKEN_DIR / f'{sig}.json'
    if token_file.exists():
        meta = json.loads(token_file.read_text())
        if meta.get('used'):
            return False, 'token 已被使用，不可重放'
        # 标记为已使用
        meta['used'] = True
        meta['used_at'] = now
        token_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    
    return True, ''


def cleanup_expired_tokens():
    """清理过期的 token 文件"""
    if not TOKEN_DIR.exists():
        return
    now = int(time.time())
    for f in TOKEN_DIR.glob('*.json'):
        try:
            meta = json.loads(f.read_text())
            if now - meta.get('timestamp', 0) > TOKEN_TTL * 2:
                f.unlink()
        except (json.JSONDecodeError, KeyError):
            f.unlink()
