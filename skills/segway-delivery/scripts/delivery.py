#!/root/miniconda3/envs/openclaw/bin/python3
# -*- coding: utf-8 -*-
"""
Segway 一站式配送编排脚本
自动完成 楼宇查询 → 站点匹配 → 运力检查 → 运单创建 的全流程。
用户只需提供楼宇名称和站点名称，无需手动查询 ID。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import segway_auth
import segway_resolve
import segway_output
import segway_confirm


def resolve_area(area_name):
    """通过名称查找楼宇，返回 area dict 或退出"""
    result = segway_auth.call_api('GET', '/api/transport/areas')
    if not result or result.get('code') not in (200, '200'):
        msg = result.get('message', '未知错误') if result else 'API 请求失败'
        print(f'查询楼宇列表失败: {msg}')
        sys.exit(1)

    areas = result.get('data', [])
    if not areas:
        print('当前没有可用的楼宇')
        sys.exit(1)

    matched, names = segway_resolve.fuzzy_match(area_name, areas, 'areaName')
    if matched:
        return matched

    if names and len(names) <= 10:
        print(f'未找到楼宇 "{area_name}"，可用楼宇: {", ".join(names)}')
    else:
        print(f'未找到楼宇 "{area_name}"')
    sys.exit(1)


def resolve_station(area_id, station_name, area_name=''):
    """通过名称查找站点，返回 station dict 或退出"""
    result = segway_auth.call_api('GET', f'/api/transport/area/{area_id}/stations')
    if not result or result.get('code') not in (200, '200'):
        msg = result.get('message', '未知错误') if result else 'API 请求失败'
        print(f'查询站点列表失败: {msg}')
        sys.exit(1)

    stations = result.get('data', [])
    if not stations:
        print(f'楼宇 "{area_name}" 下没有可用站点')
        sys.exit(1)

    matched, names = segway_resolve.fuzzy_match(station_name, stations, 'stationName')
    if matched:
        return matched

    if names and len(names) <= 20:
        print(f'未找到站点 "{station_name}"，可用站点: {", ".join(names)}')
    else:
        print(f'未找到站点 "{station_name}"')
    sys.exit(1)


def check_service(area_id, area_name=''):
    """检查楼宇运力状态"""
    result = segway_auth.call_api('GET', '/api/transport/area/service',
                                  query_params={'areaId': area_id})
    if not result or result.get('code') not in (200, '200'):
        # 运力检查失败不阻断，只警告
        print(f'警告: 无法检查楼宇 "{area_name}" 的运力状态，继续尝试创建运单')
        return None
    return result.get('data')


def create_task(body):
    """创建运单并输出结果"""
    result = segway_auth.call_api('POST', '/api/transport/task/create', body=body)
    if not result:
        print('错误: 创建运单请求失败')
        sys.exit(1)

    code = result.get('code', result.get('resultCode'))
    if code in (200, '200'):
        data = result.get('data')
        if data:
            task_id = data.get('taskId', '')
            print(f'运单创建成功！运单 ID: {task_id}')
            if body.get('callbackUrl'):
                print(f'回调 URL: {body["callbackUrl"]}（状态变更将自动推送）')
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print('运单创建成功')
    else:
        message = result.get('message', result.get('resultMessage', '未知错误'))
        print(f'运单创建失败 - 错误码: {code}, 错误信息: {message}')
        if code in (9012, '9012'):
            print('建议: 当前无可用机器人，请稍后重试或尝试其他楼宇')
        sys.exit(1)


def get_default_callback_url(port=18800):
    """尝试获取 webhook 服务的回调 URL"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return f'http://{ip}:{port}/callback'
    except Exception:
        return None


def inject_callback_url(body, args):
    """如果用户没有禁用回调，自动注入 callbackUrl"""
    if getattr(args, 'no_callback', False):
        return
    callback_url = getattr(args, 'callback_url', None)
    if callback_url:
        body['callbackUrl'] = callback_url
        return
    # 尝试自动检测 webhook 服务
    auto_url = get_default_callback_url()
    if auto_url:
        # 检查 webhook 服务是否在运行
        webhook_pid = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   '..', 'segway-webhook', 'data', 'webhook.pid')
        if os.path.exists(webhook_pid):
            try:
                pid = int(open(webhook_pid).read().strip())
                os.kill(pid, 0)  # 检查进程存在
                body['callbackUrl'] = auto_url
                print(f'  ℹ 已自动设置回调 URL: {auto_url}')
            except (ProcessLookupError, ValueError, FileNotFoundError):
                pass


