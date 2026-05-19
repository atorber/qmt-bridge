"""OpenAPI 契约测试：自动遍历并验证全部 REST 端点。"""

from __future__ import annotations

import pytest

from tests.openapi_harness import (
    ApiOperation,
    collect_operations,
    invoke_operation,
    run_all_operations,
)

# 按 tag 前缀分组，便于定位失败域
_TAG_PREFIXES = (
    "meta",
    "market",
    "tick",
    "sector",
    "calendar",
    "financial",
    "instrument",
    "option",
    "etf",
    "cb",
    "futures",
    "download",
    "formula",
    "hk",
    "tabular",
    "utility",
    "legacy",
    "trading",
    "credit",
    "fund",
    "bank",
    "smt",
)


def _tag_for_path(path: str) -> str:
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "api":
        return parts[1]
    return parts[0] if parts else "root"


@pytest.fixture(scope="module")
def all_operations(openapi_spec: dict) -> list[ApiOperation]:
    return collect_operations(openapi_spec)


def test_openapi_has_enough_operations(all_operations: list[ApiOperation]) -> None:
    """确保 OpenAPI 收录了主要 REST 路由。"""
    assert len(all_operations) >= 120


def test_all_rest_endpoints(client, openapi_spec, auth_headers) -> None:
    """批量调用全部 REST 端点，期望 2xx。"""
    failures = run_all_operations(client, openapi_spec, auth_headers=auth_headers)
    if not failures:
        return
    lines = [
        f"  {op.method.upper()} {op.path} -> {status}: {detail[:120]}"
        for op, status, detail in failures[:30]
    ]
    extra = len(failures) - 30
    suffix = f"\n  ... 另有 {extra} 个失败" if extra > 0 else ""
    pytest.fail(
        f"{len(failures)} 个端点未返回 2xx:\n" + "\n".join(lines) + suffix
    )


@pytest.mark.parametrize("tag", _TAG_PREFIXES)
def test_rest_endpoints_by_tag(
    client,
    openapi_spec,
    auth_headers,
    tag: str,
    all_operations: list[ApiOperation],
) -> None:
    """按 API 域分组验证，便于 CI 定位。"""
    ops = [op for op in all_operations if _tag_for_path(op.path) == tag]
    if not ops:
        pytest.skip(f"无 {tag} 相关端点")

    failures = []
    for op in ops:
        headers = auth_headers if op.requires_auth else {}
        resp = invoke_operation(client, openapi_spec, op, headers=headers)
        if resp.status_code not in {200, 201, 204}:
            failures.append(f"{op.method.upper()} {op.path} -> {resp.status_code}")

    assert not failures, "\n".join(failures)
