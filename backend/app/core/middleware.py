"""
全局请求日志中间件
"""
import time
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        path = request.url.path
        method = request.method
        ip = request.client.host if request.client else "-"
        ua = request.headers.get("user-agent", "-")

        try:
            response = await call_next(request)
            status = getattr(response, "status_code", 0) or 0
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(f"{method} {path} {status} {duration_ms}ms ip={ip} ua={ua}")
            return response
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.error(f"{method} {path} 500 {duration_ms}ms ip={ip} ua={ua} error={e}")
            raise