"""桌面壳入口：控制面板 + 系统托盘。"""

from __future__ import annotations

import logging
import sys
import threading

from qmt_bridge.desktop import runtime
from qmt_bridge.desktop.panel import start_panel_server

logger = logging.getLogger("qmt_bridge.desktop")


def _setup_logging() -> None:
    runtime.app_data_dir()
    log_file = runtime.log_dir() / "desktop.log"
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)


def _run_tray(panel_url: str) -> None:
    try:
        import pystray

        from qmt_bridge.desktop.icon import tray_image
    except Exception as exc:
        logger.warning("系统托盘不可用（%s），控制面板窗口仍可使用", exc)
        threading.Event().wait()
        return

    def _open(icon=None, item=None):  # noqa: ARG001
        runtime.open_app_window(panel_url)

    def _start(icon=None, item=None):  # noqa: ARG001
        try:
            runtime.start_server()
        except Exception:
            logger.exception("托盘启动服务失败")

    def _stop(icon=None, item=None):  # noqa: ARG001
        cfg = runtime.load_config()
        runtime.stop_server(int(cfg["port"]))

    def _exit(icon, item=None):  # noqa: ARG001
        cfg = runtime.load_config()
        runtime.stop_server(int(cfg["port"]))
        runtime.release_single_instance()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("打开主界面", _open, default=True),
        pystray.MenuItem("启动服务", _start),
        pystray.MenuItem("停止服务", _stop),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _exit),
    )
    icon = pystray.Icon(
        "qmt-bridge",
        icon=tray_image(64),
        title="QMT Bridge",
        menu=menu,
    )
    logger.info("托盘已启动")
    icon.run()


def main(argv: list[str] | None = None) -> int:
    _ = argv
    if sys.platform != "win32":
        print(
            "QMT Bridge 桌面程序仅支持 Windows（需与 miniQMT 同机）。", file=sys.stderr
        )
        return 2

    _setup_logging()
    if not runtime.acquire_single_instance():
        logger.info("已有实例在运行，已尝试打开主界面")
        return 0

    runtime.ensure_xtquant_on_path()
    httpd = start_panel_server("127.0.0.1", 0)
    host, port = httpd.server_address[:2]
    panel_url = f"http://{host}:{port}/"
    runtime.panel_url_path().write_text(panel_url, encoding="utf-8")
    logger.info("控制面板: %s", panel_url)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    cfg = runtime.load_config()
    if cfg.get("start_on_launch"):
        threading.Thread(target=lambda: runtime.start_server(cfg), daemon=True).start()

    runtime.open_app_window(panel_url)
    try:
        _run_tray(panel_url)
    except KeyboardInterrupt:
        pass
    finally:
        runtime.release_single_instance()
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