def cmd_guidance(args):
    """引领配送：查楼宇 → 查站点 → 检查运力 → 创建引领运单"""
    print(f'[1/4] 查询楼宇 "{args.area_name}" ...')
    area = resolve_area(args.area_name)
    area_id = area['areaId']
    area_name = area.get('areaName', args.area_name)
    print(f'  ✓ 找到楼宇: {area_name} (ID: {area_id})')

    print(f'[2/4] 查询站点 "{args.station_name}" ...')
    station = resolve_station(area_id, args.station_name, area_name)
    station_id = station['stationId']
    station_name = station.get('stationName', args.station_name)
    print(f'  ✓ 找到站点: {station_name} (ID: {station_id})')

    print(f'[3/4] 检查运力状态 ...')
    service = check_service(area_id, area_name)
    if service:
        print(f'  ✓ 运力状态正常')

    print(f'[4/4] 创建引领运单 ...')
    body = {
        'areaId': area_id,
        'taskType': 'Guidance',
        'stationId': station_id,
    }
    if args.priority_level is not None:
        body['priorityLevel'] = args.priority_level
    if args.remark:
        body['remark'] = args.remark
    inject_callback_url(body, args)

    # dry-run / confirm 门控
    action_name = 'delivery.guidance'
    if args.dry_run:
        segway_confirm.cleanup_expired_tokens()
        token = segway_confirm.generate_token(action_name, body)
        print(f'\n=== 操作预览（dry-run）===')
        print(f'操作: 引领配送')
        print(f'楼宇: {area_name} (ID: {area_id})')
        print(f'站点: {station_name} (ID: {station_id})')
        print(f'请求体:')
        print(json.dumps(body, ensure_ascii=False, indent=2))
        print(f'\n确认 token: {token}')
        print(f'\n[ACTION_PENDING] 请将以上操作摘要展示给用户确认。用户确认后，使用相同参数加 --confirm {token} 执行。')
        return

    if not args.confirm:
        print(f'\n[TASK_FAILED] 安全机制：写操作必须经过 dry-run + confirm 两步确认。请先加 --dry-run 参数运行。')
        sys.exit(1)

    valid, err = segway_confirm.verify_token(args.confirm, action_name, body)
    if not valid:
        print(f'错误: confirm token 验证失败 - {err}')
        print(f'\n[TASK_FAILED] token 验证失败: {err}。请重新用 --dry-run 生成新的 token。')
        sys.exit(1)

    create_task(body)
    print(f'\n[TASK_COMPLETE] 引领运单已下发，机器人将前往 {area_name} 的 {station_name}')


def cmd_take_deliver(args):
    """取送配送：查楼宇 → 查取件站点 → 查送件站点 → 检查运力 → 创建取送运单"""
    print(f'[1/5] 查询楼宇 "{args.area_name}" ...')
    area = resolve_area(args.area_name)
    area_id = area['areaId']
    area_name = area.get('areaName', args.area_name)
    print(f'  ✓ 找到楼宇: {area_name} (ID: {area_id})')

    print(f'[2/5] 查询取件站点 "{args.take_station_name}" ...')
    take_station = resolve_station(area_id, args.take_station_name, area_name)
    take_station_id = take_station['stationId']
    take_name = take_station.get('stationName', args.take_station_name)
    print(f'  ✓ 找到取件站点: {take_name} (ID: {take_station_id})')

    print(f'[3/5] 查询送件站点 "{args.deliver_station_name}" ...')
    deliver_station = resolve_station(area_id, args.deliver_station_name, area_name)
    deliver_station_id = deliver_station['stationId']
    deliver_name = deliver_station.get('stationName', args.deliver_station_name)
    print(f'  ✓ 找到送件站点: {deliver_name} (ID: {deliver_station_id})')

    print(f'[4/5] 检查运力状态 ...')
    service = check_service(area_id, area_name)
    if service:
        print(f'  ✓ 运力状态正常')

    print(f'[5/5] 创建取送运单 ...')
    take_pair = {
        'stationId': take_station_id,
        'openCode': args.take_open_code,
        'action': 'TAKE',
    }
    deliver_pair = {
        'stationId': deliver_station_id,
        'action': 'DELIVER',
    }
    if args.verify:
        deliver_pair['verify'] = True
    if args.deliver_open_code:
        deliver_pair['openCode'] = args.deliver_open_code

    body = {
        'areaId': area_id,
        'taskType': 'TakeAndDeliver',
        'stationPairList': [take_pair, deliver_pair],
    }
    if args.priority_level is not None:
        body['priorityLevel'] = args.priority_level
    if args.remark:
        body['remark'] = args.remark
    inject_callback_url(body, args)

    # dry-run / confirm 门控
    action_name = 'delivery.take-deliver'
    if args.dry_run:
        segway_confirm.cleanup_expired_tokens()
        token = segway_confirm.generate_token(action_name, body)
        print(f'\n=== 操作预览（dry-run）===')
        print(f'操作: 取送配送')
        print(f'楼宇: {area_name} (ID: {area_id})')
        print(f'取件站点: {take_name} (ID: {take_station_id})')
        print(f'送件站点: {deliver_name} (ID: {deliver_station_id})')
        print(f'请求体:')
        print(json.dumps(body, ensure_ascii=False, indent=2))
        print(f'\n确认 token: {token}')
        print(f'\n[ACTION_PENDING] 请将以上操作摘要展示给用户确认。用户确认后，使用相同参数加 --confirm {token} 执行。')
        return

    if not args.confirm:
        print(f'\n[TASK_FAILED] 安全机制：写操作必须经过 dry-run + confirm 两步确认。请先加 --dry-run 参数运行。')
        sys.exit(1)

    valid, err = segway_confirm.verify_token(args.confirm, action_name, body)
    if not valid:
        print(f'错误: confirm token 验证失败 - {err}')
        print(f'\n[TASK_FAILED] token 验证失败: {err}。请重新用 --dry-run 生成新的 token。')
        sys.exit(1)

    create_task(body)
    print(f'\n[TASK_COMPLETE] 取送运单已下发，机器人将从 {take_name} 取件后送往 {deliver_name}')


