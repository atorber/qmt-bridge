"""API Key 认证相关测试。"""

from __future__ import annotations


def test_trading_requires_api_key(client) -> None:
    """交易端点未带 Key 应返回 401。"""
    resp = client.get("/api/trading/positions")
    assert resp.status_code == 401


def test_trading_with_valid_api_key(client, auth_headers) -> None:
    """携带正确 Key 可查询持仓。"""
    resp = client.get("/api/trading/positions", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body


def test_trading_with_invalid_api_key(client) -> None:
    """错误 Key 应被拒绝。"""
    resp = client.get(
        "/api/trading/positions",
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_meta_health_no_auth_required(client) -> None:
    """健康检查无需认证。"""
    resp = client.get("/api/meta/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
