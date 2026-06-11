from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADERS: dict[str, str] = {
    # Prevent MIME-type sniffing
    "X-Content-Type-Options": "nosniff",
    # Block the page from being framed (clickjacking protection)
    "X-Frame-Options": "DENY",
    # Limit referrer info sent to third parties
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Deny browser feature APIs this API has no business using
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # Enforce HTTPS for 1 year (active once the service is behind TLS)
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # API responses must never be cached by browsers or intermediaries
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in _HEADERS.items():
            response.headers[name] = value
        return response
