"""元数据端点冒烟测试。"""

from __future__ import annotations


def test_meta_version(client) -> None:
    resp = client.get("/api/meta/version")
    assert resp.status_code == 200
    assert "version" in resp.json()


def test_meta_markets(client) -> None:
    resp = client.get("/api/meta/markets")
    assert resp.status_code == 200
    assert "markets" in resp.json()


def test_meta_stock_list(client) -> None:
    resp = client.get(
        "/api/meta/stock_list",
        params={"category": "沪深A股"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert "000001.SZ" in data["stocks"]
