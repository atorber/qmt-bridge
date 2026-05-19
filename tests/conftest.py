"""QMT Bridge API 测试 fixtures。"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# 必须在导入 qmt_bridge.server 之前安装 xtquant 桩
from tests.mocks.trader_mock import TraderManagerStub
from tests.mocks.xtquant_mock import install_xtquant_mock

install_xtquant_mock()

from qmt_bridge.server.app import create_app  # noqa: E402
from qmt_bridge.server.config import Settings, reset_settings  # noqa: E402

TEST_API_KEY = "test-secret-key"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """全功能测试配置（交易开启 + API Key）。"""
    return Settings(
        api_key=TEST_API_KEY,
        trading_enabled=True,
        notify_enabled=False,
        require_auth_for_data=False,
        trading_account_id="12345678",
        mini_qmt_path="C:\\mock\\qmt",
        xtdata_lock_wait_timeout_sec=5.0,
        divid_factors_timeout_sec=2.0,
        market_data_timeout_sec=5.0,
    )


@pytest.fixture(scope="session")
def app(test_settings: Settings):
    """带 mock 交易模块的 FastAPI 应用。"""
    reset_settings(test_settings)
    os.environ["QMT_BRIDGE_API_KEY"] = TEST_API_KEY
    os.environ["QMT_BRIDGE_TRADING_ENABLED"] = "true"

    with patch(
        "qmt_bridge.server.trading.manager.XtTraderManager",
        TraderManagerStub,
    ):
        application = create_app(test_settings)
        yield application
    reset_settings(None)


@pytest.fixture(scope="session")
def client(app):
    """HTTP 测试客户端（自动执行 lifespan）。"""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def openapi_spec(client: TestClient) -> dict:
    """应用 OpenAPI 规范。"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture(autouse=True)
def _patch_heavy_download(monkeypatch):
    """避免测试触发真实 xtdata 批量下载。"""
    monkeypatch.setattr(
        "qmt_bridge.server.downloader.download_history_data2_safe",
        lambda *args, **kwargs: {"downloaded": 0, "skipped": 0},
    )
