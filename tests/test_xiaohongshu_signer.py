from __future__ import annotations

import threading

import httpx

from video_bundle_agent.providers.xiaohongshu.signer import create_signer_server, sign_request


def test_sign_request_returns_xhs_headers() -> None:
    headers = sign_request(
        "/api/sns/web/v2/comment/page?note_id=abc123&cursor=",
        a1="a-one",
    )

    assert set(headers) == {"x-s", "x-t", "x-s-common"}
    assert headers["x-s"]
    assert headers["x-t"].isdigit()


def test_signer_server_serves_health_and_sign() -> None:
    server = create_signer_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        health = httpx.get(f"http://127.0.0.1:{port}/health", timeout=5)
        response = httpx.post(
            f"http://127.0.0.1:{port}/sign",
            json={
                "uri": "/api/sns/web/v2/comment/page?note_id=abc123&cursor=",
                "a1": "a-one",
            },
            timeout=5,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert health.json() == {"status": "ok"}
    assert response.status_code == 200
    assert set(response.json()) == {"x-s", "x-t", "x-s-common"}
