"""进程内 API 防护中间件：滑动窗口限流 + 请求体上限（默认关闭，按需开启）。"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _SlidingWindowLimiter:
    """滑动窗口日志限流。桶按 IP 建立且条目过期后并不自动消失，
    因此周期性清扫空桶与过期桶，避免公网环境下大量一次性 IP 造成内存无界增长。"""

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        *,
        sweep_interval: int = 64,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._sweep_interval = max(1, sweep_interval)
        self._calls_since_sweep = 0

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        self._calls_since_sweep += 1
        if self._calls_since_sweep >= self._sweep_interval:
            self._calls_since_sweep = 0
            self._sweep(now)
        window = self._hits[key]
        while window and now - window[0] >= self._window:
            window.popleft()
        if len(window) >= self._limit:
            return False
        window.append(now)
        return True

    def _sweep(self, now: float) -> None:
        expired = [
            key
            for key, window in self._hits.items()
            if not window or now - window[-1] >= self._window
        ]
        for key in expired:
            del self._hits[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按客户端 IP 限制写操作频率（创建扫描 / 上传验证结果）。"""

    def __init__(self, app, *, limit: int, window_seconds: float = 60.0) -> None:
        super().__init__(app)
        self._limiter = _SlidingWindowLimiter(limit, window_seconds)

    async def dispatch(self, request, call_next):
        path = request.url.path.rstrip("/")
        is_write = request.method == "POST" and (
            path == "/api/scans" or path.endswith("/verification-runs")
        )
        if is_write:
            client_ip = request.client.host if request.client else "unknown"
            if not self._limiter.allow(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "请求过于频繁，请稍后再试。",
                            "details": {},
                        }
                    },
                )
        return await call_next(request)


class RequestBodyLimitMiddleware:
    """同时校验 Content-Length 和实际接收字节数。"""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "").rstrip("/")
        # 验证结果上传走端点自身的流式分块校验（UPLOAD_TOO_LARGE 语义），
        # 全局请求体上限在这里放行，避免错误码契约被静默替换。
        if scope.get("method") == "POST" and path.endswith("/verification-runs"):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                if int(declared.decode("ascii")) > self._max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except (UnicodeDecodeError, ValueError):
                pass

        received = 0
        buffered: deque[Message] = deque()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                buffered.append(message)
                break
            received += len(message.get("body", b""))
            if received > self._max_bytes:
                await self._reject(scope, receive, send)
                return
            buffered.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive() -> Message:
            if buffered:
                return buffered.popleft()
            return await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "REQUEST_TOO_LARGE",
                    "message": f"请求体不能超过 {self._max_bytes} 字节。",
                    "details": {},
                }
            },
        )
        await response(scope, receive, send)
