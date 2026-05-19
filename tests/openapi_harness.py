"""基于 OpenAPI 的 REST 端点批量调用工具。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from tests.openapi_samples import (
    OPERATION_SAMPLES,
    SKIP_OPERATIONS,
    TRADING_PREFIXES,
)

HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "head", "options"})

SUCCESS_STATUS = frozenset({200, 201, 204})

# 路径参数占位默认值
_PATH_PARAM_DEFAULTS: dict[str, str] = {
    "stock_code": "000001.SZ",
    "stock": "000001.SZ",
    "stocks": "000001.SZ",
    "option_code": "10001234.SH",
    "order_id": "10001",
    "trade_id": "20001",
    "market": "SH",
    "sector": "沪深A股",
    "index_code": "000300.SH",
    "undl_code": "000300.SH",
    "code_market": "IF.CFE",
    "account_id": "12345678",
    "sysid": "test-sysid",
}


@dataclass(frozen=True)
class ApiOperation:
    """单个 REST 操作描述。"""

    method: str
    path: str
    operation_id: str
    requires_auth: bool

    @property
    def key(self) -> str:
        return f"{self.method.upper()} {self.path}"


def _requires_auth(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in TRADING_PREFIXES)


def collect_operations(spec: dict) -> list[ApiOperation]:
    """从 OpenAPI 规范收集所有 HTTP 操作。"""
    ops: list[ApiOperation] = []
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if method.lower() in ("head", "options"):
                continue
            op = ApiOperation(
                method=method.lower(),
                path=path,
                operation_id=operation.get("operationId", f"{method}_{path}"),
                requires_auth=_requires_auth(path),
            )
            if op.key in SKIP_OPERATIONS:
                continue
            ops.append(op)
    return ops


def _resolve_ref(schema: dict, components: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    name = ref.rsplit("/", 1)[-1]
    return components.get("schemas", {}).get(name, schema)


def _sample_value(
    schema: dict,
    components: dict,
    *,
    name: str = "",
    depth: int = 0,
) -> Any:
    if depth > 6:
        return None
    schema = _resolve_ref(schema, components)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    for key in ("anyOf", "oneOf"):
        if key in schema:
            variants = schema[key]
            for variant in variants:
                if variant.get("type") != "null":
                    return _sample_value(variant, components, name=name, depth=depth + 1)
            return None

    schema_type = schema.get("type")
    if schema_type == "string":
        if name in _PATH_PARAM_DEFAULTS:
            return _PATH_PARAM_DEFAULTS[name]
        fmt = schema.get("format")
        if fmt == "date-time":
            return "20250101120000"
        return "000001.SZ"
    if schema_type == "integer":
        if "order" in name.lower():
            return 10001
        return 1
    if schema_type == "number":
        return 10.0
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        items = schema.get("items", {"type": "string"})
        return [_sample_value(items, components, depth=depth + 1)]
    if schema_type == "object":
        props = schema.get("properties", {})
        if not props:
            return {}
        required = set(schema.get("required", []))
        result = {}
        for prop_name, prop_schema in props.items():
            if prop_name in required or len(required) <= 3:
                result[prop_name] = _sample_value(
                    prop_schema,
                    components,
                    name=prop_name,
                    depth=depth + 1,
                )
        return result
    return None


def _build_params(
    operation: dict,
    components: dict,
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any] | list[Any] | None]:
    path_params: dict[str, str] = {}
    query: dict[str, Any] = {}
    body: dict[str, Any] | list[Any] | None = None

    for param in operation.get("parameters", []):
        param = _resolve_ref(param, components)
        loc = param.get("in")
        name = param.get("name", "")
        required = param.get("required", False)
        schema = param.get("schema", {"type": "string"})
        value = _sample_value(schema, components, name=name)
        if loc == "path" and value is not None:
            path_params[name] = str(value)
        elif loc == "query":
            if required or name in ("stocks", "stock", "sector", "market", "category"):
                query[name] = value if value is not None else _PATH_PARAM_DEFAULTS.get(
                    name, "000001.SZ"
                )

    request_body = operation.get("requestBody")
    if request_body:
        content = request_body.get("content", {})
        json_schema = content.get("application/json", {}).get("schema")
        if json_schema:
            body = _sample_value(json_schema, components)
            if isinstance(body, dict) and not body:
                body = {}

    return path_params, query, body


def _apply_path(path: str, path_params: dict[str, str]) -> str:
    url = path
    for key, value in path_params.items():
        url = url.replace("{" + key + "}", str(value))
    return url


def build_request(
    spec: dict,
    op: ApiOperation,
) -> tuple[str, str, dict[str, Any], dict[str, Any] | list[Any] | None]:
    """构造请求的 method、url、query、body。"""
    path_item = spec["paths"][op.path]
    operation = path_item[op.method]
    components = spec.get("components", {})

    override = OPERATION_SAMPLES.get(op.key, {})
    path_params, query, body = _build_params(operation, components)

    path_params.update(override.get("path_params", {}))
    query.update(override.get("query", {}))
    if "body" in override:
        body = override["body"]

    url = _apply_path(op.path, path_params)
    return op.method, url, query, body


def invoke_operation(
    client: TestClient,
    spec: dict,
    op: ApiOperation,
    headers: dict[str, str] | None = None,
) -> Any:
    """调用单个端点并返回 TestClient 响应。"""
    method, url, query, body = build_request(spec, op)
    req_headers = dict(headers or {})
    kwargs: dict[str, Any] = {"headers": req_headers}
    if query:
        kwargs["params"] = query
    if body is not None and op.method in ("post", "put", "patch"):
        kwargs["json"] = body

    return getattr(client, method)(url, **kwargs)


def run_all_operations(
    client: TestClient,
    spec: dict,
    *,
    auth_headers: dict[str, str],
) -> list[tuple[ApiOperation, int, str]]:
    """执行全部操作，返回失败列表 (op, status, detail)。"""
    failures: list[tuple[ApiOperation, int, str]] = []
    for op in collect_operations(spec):
        headers = auth_headers if op.requires_auth else {}
        resp = invoke_operation(client, spec, op, headers=headers)
        if resp.status_code not in SUCCESS_STATUS:
            detail = resp.text[:300] if resp.text else ""
            failures.append((op, resp.status_code, detail))
    return failures
