"""桌面壳运行时：路径、配置读写、QMT 探测、API 进程、开机启动。"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_NAME = "QMT Bridge"
LOCK_NAME = "qmt-bridge-desktop.lock"
PID_NAME = "qmt-server.pid"
PANEL_URL_NAME = "panel.url"
ENV_NAME = ".env"
DESKTOP_NAME = "desktop.json"

CREATE_NO_WINDOW = 0x08000000
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def app_data_dir() -> Path:
    """用户配置目录：``%APPDATA%\\QMT Bridge``。"""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    return path


def env_path() -> Path:
    return app_data_dir() / ENV_NAME


def desktop_prefs_path() -> Path:
    return app_data_dir() / DESKTOP_NAME


def log_dir() -> Path:
    return app_data_dir() / "logs"


def server_log_path() -> Path:
    return log_dir() / "qmt-server.log"


def pid_path() -> Path:
    return app_data_dir() / PID_NAME


def panel_url_path() -> Path:
    return app_data_dir() / PANEL_URL_NAME


def lock_path() -> Path:
    return app_data_dir() / LOCK_NAME


def install_root() -> Path | None:
    """打包安装根目录（含 QMTBridge.exe 与 runtime\\）。开发模式返回 None。"""
    exe = Path(sys.executable).resolve()
    # <root>/runtime/pythonw.exe
    candidate = exe.parent.parent / "QMTBridge.exe"
    if candidate.is_file():
        return candidate.parent
    bundled = Path(sys.argv[0]).resolve().parent / "QMTBridge.exe"
    if bundled.is_file():
        return bundled.parent
    return None


def python_executable(*, windowed: bool = False) -> Path:
    """当前运行时的 python.exe / pythonw.exe。"""
    exe = Path(sys.executable).resolve()
    if windowed:
        alt = exe.with_name("pythonw.exe")
        if alt.is_file():
            return alt
        return exe
    alt = exe.with_name("python.exe")
    if exe.name.lower() == "pythonw.exe" and alt.is_file():
        return alt
    return exe


def default_config() -> dict:
    return {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info",
        "api_key": "",
        "require_auth_for_data": False,
        "trading_enabled": False,
        "mini_qmt_path": "",
        "stock_account_id": "",
        "credit_account_id": "",
        "default_account": "stock",
        "autostart": False,
        "start_on_launch": False,
    }


def _parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    text = path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        data[key.strip()] = val.strip().strip("'").strip('"')
    return data


def _as_bool(val: str | bool | None, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None or val == "":
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def load_desktop_prefs() -> dict:
    path = desktop_prefs_path()
    # 已有 .env 的旧安装视为已完成首次配置
    legacy_done = env_path().is_file()
    defaults = {
        "autostart": False,
        "start_on_launch": False,
        "setup_complete": legacy_done,
    }
    if not path.is_file():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    return {
        "autostart": bool(data.get("autostart", False)),
        "start_on_launch": bool(data.get("start_on_launch", False)),
        "setup_complete": bool(data.get("setup_complete", legacy_done)),
    }


def save_desktop_prefs(prefs: dict) -> None:
    current = load_desktop_prefs()
    desktop_prefs_path().write_text(
        json.dumps(
            {
                "autostart": bool(prefs.get("autostart", False)),
                "start_on_launch": bool(prefs.get("start_on_launch", False)),
                "setup_complete": bool(
                    prefs.get("setup_complete", current.get("setup_complete", False))
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def missing_required_config(cfg: dict | None = None) -> list[str]:
    """返回缺失的必填配置项（用于首次编辑态）。"""
    cfg = cfg or load_config()
    missing: list[str] = []
    try:
        port = int(cfg.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    if port < 1 or port > 65535:
        missing.append("端口")
    if cfg.get("trading_enabled"):
        if not str(cfg.get("mini_qmt_path") or "").strip():
            missing.append("miniQMT 路径")
        has_stock = bool(str(cfg.get("stock_account_id") or "").strip())
        has_credit = bool(str(cfg.get("credit_account_id") or "").strip())
        if not has_stock and not has_credit:
            missing.append("交易账户")
    return missing


def needs_setup(cfg: dict | None = None) -> bool:
    """首次尚未完成配置，或仍缺少必填项时进入编辑态。"""
    cfg = cfg or load_config()
    prefs = load_desktop_prefs()
    if not prefs.get("setup_complete"):
        return True
    return bool(missing_required_config(cfg))


def load_config() -> dict:
    cfg = default_config()
    env = _parse_env_file(env_path())
    if "QMT_BRIDGE_HOST" in env:
        cfg["host"] = env["QMT_BRIDGE_HOST"] or "0.0.0.0"
    if "QMT_BRIDGE_PORT" in env:
        try:
            cfg["port"] = int(env["QMT_BRIDGE_PORT"])
        except ValueError:
            pass
    if "QMT_BRIDGE_LOG_LEVEL" in env:
        cfg["log_level"] = env["QMT_BRIDGE_LOG_LEVEL"] or "info"
    if "QMT_BRIDGE_API_KEY" in env:
        cfg["api_key"] = env["QMT_BRIDGE_API_KEY"]
    cfg["require_auth_for_data"] = _as_bool(env.get("QMT_BRIDGE_REQUIRE_AUTH_FOR_DATA"))
    cfg["trading_enabled"] = _as_bool(env.get("QMT_BRIDGE_TRADING_ENABLED"))
    if "QMT_BRIDGE_MINI_QMT_PATH" in env:
        cfg["mini_qmt_path"] = env["QMT_BRIDGE_MINI_QMT_PATH"]
    if "QMT_BRIDGE_STOCK_ACCOUNT_ID" in env:
        cfg["stock_account_id"] = env["QMT_BRIDGE_STOCK_ACCOUNT_ID"]
    if "QMT_BRIDGE_CREDIT_ACCOUNT_ID" in env:
        cfg["credit_account_id"] = env["QMT_BRIDGE_CREDIT_ACCOUNT_ID"]
    if "QMT_BRIDGE_DEFAULT_ACCOUNT" in env:
        acct = env["QMT_BRIDGE_DEFAULT_ACCOUNT"].lower()
        cfg["default_account"] = acct if acct in ("stock", "credit") else "stock"
    prefs = load_desktop_prefs()
    cfg["autostart"] = prefs["autostart"]
    cfg["start_on_launch"] = prefs["start_on_launch"]
    cfg["setup_complete"] = prefs["setup_complete"]
    if not cfg["mini_qmt_path"]:
        detected = detect_qmt()
        if detected.get("userdata_mini"):
            cfg["mini_qmt_path"] = detected["userdata_mini"]
    return cfg


def save_config(cfg: dict) -> dict:
    """把控制面板配置写入 ``config.env``，并同步开机启动项。"""
    merged = default_config()
    merged.update(cfg)
    try:
        merged["port"] = int(merged.get("port") or 8000)
    except (TypeError, ValueError):
        merged["port"] = 8000
    if merged["port"] < 1 or merged["port"] > 65535:
        raise ValueError("端口需在 1–65535 之间")
    acct = str(merged.get("default_account") or "stock").lower()
    merged["default_account"] = acct if acct in ("stock", "credit") else "stock"
    trading = _as_bool(merged.get("trading_enabled"))
    merged["trading_enabled"] = trading
    merged["require_auth_for_data"] = _as_bool(merged.get("require_auth_for_data"))
    merged["autostart"] = _as_bool(merged.get("autostart"))
    merged["start_on_launch"] = _as_bool(merged.get("start_on_launch"))
    # 仅在面板显式传入时更新；静默保存字段不误标「首次配置完成」
    if "setup_complete" in cfg:
        merged["setup_complete"] = _as_bool(cfg.get("setup_complete"))
    else:
        merged["setup_complete"] = bool(load_desktop_prefs().get("setup_complete", False))

    lines = [
        "# QMT Bridge 桌面配置（由控制面板写入，请勿与仓库 .env 混淆）",
        f"QMT_BRIDGE_HOST={merged.get('host') or '0.0.0.0'}",
        f"QMT_BRIDGE_PORT={merged['port']}",
        f"QMT_BRIDGE_LOG_LEVEL={merged.get('log_level') or 'info'}",
        "QMT_BRIDGE_WORKERS=1",
        f"QMT_BRIDGE_API_KEY={merged.get('api_key') or ''}",
        f"QMT_BRIDGE_REQUIRE_AUTH_FOR_DATA={'true' if merged['require_auth_for_data'] else 'false'}",
        f"QMT_BRIDGE_TRADING_ENABLED={'true' if trading else 'false'}",
        f"QMT_BRIDGE_MINI_QMT_PATH={merged.get('mini_qmt_path') or ''}",
        f"QMT_BRIDGE_STOCK_ACCOUNT_ID={merged.get('stock_account_id') or ''}",
        f"QMT_BRIDGE_CREDIT_ACCOUNT_ID={merged.get('credit_account_id') or ''}",
        f"QMT_BRIDGE_DEFAULT_ACCOUNT={merged['default_account']}",
        "",
    ]
    env_path().write_text("\n".join(lines), encoding="utf-8")
    save_desktop_prefs(
        {
            "autostart": merged["autostart"],
            "start_on_launch": merged["start_on_launch"],
            "setup_complete": merged.get("setup_complete", True),
        }
    )
    set_autostart(merged["autostart"])
    return load_config()


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.3)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return "127.0.0.1"


_qmt_homes_cache: list[Path] | None = None
_qmt_detect_cache: tuple[float, dict] | None = None


def _win_drive_letters() -> list[str]:
    if sys.platform != "win32":
        return []
    import ctypes

    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    get_type = ctypes.windll.kernel32.GetDriveTypeW
    letters = []
    for i in range(26):
        if bitmask & (1 << i):
            letter = chr(ord("A") + i)
            # 3=固定磁盘，避免扫描光驱 / 网络盘卡住
            if get_type(f"{letter}:\\") == 3:
                letters.append(letter)
    return letters


def _looks_like_qmt_home(path: Path) -> bool:
    if (path / "userdata_mini").is_dir():
        return True
    for name in ("XtMiniQmt.exe", "XtItClient.exe", "miniqmt.exe"):
        if (path / name).is_file() or (path / "bin.x64" / name).is_file():
            return True
    return False


def _qmt_running() -> bool:
    if sys.platform != "win32":
        return False
    try:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    text = (completed.stdout or "").lower()
    return any(
        name in text for name in ("xtminiqmt.exe", "miniquote.exe", "xtitclient.exe")
    )


def _iter_candidate_qmt_homes() -> list[Path]:
    global _qmt_homes_cache
    if _qmt_homes_cache is not None:
        return _qmt_homes_cache

    homes: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            return
        key = str(resolved).lower()
        if key in seen:
            return
        seen.add(key)
        homes.append(resolved)

    extra = os.environ.get("QMT_BRIDGE_QMT_HOME", "")
    if extra:
        add(Path(extra))

    program_dirs = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("LOCALAPPDATA", "")),
    ]
    for drive in _win_drive_letters():
        program_dirs.append(Path(f"{drive}:/"))

    keywords = ("qmt", "迅投", "miniqmt", "国金", "中航", "华泰", "银河", "广发")
    for root in program_dirs:
        if not root or not root.is_dir():
            continue
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir():
                continue
            name = entry.name.lower()
            if any(k in name for k in keywords):
                add(entry)

    _qmt_homes_cache = homes
    return homes


def detect_qmt() -> dict:
    """探测 miniQMT 安装路径与是否在运行。"""
    global _qmt_detect_cache
    now = time.time()
    if _qmt_detect_cache and now - _qmt_detect_cache[0] < 5:
        return _qmt_detect_cache[1]

    homes = [p for p in _iter_candidate_qmt_homes() if _looks_like_qmt_home(p)]
    userdata = ""
    home = ""
    if homes:
        home = str(homes[0])
        mini = homes[0] / "userdata_mini"
        userdata = str(mini) if mini.is_dir() else home
    running_paths = _qmt_running()
    result = {
        "found": bool(home),
        "home": home,
        "userdata_mini": userdata,
        "running": running_paths,
    }
    _qmt_detect_cache = (now, result)
    return result


def find_xtquant_site_packages() -> list[str]:
    """返回包含 ``xtquant`` 包的目录，供 PYTHONPATH / .pth 注入。

    只做文件系统探测，避免在桌面进程里 ``import xtquant``
    （C 扩展异常会拖垮控制面板）。
    仅返回与当前 CPython 版本兼容的目录，避免 QMT 旧包盖住 pip 新包。
    """
    found: list[str] = []
    rels = (
        Path("bin.x64") / "Lib" / "site-packages",
        Path("bin") / "Lib" / "site-packages",
        Path("python") / "Lib" / "site-packages",
        Path("Lib") / "site-packages",
        Path("pypi"),
        Path("."),
    )

    homes: list[Path] = list(_iter_candidate_qmt_homes())
    # 优先纳入用户配置的 miniQMT 路径（及其上级安装目录）
    try:
        configured = str(load_config().get("mini_qmt_path") or "").strip()
    except Exception:
        configured = ""
    if configured:
        cfg_path = Path(configured)
        homes.insert(0, cfg_path)
        if cfg_path.name.lower() == "userdata_mini":
            homes.insert(0, cfg_path.parent)
        elif (cfg_path / "userdata_mini").is_dir():
            homes.insert(0, cfg_path)

    for home in homes:
        for rel in rels:
            try:
                site = (home / rel).resolve()
            except OSError:
                continue
            xt_dir = site / "xtquant"
            if xt_dir.is_dir() and _xtquant_dir_compatible(xt_dir):
                found.append(str(site))
            elif (site / "xtquant.py").is_file():
                found.append(str(site))
    runtime_site = Path(sys.executable).resolve().parent / "Lib" / "site-packages"
    runtime_xt = runtime_site / "xtquant"
    if runtime_xt.is_dir() and _xtquant_dir_compatible(runtime_xt):
        found.insert(0, str(runtime_site))
    uniq: list[str] = []
    seen: set[str] = set()
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(item)
    return uniq


def _xtquant_dir_compatible(xt_dir: Path) -> bool:
    """判断 xtquant 目录是否适配当前解释器（按扩展后缀匹配 .pyd）。"""
    try:
        import sysconfig

        ext = sysconfig.get_config_var("EXT_SUFFIX") or ""
    except Exception:
        ext = ""
    if not xt_dir.is_dir():
        return False
    # 新版 pip xtquant：xtpythonclient / datacenter
    if ext and (
        list(xt_dir.glob(f"xtpythonclient*{ext}"))
        or list(xt_dir.glob(f"datacenter*{ext}"))
    ):
        return True
    # 旧版 QMT 自带：IPythonApiClient
    if ext and list(xt_dir.glob(f"IPythonApiClient*{ext}")):
        return True
    # 仅有其它 Python 版本的旧版 .pyd → 不兼容（强行注入会盖住可用的 pip 包）
    if list(xt_dir.glob("IPythonApiClient*.pyd")):
        return False
    if list(xt_dir.glob("xtpythonclient*.pyd")) or list(
        xt_dir.glob("datacenter*.pyd")
    ):
        return False
    return (xt_dir / "xtdata.py").is_file()


def _xtquant_already_usable() -> bool:
    """当前 sys.path 上是否已有可用的 xtquant（不主动 import C 扩展）。"""
    try:
        import importlib.util

        spec = importlib.util.find_spec("xtquant")
    except (ImportError, ModuleNotFoundError, ValueError):
        return False
    if spec is None or not spec.origin:
        return False
    return _xtquant_dir_compatible(Path(spec.origin).resolve().parent)


def _is_embeddable_runtime() -> bool:
    """嵌入式发行版旁有 ``python*._pth``，系统/Anaconda Python 通常没有。"""
    root = Path(sys.executable).resolve().parent
    return any(root.glob("python*._pth"))


def runtime_site_packages() -> Path:
    return Path(sys.executable).resolve().parent / "Lib" / "site-packages"


def write_xtquant_pth(sites: list[str] | None = None) -> Path | None:
    """把 xtquant 路径写入嵌入式运行时的 ``.pth``。

    嵌入式 Python 的 ``python*._pth`` 会忽略 ``PYTHONPATH``，
    必须通过 ``site-packages/*.pth``（需 ``import site``）注入。
    对系统 Python / Anaconda **不写** .pth，避免污染全局环境。
    """
    if not _is_embeddable_runtime():
        return None
    sites = sites if sites is not None else find_xtquant_site_packages()
    site_dir = runtime_site_packages()
    pth = site_dir / "qmt_bridge_xtquant.pth"
    if not sites:
        try:
            pth.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    try:
        site_dir.mkdir(parents=True, exist_ok=True)
        pth.write_text("\n".join(sites) + "\n", encoding="utf-8")
    except OSError:
        return None
    return pth


def ensure_xtquant_on_path() -> None:
    """仅在当前环境缺少可用 xtquant 时，注入兼容的 QMT/运行时路径。"""
    if _xtquant_already_usable():
        return
    sites = find_xtquant_site_packages()
    write_xtquant_pth(sites)
    for site in sites:
        if site not in sys.path:
            sys.path.insert(0, site)
        current = os.environ.get("PYTHONPATH", "")
        parts = current.split(os.pathsep) if current else []
        if site not in parts:
            os.environ["PYTHONPATH"] = (
                os.pathsep.join([site, *parts]) if parts else site
            )


def xtquant_status() -> dict:
    """桌面进程不 import xtquant，只检查安装位置是否存在。"""
    if _xtquant_already_usable():
        return {"ok": True, "version": "可用"}
    sites = find_xtquant_site_packages()
    if sites:
        return {"ok": True, "version": "已检测到"}
    return {"ok": False, "version": "", "error": "未找到与当前 Python 兼容的 xtquant"}


def health_url(port: int) -> str:
    return f"http://127.0.0.1:{int(port)}/api/meta/health"


def is_server_healthy(port: int, timeout: float = 1.2) -> bool:
    try:
        with _NO_PROXY.open(health_url(port), timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import ctypes

    kernel32 = ctypes.windll.kernel32
    SYNCHRONIZE = 0x00100000
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def _read_pid() -> int | None:
    path = pid_path()
    if not path.is_file():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    if _pid_alive(pid):
        return pid
    try:
        path.unlink()
    except OSError:
        pass
    return None


def server_running(port: int) -> bool:
    if is_server_healthy(port):
        return True
    return _read_pid() is not None


def start_server(cfg: dict | None = None) -> dict:
    """在独立进程中启动 ``qmt-server``。"""
    cfg = save_config(cfg or load_config())
    port = int(cfg["port"])
    if is_server_healthy(port):
        return {"ok": True, "already": True, "port": port}

    sites = find_xtquant_site_packages()
    ensure_xtquant_on_path()
    if not sites:
        return {
            "ok": False,
            "error": (
                "未找到 xtquant。请确认已安装券商 miniQMT；"
                "ARM 设备请优先使用 x86-win（x64）安装包以便对接 miniQMT。"
            ),
        }

    python = python_executable(windowed=False)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # 仍设置 PYTHONPATH：非嵌入式开发环境可用；嵌入式依赖上方 .pth
    extra = os.pathsep.join(sites)
    env["PYTHONPATH"] = (
        extra + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else extra
    )
    env["QMT_BRIDGE_HOST"] = str(cfg.get("host") or "0.0.0.0")
    env["QMT_BRIDGE_PORT"] = str(port)
    env["QMT_BRIDGE_LOG_LEVEL"] = str(cfg.get("log_level") or "info")
    env["QMT_BRIDGE_WORKERS"] = "1"
    env["QMT_BRIDGE_API_KEY"] = str(cfg.get("api_key") or "")
    env["QMT_BRIDGE_REQUIRE_AUTH_FOR_DATA"] = (
        "true" if cfg.get("require_auth_for_data") else "false"
    )
    env["QMT_BRIDGE_TRADING_ENABLED"] = (
        "true" if cfg.get("trading_enabled") else "false"
    )
    env["QMT_BRIDGE_MINI_QMT_PATH"] = str(cfg.get("mini_qmt_path") or "")
    env["QMT_BRIDGE_STOCK_ACCOUNT_ID"] = str(cfg.get("stock_account_id") or "")
    env["QMT_BRIDGE_CREDIT_ACCOUNT_ID"] = str(cfg.get("credit_account_id") or "")
    env["QMT_BRIDGE_DEFAULT_ACCOUNT"] = str(cfg.get("default_account") or "stock")

    log_file = server_log_path()
    log_handle = open(log_file, "a", encoding="utf-8")
    kwargs: dict = {
        "cwd": str(app_data_dir()),
        "env": env,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "close_fds": False,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
            [str(python), "-m", "qmt_bridge.server.cli"],
            **kwargs,
        )
    finally:
        log_handle.close()
    pid_path().write_text(str(proc.pid), encoding="utf-8")

    deadline = time.time() + 12
    while time.time() < deadline:
        if is_server_healthy(port, timeout=0.8):
            return {"ok": True, "already": False, "port": port, "pid": proc.pid}
        if proc.poll() is not None:
            tail = read_log_tail()
            return {
                "ok": False,
                "error": "服务进程已退出，请查看日志。",
                "log": tail,
            }
        time.sleep(0.4)
    # 进程还在但健康检查未通过：多半是 xtquant/QMT 未就绪
    return {
        "ok": True,
        "starting": True,
        "port": port,
        "pid": proc.pid,
        "warning": "服务已启动，但健康检查尚未通过。请确认 miniQMT 已登录。",
    }


def stop_server(port: int | None = None) -> dict:
    pid = _read_pid()
    if pid is None and port is not None and not is_server_healthy(port):
        return {"ok": True, "already": True}
    if pid is not None and sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
    elif pid is not None:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    try:
        pid_path().unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True}


def read_log_tail(max_chars: int = 4000) -> str:
    path = server_log_path()
    if not path.is_file():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-max_chars:]


def pick_folder() -> str:
    """弹出系统文件夹选择框，失败时返回空字符串。"""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="选择 miniQMT 的 userdata_mini 目录")
        root.destroy()
        return selected or ""
    except Exception:
        return ""


def autostart_command() -> str:
    root = install_root()
    if root is not None:
        return f'"{root / "QMTBridge.exe"}"'
    pythonw = python_executable(windowed=True)
    return f'"{pythonw}" -m qmt_bridge.desktop'


def set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


def open_path(path: Path | str) -> None:
    target = str(path)
    if sys.platform == "win32":
        os.startfile(target)  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", target])


def open_url(url: str) -> None:
    import webbrowser

    webbrowser.open(url)


def open_app_window(url: str) -> None:
    """尽量用 Edge/Chrome 的无标签 app 模式打开控制面板。"""
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Microsoft"
            / "Edge"
            / "Application"
            / "msedge.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "Google"
            / "Chrome"
            / "Application"
            / "chrome.exe",
        ]
        profile = app_data_dir() / "webview-profile"
        profile.mkdir(exist_ok=True)
        for browser in candidates:
            if not browser.is_file():
                continue
            subprocess.Popen(
                [
                    str(browser),
                    f"--app={url}",
                    "--window-size=920,540",
                    f"--user-data-dir={profile}",
                ],
                creationflags=CREATE_NO_WINDOW,
            )
            return
    open_url(url)


def _pid_from_lock() -> int | None:
    path = lock_path()
    if not path.is_file():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    if _pid_alive(pid):
        return pid
    try:
        path.unlink()
    except OSError:
        pass
    return None


def acquire_single_instance() -> bool:
    """本进程成为唯一桌面实例时返回 True；已有实例则唤起并返回 False。"""
    existing = _pid_from_lock()
    if existing is not None and existing != os.getpid():
        url_file = panel_url_path()
        for _ in range(10):
            if url_file.is_file():
                url = url_file.read_text(encoding="utf-8").strip()
                if url:
                    open_app_window(url)
                    break
            time.sleep(0.2)
        return False
    lock_path().write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_single_instance() -> None:
    try:
        if _pid_from_lock() == os.getpid():
            lock_path().unlink(missing_ok=True)
        panel_url_path().unlink(missing_ok=True)
    except OSError:
        pass
