from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from xhs.help import sign as xhs_sign


def sign_request(
    uri: str,
    data: dict[str, Any] | None = None,
    *,
    a1: str = "",
    b1: str = "",
    web_session: str = "",
    ctime: int | None = None,
) -> dict[str, str]:
    """Return Xiaohongshu web API signing headers for a request.

    `web_session` is accepted for compatibility with external signer payloads, but the
    bundled xhs algorithm only uses `a1` and optional localStorage `b1`.
    """

    if not uri or not uri.startswith("/"):
        raise ValueError("uri must be a Xiaohongshu API path starting with '/'.")
    payload = data if isinstance(data, dict) else None
    signs = xhs_sign(uri, payload, ctime=ctime, a1=a1 or "", b1=b1 or "")
    return {
        key: str(signs[key])
        for key in ("x-s", "x-t", "x-s-common")
        if signs.get(key)
    }


class XhsSignerHandler(BaseHTTPRequestHandler):
    server_version = "video-bundle-agent-xhs-signer/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/sign":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(size).decode("utf-8") if size else "{}"
            payload = json.loads(body or "{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object.")
            signs = sign_request(
                str(payload.get("uri") or ""),
                payload.get("data") if isinstance(payload.get("data"), dict) else None,
                a1=str(payload.get("a1") or ""),
                b1=str(payload.get("b1") or ""),
                web_session=str(payload.get("web_session") or ""),
                ctime=payload.get("ctime") if isinstance(payload.get("ctime"), int) else None,
            )
        except Exception as error:  # noqa: BLE001
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"error": type(error).__name__, "message": str(error)},
            )
            return
        self._write_json(HTTPStatus.OK, signs)


def create_signer_server(host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), XhsSignerHandler)


def serve_signer(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = create_signer_server(host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