def cmd_status(args):
    """配送状态总览：查楼宇 → 查运力 → 查站点 → 查机器人"""
    print(f'查询楼宇 "{args.area_name}" 的配送状态 ...\n')
    area = resolve_area(args.area_name)
    area_id = area['areaId']
    area_name = area.get('areaName', args.area_name)

    # 运力状态
    service = check_service(area_id, area_name)
    if service:
        print(f'【运力状态】')
        print(json.dumps(service, ensure_ascii=False, indent=2))
        print()

    # 站点列表
    stations_result = segway_auth.call_api('GET', f'/api/transport/area/{area_id}/stations')
    if stations_result and stations_result.get('code') in (200, '200'):
        stations = stations_result.get('data', [])
        print(f'【站点列表】共 {len(stations)} 个站点')
        for s in stations:
            print(f'  - {s.get("stationName", "未知")} (ID: {s.get("stationId", "")})')
        print()

    # 机器人列表
    robots_result = segway_auth.call_api('GET',
                                         '/business-robot-area/api/transport/customer/robot/sort/list',
                                         query_params={'areaId': area_id})
    if robots_result and robots_result.get('code') in (200, '200'):
        robots = robots_result.get('data', [])
        print(f'【机器人列表】共 {len(robots)} 台')
        for r in robots:
            name = r.get('robotNickName', r.get('robotId', '未知'))
            status = r.get('robotStatus', '未知')
            print(f'  - {name}: {status}')


def cmd_list_areas(args):
    """列出所有可用楼宇"""
    result = segway_auth.call_api('GET', '/api/transport/areas')
    if not result or result.get('code') not in (200, '200'):
        msg = result.get('message', '未知错误') if result else 'API 请求失败'
        print(f'查询楼宇列表失败: {msg}')
        sys.exit(1)

    areas = result.get('data', [])
    if not areas:
        print('当前没有可用的楼宇')
        return

    print(f'共 {len(areas)} 个可用楼宇:\n')
    for a in areas:
        name = a.get('areaName', '未知')
        aid = a.get('areaId', '')
        lat = a.get('latitude', '')
        lng = a.get('longitude', '')
        print(f'  - {name} (ID: {aid}, 坐标: {lat},{lng})')


def main():
    parser = argparse.ArgumentParser(description='Segway 一站式配送编排')
    parser.add_argument('action', choices=['guidance', 'take-deliver', 'status', 'list-areas'],
                        help='操作类型')
    # 通用参数
    parser.add_argument('--area-name', help='楼宇名称（支持模糊匹配）')
    parser.add_argument('--station-name', help='目标站点名称（引领配送用）')
    parser.add_argument('--priority-level', type=int, help='优先级 (40-60)')
    parser.add_argument('--remark', help='备注')
    parser.add_argument('--callback-url', help='运单状态回调 URL（不指定时自动使用 webhook 服务地址）')
    parser.add_argument('--no-callback', action='store_true', help='不设置回调 URL')
    # 取送配送参数
    parser.add_argument('--take-station-name', help='取件站点名称')
    parser.add_argument('--take-open-code', help='取件开箱码')
    parser.add_argument('--deliver-station-name', help='送件站点名称')
    parser.add_argument('--deliver-open-code', help='送件开箱码')
    parser.add_argument('--verify', action='store_true', help='送件是否需要验证')
    parser.add_argument('--dry-run', action='store_true', help='仅验证参数并生成确认 token，不真正执行')
    parser.add_argument('--confirm', help='确认 token（由 --dry-run 生成）')

    args = parser.parse_args()

    if args.action == 'guidance':
        if not args.area_name or not args.station_name:
            print('错误: guidance 操作需要 --area-name 和 --station-name 参数')
            sys.exit(1)
        cmd_guidance(args)

    elif args.action == 'take-deliver':
        if not args.area_name or not args.take_station_name or not args.take_open_code or not args.deliver_station_name:
            print('错误: take-deliver 操作需要 --area-name、--take-station-name、--take-open-code 和 --deliver-station-name 参数')
            sys.exit(1)
        cmd_take_deliver(args)

    elif args.action == 'status':
        if not args.area_name:
            print('错误: status 操作需要 --area-name 参数')
            sys.exit(1)
        cmd_status(args)

    elif args.action == 'list-areas':
        cmd_list_areas(args)


if __name__ == '__main__':
    main()
