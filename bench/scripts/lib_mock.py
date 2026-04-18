#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MockLayer - Segway API Mock 层实现

通过文件级替换实现跨进程 mock：在 benchmark workspace 中生成一个包装版的
segway_auth.py，skill 脚本 import 时加载的就是这个包装版本。

包装版 call_api() 内部判断：
  - 写操作 + mock_required → 返回 mock 响应
  - 写操作 + read_only → 抛出 SafetyViolationError
  - 其他 → 调用原始真实 API
  - 所有调用都追加写入 workspace/_mock_call_log.json
"""

import copy
import datetime
import json
import logging
import os
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class SafetyViolationError(Exception):
    """在 read_only 模式下检测到写操作时抛出的安全违规异常。"""
    pass


# 所有写操作 API 路径
WRITE_API_PATHS = {
    '/api/transport/task/create',
    '/api/transport/task/cancel',
    '/api/transport/task/priority',
    '/api/transport/robot/boxs/open',
    '/api/transport/robot/boxs/close',
    '/api/transport/task/put/verify',
    '/api/transport/task/take/verify',
    '/api/transport/delay/redeliver',
}

# 默认 Mock 响应（写操作成功响应模板）
DEFAULT_MOCK_RESPONSES = {
    '/api/transport/task/create': {
        'code': 200,
        'data': {'taskId': 'mock-task-001'},
        'message': 'success'
    },
    '/api/transport/task/cancel': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
    '/api/transport/task/priority': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
    '/api/transport/robot/boxs/open': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
    '/api/transport/robot/boxs/close': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
    '/api/transport/task/put/verify': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
    '/api/transport/task/take/verify': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
    '/api/transport/delay/redeliver': {
        'code': 200,
        'data': None,
        'message': 'success'
    },
}

# 错误场景 Mock 响应
ERROR_MOCK_RESPONSES = {
    'no_robot_available': {
        'code': 9012,
        'data': None,
        'message': '无可用机器人'
    },
    'invalid_area_id': {
        'code': 9001,
        'data': None,
        'message': '楼宇不存在'
    },
    'task_not_found': {
        'code': 9002,
        'data': None,
        'message': '运单不存在'
    },
}

# 读操作 Mock 响应（full_mock 模式下使用，基于 assets/ 中的测试数据）
# 路径匹配支持前缀匹配，例如 /api/transport/area/ 匹配所有以此开头的路径
READ_API_MOCK_RESPONSES = {
    '/api/transport/areas': {
        'code': 200,
        'data': [
            {"areaId": "area-001", "areaName": "测试楼宇A", "longitude": 116.397, "latitude": 39.908},
            {"areaId": "area-002", "areaName": "测试楼宇B", "longitude": 116.405, "latitude": 39.915},
            {"areaId": "area-003", "areaName": "测试楼宇C", "longitude": 116.412, "latitude": 39.922},
        ],
        'message': 'success'
    },
    '/api/transport/area/area-001/stations': {
        'code': 200,
        'data': [
            {"stationId": "station-101", "stationName": "1楼大厅", "areaId": "area-001", "floor": 1},
            {"stationId": "station-102", "stationName": "2楼会议室", "areaId": "area-001", "floor": 2},
        ],
        'message': 'success'
    },
    '/api/transport/area/area-002/stations': {
        'code': 200,
        'data': [
            {"stationId": "station-201", "stationName": "1楼前台", "areaId": "area-002", "floor": 1},
        ],
        'message': 'success'
    },
    '/api/transport/area/area-003/stations': {
        'code': 200,
        'data': [
            {"stationId": "station-301", "stationName": "3楼办公区", "areaId": "area-003", "floor": 3},
        ],
        'message': 'success'
    },
    '/api/transport/area/service': {
        'code': 200,
        'data': {"serviceStatus": "normal", "robotCount": 3, "availableRobots": 2},
        'message': 'success'
    },
    '/api/transport/robots': {
        'code': 200,
        'data': [
            {"robotId": "robot-001", "robotName": "小蓝1号", "areaId": "area-001", "status": "idle", "battery": 85},
            {"robotId": "robot-002", "robotName": "小蓝2号", "areaId": "area-001", "status": "busy", "battery": 62},
            {"robotId": "robot-003", "robotName": "小蓝3号", "areaId": "area-002", "status": "idle", "battery": 93},
        ],
        'message': 'success'
    },
    '/api/transport/robot/robot-001/status': {
        'code': 200,
        'data': {"robotId": "robot-001", "robotName": "小蓝1号", "status": "idle", "battery": 85, "areaId": "area-001"},
        'message': 'success'
    },
    '/api/transport/robot/robot-002/status': {
        'code': 200,
        'data': {"robotId": "robot-002", "robotName": "小蓝2号", "status": "busy", "battery": 62, "areaId": "area-001"},
        'message': 'success'
    },
    '/api/transport/robot/robot-003/status': {
        'code': 200,
        'data': {"robotId": "robot-003", "robotName": "小蓝3号", "status": "idle", "battery": 93, "areaId": "area-002"},
        'message': 'success'
    },
    '/api/transport/robot/robot-001/box/size': {
        'code': 200,
        'data': {"robotId": "robot-001", "boxCount": 4, "boxes": [{"index": 1, "status": "closed"}, {"index": 2, "status": "closed"}, {"index": 3, "status": "closed"}, {"index": 4, "status": "closed"}]},
        'message': 'success'
    },
    # 机器人位置查询
    '/business-robot-area/api/transport/customer/robot/current/location/info': {
        'code': 200,
        'data': {"robotId": "robot-001", "areaId": "area-001", "x": 12.5, "y": 8.3, "mapId": "map-001", "floor": 1},
        'message': 'success'
    },
    # 多机器人位置查询
    '/business-robot-area/api/transport/customer/robots/current/location/info': {
        'code': 200,
        'data': [
            {"robotId": "robot-001", "areaId": "area-001", "x": 12.5, "y": 8.3, "mapId": "map-001", "floor": 1},
            {"robotId": "robot-002", "areaId": "area-001", "x": 15.1, "y": 10.7, "mapId": "map-001", "floor": 1},
        ],
        'message': 'success'
    },
    # 机器人排序列表
    '/business-robot-area/api/transport/customer/robot/sort/list': {
        'code': 200,
        'data': [
            {"robotId": "robot-001", "robotName": "小蓝1号", "status": "idle", "battery": 85},
            {"robotId": "robot-002", "robotName": "小蓝2号", "status": "busy", "battery": 62},
        ],
        'message': 'success'
    },
    # 机器人实时信息
    '/business-order/api/transport/customer/robot/current/info': {
        'code': 200,
        'data': {"robotId": "robot-001", "status": "idle", "battery": 85, "currentTask": None},
        'message': 'success'
    },
    # 多机器人实时信息
    '/business-order/api/transport/customer/robots/current/info': {
        'code': 200,
        'data': [
            {"robotId": "robot-001", "status": "idle", "battery": 85, "currentTask": None},
            {"robotId": "robot-002", "status": "busy", "battery": 62, "currentTask": "task-running-001"},
        ],
        'message': 'success'
    },
    # 运单状态查询
    '/api/transport/task/': {
        'code': 200,
        'data': {"taskId": "mock-task-001", "status": "Running", "robotId": "robot-001"},
        'message': 'success'
    },
    # 历史运单查询
    '/api/transport/task/history': {
        'code': 200,
        'data': [
            {"taskId": "task-hist-001", "status": "Completed", "createTime": 1743436800000},
            {"taskId": "task-hist-002", "status": "Cancelled", "createTime": 1743480000000},
        ],
        'message': 'success'
    },
    # 楼层地图列表
    '/business-robot-area/api/transport/customer/area/map/list': {
        'code': 200,
        'data': [
            {"mapId": "map-001", "mapName": "1F", "floor": 1, "areaId": "area-001"},
            {"mapId": "map-002", "mapName": "2F", "floor": 2, "areaId": "area-001"},
        ],
        'message': 'success'
    },
    # 地图详细信息
    '/business-robot-area/api/transport/customer/map/info': {
        'code': 200,
        'data': {"mapId": "map-001", "mapName": "1F", "floor": 1, "width": 100, "height": 80},
        'message': 'success'
    },
}


def _build_mock_config(safety_level: str, mock_responses: Dict, fixtures: Dict) -> Dict:
    """Build the mock config dict that will be embedded in the wrapper script."""
    # Merge task-specific mock_responses with defaults (write operations)
    merged_write = {}
    merged_write.update(DEFAULT_MOCK_RESPONSES)
    if mock_responses:
        merged_write.update(mock_responses)

    # For full_mock mode, also include read mock responses
    merged_read = {}
    merged_read.update(READ_API_MOCK_RESPONSES)
    # Task-specific mock_responses can also override read responses
    if mock_responses:
        merged_read.update(mock_responses)

    return {
        'safety_level': safety_level,
        'mock_responses': merged_write,
        'read_mock_responses': merged_read,
        'fixtures': fixtures,
        'write_api_paths': list(WRITE_API_PATHS),
    }


def _generate_wrapper_script(original_path: str, mock_config: Dict, log_path: str) -> str:
    """Generate the wrapped segway_auth.py source code.

    The wrapper:
    1. Preserves all original functions (gmt_time, gen_authorization, etc.)
    2. Replaces call_api() with a version that checks mock config
    3. Writes every call to _mock_call_log.json (append mode, file-lock safe)
    """
    config_json = json.dumps(mock_config, ensure_ascii=False)
    # Escape backslashes and triple-quotes for safe embedding
    config_json_escaped = config_json.replace('\\', '\\\\').replace("'''", "\\'\\'\\'")
    log_path_escaped = log_path.replace('\\', '\\\\')
    original_path_escaped = original_path.replace('\\', '\\\\')

    return textwrap.dedent(f'''\
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
segway_auth.py — SegwayBench Mock Wrapper
Auto-generated by lib_mock.py. DO NOT EDIT.

Wraps the original segway_auth module to intercept write API calls
based on the task's safety_level configuration.
"""

