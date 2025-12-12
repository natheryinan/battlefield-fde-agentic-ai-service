# app/aws_lambda_handler.py
from __future__ import annotations

import json
import base64
from typing import Any, Dict

from .router import handle_run_engine


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 API Gateway 事件里把 body 解出来，兼容 base64。
    """
    body = event.get("body") or "{}"

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {}


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # 如果前端要直接打，就先全开 CORS
        },
        "body": json.dumps(body),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    顶层 Lambda 入口。
    把 API Gateway 的 event → 路由 → 引擎 → 标准 HTTP 响应。
    """
    try:
        route_key = event.get("routeKey")  # e.g. "POST /engine/run"
        http_method = event.get("requestContext", {}).get("http", {}).get("method")

        # 兼容两种写法，防止以后你切 API 类型
        path = (
            event.get("rawPath")
            or event.get("path")
            or event.get("requestContext", {}).get("http", {}).get("path")
        )

        # ---- 路由表 （简单版）----
        if (route_key == "POST /engine/run") or (
            http_method == "POST" and path == "/engine/run"
        ):
            payload = _parse_body(event)
            data = handle_run_engine(payload)
            # 如果 handle_run_engine 里返回 error，就统一 400
            if "error" in data:
                return _response(400, {"ok": False, **data})
            return _response(200, {"ok": True, "data": data})

        # 其他路径：404
        return _response(404, {"ok": False, "error": {"code": "NOT_FOUND"}})

    except Exception as e:
        # 这里生产上可以打 CloudWatch 日志、带 trace_id
        return _response(
            500,
            {
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                },
            },
        )

