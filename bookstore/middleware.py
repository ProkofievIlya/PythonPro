import logging
import time

logger = logging.getLogger("bookstore")


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            username = user.get_username()
        else:
            username = "anonymous"
        logger.info(
            "%s %s %s user=%s %.1fms",
            request.method,
            request.path,
            response.status_code,
            username,
            elapsed_ms,
        )
        return response
