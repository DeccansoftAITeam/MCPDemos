from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from util import validate_token


USERS = ["User Userson", "Admin Adminson"]
REQUIRED_SCOPE = "Admin.Write"
BEARER_PREFIX = "Bearer "


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    if not authorization_header.startswith(BEARER_PREFIX):
        return None
    token = authorization_header[len(BEARER_PREFIX):].strip()
    return token or None


def decode_token(authorization_header: str | None) -> dict | None:
    token = authorization_header[len(BEARER_PREFIX):].strip()
    if not token:
        return None
    return validate_token(token)


def is_user(decoded_token: dict) -> bool:
    return decoded_token.get("name") in USERS


def has_scope(decoded_token: dict, scope: str) -> bool:
    scopes = decoded_token.get("scopes", [])
    return scope in scopes


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            print("-> Missing Authorization header!")
            return Response(status_code=401, content="Unauthorized")

        token = authorization_header[len(BEARER_PREFIX):].strip()
        if not token:
            print("-> Invalid Authorization header format. Expected 'Bearer <token>'.")
            return Response(status_code=401, content="Unauthorized - invalid bearer token format")

        decoded_token = validate_token(token)
        if not decoded_token:
            print("-> Invalid or expired token!")
            return Response(status_code=403, content="Forbidden - invalid or expired token")

        print("Valid token, proceeding...")

        if not is_user(decoded_token):
            print(f"-> User does not exist! Token name: {decoded_token.get('name')}")
            return Response(status_code=403, content="Forbidden - user does not exist")
        print("User exists, proceeding...")

        if not has_scope(decoded_token, REQUIRED_SCOPE):
            print(f"-> Missing required scope! Token scopes: {decoded_token.get('scopes', [])}")
            return Response(status_code=403, content="Forbidden - insufficient scopes")

        print("User has required scope, proceeding...")
        print(f"-> Received {request.method} {request.url}")

        response = await call_next(request)
        response.headers["Custom"] = "Example"
        return response
