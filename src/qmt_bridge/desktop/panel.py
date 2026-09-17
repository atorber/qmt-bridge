"""本地控制面板 HTTP 服务（仅绑定 127.0.0.1）。"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from qmt_bridge._version import __version__
from qmt_bridge.desktop import runtime

logger = logging.getLogger("qmt_bridge.desktop")

_ASSETS = Path(__file__).resolve().parent / "assets"


def _read_asset(name: str) -> bytes:
    path = _ASSETS / name
    return path.read_bytes()


def snapshot() -> dict:
    cfg = runtime.load_config()
    port = int(cfg["port"])
    healthy = runtime.is_server_healthy(port)
    running = healthy or runtime.server_running(port)
    qmt = runtime.detect_qmt()
    xt = runtime.xtquant_status()
    ip = runtime.lan_ip()
    return {
        "version": __version__,
        "running": running,
        "healthy": healthy,
        "port": port,
        "local_url": f"http://127.0.0.1:{port}",
        "lan_url": f"http://{ip}:{port}",
        "docs_url": f"http://127.0.0.1:{port}/docs",
        "qmt": qmt,
        "xtquant": xt,
        "config": cfg,
        "log_tail": runtime.read_log_tail(2500),
    }


class PanelHandler(BaseHTTPRequestHandler):
    server_version = "QMTBridgePanel/1.0"

    def log_message(self, fmt: str, *args) -> None:
        logger.debug("%s - " + fmt, self.address_string(), *args)

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._bytes(_read_asset("index.html"), "text/html; charset=utf-8")
            return
        if path == "/favicon.ico":
            try:
                from qmt_bridge.desktop.icon import png_bytes

                self._bytes(png_bytes(32), "image/png")
            except Exception:
                self._bytes(b"", "image/x-icon")
            return
        if path == "/api/state":
            self._json(snapshot())
            return
        self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/config":
                cfg = runtime.save_config(self._read_json())
                self._json({"ok": True, "config": cfg})
                return
            if path == "/api/start":
                payload = self._read_json()
                result = runtime.start_server(payload or None)
                status = 200 if result.get("ok") else 500
                self._json(result, status)
                return
            if path == "/api/stop":
                cfg = runtime.load_config()
                result = runtime.stop_server(int(cfg["port"]))
                self._json(result)
                return
            if path == "/api/browse":
                selected = runtime.pick_folder()
                self._json({"ok": True, "path": selected})
                return
            if path == "/api/open-docs":
                cfg = runtime.load_config()
                runtime.open_url(f"http://127.0.0.1:{int(cfg['port'])}/docs")
                self._json({"ok": True})
                return
            if path == "/api/open-logs":
                runtime.open_path(runtime.log_dir())
                self._json({"ok": True})
                return
            if path == "/api/detect":
                qmt = runtime.detect_qmt()
                self._json(
                    {"ok": True, "qmt": qmt, "xtquant": runtime.xtquant_status()}
                )
                return
        except Exception as exc:
            logger.exception("面板接口失败: %s", path)
            self._json({"ok": False, "error": str(exc)}, 500)
            return
        self._json({"ok": False, "error": "not found"}, 404)


def start_panel_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), PanelHandler)
    httpd.daemon_threads = True
    return httpd