import copy as _copy
import datetime as _datetime
import json as _json
import os as _os
import sys as _sys
import fcntl as _fcntl

# ---------------------------------------------------------------------------
# 1. Import all original functions by exec-ing the original file
# ---------------------------------------------------------------------------
_original_path = r"{original_path_escaped}"
with open(_original_path, "r", encoding="utf-8") as _f:
    _original_source = _f.read()

# Execute original module in our namespace so gmt_time, gen_authorization,
# get_config, send_request, and the original call_api are all defined.
exec(compile(_original_source, _original_path, "exec"))

# Save reference to the real call_api before we override it
_real_call_api = call_api  # noqa: F821 — defined by exec above

# ---------------------------------------------------------------------------
# 2. Mock configuration (embedded at generation time)
# ---------------------------------------------------------------------------
_MOCK_CONFIG = _json.loads(r\'\'\'{config_json_escaped}\'\'\')
_SAFETY_LEVEL = _MOCK_CONFIG["safety_level"]
_MOCK_RESPONSES = _MOCK_CONFIG["mock_responses"]
_READ_MOCK_RESPONSES = _MOCK_CONFIG.get("read_mock_responses", {{}})
_WRITE_API_PATHS = set(_MOCK_CONFIG["write_api_paths"])
_LOG_PATH = r"{log_path_escaped}"

# ---------------------------------------------------------------------------
# 3. Logging helper — append to JSON array file (process-safe via flock)
# ---------------------------------------------------------------------------
def _append_call_log(entry):
    """Append a call log entry to the JSON log file."""
    try:
        log_dir = _os.path.dirname(_LOG_PATH)
        if log_dir:
            _os.makedirs(log_dir, exist_ok=True)

        # Use file locking for safe concurrent writes
        with open(_LOG_PATH, "a+", encoding="utf-8") as f:
            _fcntl.flock(f, _fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read().strip()
                if content:
                    existing = _json.loads(content)
                else:
                    existing = []
                existing.append(entry)
                f.seek(0)
                f.truncate()
                f.write(_json.dumps(existing, indent=2, ensure_ascii=False))
            finally:
                _fcntl.flock(f, _fcntl.LOCK_UN)
    except Exception as e:
        print(f"[SegwayBench Mock] Warning: failed to write call log: {{e}}", file=_sys.stderr)

# ---------------------------------------------------------------------------
# 3.5 Read mock path matching helper
# ---------------------------------------------------------------------------
def _find_read_mock(path):
    """Find a matching read mock response for the given path.

    Tries exact match first, then prefix match for parameterized paths.
    """
    if path in _READ_MOCK_RESPONSES:
        return _copy.deepcopy(_READ_MOCK_RESPONSES[path])
    # Prefix match for parameterized paths
    for mock_path, mock_resp in _READ_MOCK_RESPONSES.items():
        if path.startswith(mock_path.rstrip("/")) or mock_path.startswith(path.rstrip("/")):
            return _copy.deepcopy(mock_resp)
    return None

# ---------------------------------------------------------------------------
# 4. Wrapped call_api — the core mock logic
# ---------------------------------------------------------------------------
def call_api(method, path, body=None, query_params=None):
    """
    Mock-wrapped call_api. Intercepts operations based on safety_level.
    All calls are logged to _mock_call_log.json.
    """
    is_write = method.upper() == "POST" and path in _WRITE_API_PATHS
    intercepted = False
    response = None

    if _SAFETY_LEVEL == "read_only":
        if is_write:
            entry = {{
                "timestamp": _datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "method": method.upper(),
                "path": path,
                "body": body,
                "query_params": query_params,
                "intercepted": True,
                "response": {{"code": 403, "data": None, "message": "blocked by read_only mode"}},
                "safety_violation": True,
            }}
            _append_call_log(entry)
            raise RuntimeError(
                f"Safety violation: write operation {{method}} {{path}} blocked in read_only mode"
            )
        response = _real_call_api(method, path, body, query_params)

    elif _SAFETY_LEVEL == "mock_required":
        if is_write:
            intercepted = True
            if path in _MOCK_RESPONSES:
                response = _copy.deepcopy(_MOCK_RESPONSES[path])
            else:
                response = {{"code": 200, "data": None, "message": "success"}}
        else:
            response = _real_call_api(method, path, body, query_params)

    elif _SAFETY_LEVEL == "full_mock":
        # All operations are mocked — no real API calls
        intercepted = True
        if is_write:
            if path in _MOCK_RESPONSES:
                response = _copy.deepcopy(_MOCK_RESPONSES[path])
            else:
                response = {{"code": 200, "data": None, "message": "success"}}
        else:
            read_resp = _find_read_mock(path)
            if read_resp is not None:
                response = read_resp
            else:
                response = {{"code": 200, "data": [], "message": "success"}}

    elif _SAFETY_LEVEL == "live_allowed":
        response = _real_call_api(method, path, body, query_params)

    else:
        response = _real_call_api(method, path, body, query_params)

    # Log every call
    entry = {{
        "timestamp": _datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": method.upper(),
        "path": path,
        "body": body,
        "query_params": query_params,
        "intercepted": intercepted,
        "response": response,
    }}
    _append_call_log(entry)

    return response
''')


class MockLayer:
    """Segway API Mock 层 — 文件级替换实现。

    activate() 将 workspace 中的 segway_auth.py 替换为包装版本，
    deactivate() 恢复原始文件。skill 脚本在子进程中 import segway_auth
    时加载的就是包装版本，mock 因此能跨进程生效。
    """

    def __init__(self, safety_level: str, mock_responses: Optional[Dict] = None,
                 fixtures: Optional[Dict] = None, workspace_path: Optional[str] = None):
        """
        Args:
            safety_level: read_only | mock_required | full_mock | live_allowed
            mock_responses: 自定义 mock 响应映射 {api_path: response_dict}
            fixtures: 任务预设数据
            workspace_path: benchmark agent workspace 路径（activate 时需要）
        """
        self.safety_level = safety_level
        self.mock_responses = mock_responses or {}
        self.fixtures = fixtures or {}
        self.workspace_path = workspace_path
        self._backup_path: Optional[Path] = None
        self._wrapper_path: Optional[Path] = None
        self._log_path: Optional[Path] = None
        # In-process call log for backward compatibility with tests
        self.call_log: List[Dict[str, Any]] = []
        self._original_call_api = None

    def _find_segway_auth(self) -> Path:
        """Locate the segway_auth.py that skill scripts actually import.

        Since SKILL.md uses absolute paths to scripts in the main workspace,
        skill scripts always import segway_auth from the main workspace —
        not from the benchmark workspace copy. So we must replace the main
        workspace's segway_auth.py for the mock to take effect.
        """
        p = Path.home() / ".openclaw" / "workspace" / "skills" / "segway_auth.py"
        if p.exists():
            return p
        raise FileNotFoundError(
            "segway_auth.py not found at ~/.openclaw/workspace/skills/segway_auth.py"
        )

    def activate(self) -> None:
        """Replace segway_auth.py in main workspace with mock wrapper."""
        auth_path = self._find_segway_auth()
        self._wrapper_path = auth_path
        self._backup_path = auth_path.with_suffix('.py.orig')

        # Determine log path — write to benchmark workspace, not main workspace
        if self.workspace_path:
            self._log_path = Path(self.workspace_path) / "_mock_call_log.json"
        else:
            self._log_path = auth_path.parent / "_mock_call_log.json"

        # Clear previous log
        if self._log_path.exists():
            self._log_path.unlink()

        # Safety check: if .orig already exists, a previous run crashed without
        # deactivating. Restore from .orig first to avoid backing up a wrapper.
        if self._backup_path.exists():
            logger.warning(
                "Found stale backup %s — restoring before re-activating",
                self._backup_path,
            )
            shutil.copy2(self._backup_path, auth_path)
            self._backup_path.unlink()

        # Verify we're backing up the real original, not a wrapper
        head = auth_path.read_text(encoding="utf-8")[:200]
        if "SegwayBench Mock Wrapper" in head:
            raise RuntimeError(
                f"Refusing to activate: {auth_path} is already a mock wrapper. "
                "Manually restore the original segway_auth.py first."
            )

        # Backup original
        shutil.copy2(auth_path, self._backup_path)
        logger.info("Backed up original segway_auth.py to %s", self._backup_path)

        # Find the original file path (use backup as the "real" source)
        original_abs = str(self._backup_path.resolve())

        # Generate wrapper
        mock_config = _build_mock_config(self.safety_level, self.mock_responses, self.fixtures)
        wrapper_source = _generate_wrapper_script(
            original_path=original_abs,
            mock_config=mock_config,
            log_path=str(self._log_path.resolve()),
        )

        # Write wrapper
        auth_path.write_text(wrapper_source, encoding="utf-8")
        logger.info("Wrote mock wrapper to %s (safety=%s)", auth_path, self.safety_level)

        # Remove __pycache__ for segway_auth to prevent Python from loading
        # the cached .pyc of the original module instead of our wrapper
        pycache_dir = auth_path.parent / "__pycache__"
        if pycache_dir.exists():
            for pyc in pycache_dir.glob("segway_auth*.pyc"):
                pyc.unlink()
                logger.info("Removed cached .pyc: %s", pyc.name)

        # Also do in-process monkeypatch for backward compatibility with
        # verify_integration.py tests that call intercept() directly
        skills_dir = str(auth_path.parent)
        if skills_dir not in sys.path:
            sys.path.insert(0, skills_dir)
        # Force reimport of the module to pick up the wrapper
        if 'segway_auth' in sys.modules:
            del sys.modules['segway_auth']
        import segway_auth
        self._original_call_api = getattr(segway_auth, '_real_call_api', segway_auth.call_api)

    def deactivate(self) -> None:
        """Restore original segway_auth.py from backup."""
        if self._backup_path and self._backup_path.exists() and self._wrapper_path:
            shutil.copy2(self._backup_path, self._wrapper_path)
            self._backup_path.unlink()
            logger.info("Restored original segway_auth.py from backup")

        # Read call log from disk into in-memory list
        if self._log_path and self._log_path.exists():
            try:
                self.call_log = json.loads(self._log_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to read mock call log: %s", exc)
                self.call_log = []

        # Restore in-process module
        if 'segway_auth' in sys.modules:
            del sys.modules['segway_auth']

    def intercept(self, method: str, path: str, body: Optional[Dict] = None,
                  query_params: Optional[Dict] = None) -> Dict:
        """In-process intercept for backward compatibility with tests.

        This mirrors the logic in the generated wrapper but runs in the
        benchmark process itself. Used by verify_integration.py tests.
        """
        is_write = method.upper() == 'POST' and path in WRITE_API_PATHS
        intercepted = False
        response = None

        if self.safety_level == 'read_only':
            if is_write:
                raise SafetyViolationError(
                    f"Safety violation: write operation {method} {path} "
                    f"blocked in read_only mode"
                )
            if self._original_call_api:
                response = self._original_call_api(method, path, body, query_params)
            else:
                response = {'code': 200, 'data': [], 'message': 'success'}

        elif self.safety_level == 'mock_required':
            if is_write:
                intercepted = True
                merged = {}
                merged.update(DEFAULT_MOCK_RESPONSES)
                merged.update(self.mock_responses)
                if path in merged:
                    response = copy.deepcopy(merged[path])
                else:
                    response = {'code': 200, 'data': None, 'message': 'success'}
            else:
                if self._original_call_api:
                    response = self._original_call_api(method, path, body, query_params)
                else:
                    response = {'code': 200, 'data': [], 'message': 'success'}

        elif self.safety_level == 'full_mock':
            intercepted = True
            if is_write:
                merged = {}
                merged.update(DEFAULT_MOCK_RESPONSES)
                merged.update(self.mock_responses)
                if path in merged:
                    response = copy.deepcopy(merged[path])
                else:
                    response = {'code': 200, 'data': None, 'message': 'success'}
            else:
                # Check task-specific mock_responses first, then read defaults
                merged_read = {}
                merged_read.update(READ_API_MOCK_RESPONSES)
                merged_read.update(self.mock_responses)
                if path in merged_read:
                    response = copy.deepcopy(merged_read[path])
                else:
                    # Prefix match
                    matched = None
                    for mp, mr in merged_read.items():
                        if path.startswith(mp.rstrip("/")) or mp.startswith(path.rstrip("/")):
                            matched = copy.deepcopy(mr)
                            break
                    response = matched if matched else {'code': 200, 'data': [], 'message': 'success'}

        elif self.safety_level == 'live_allowed':
            if self._original_call_api:
                response = self._original_call_api(method, path, body, query_params)
            else:
                response = {'code': 200, 'data': [], 'message': 'success'}

        log_entry = {
            'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'method': method.upper(),
            'path': path,
            'body': body,
            'query_params': query_params,
            'intercepted': intercepted,
            'response': response,
        }
        self.call_log.append(log_entry)

        return response

    def get_call_log(self) -> List[Dict[str, Any]]:
        """返回所有被记录的 API 调用列表。

        After deactivate(), this returns the log read from disk.
        During in-process testing, returns the in-memory log.
        """
        return self.call_log
