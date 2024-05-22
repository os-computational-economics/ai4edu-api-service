from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from utils.whitelist import whitelist
from utils.token_utils import parse_token
from utils.response import response
from fastapi.exceptions import HTTPException

class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in whitelist:
            return await call_next(request)

        token = request.headers.get('Authorization', '').split('Bearer ')[-1]
        payload = parse_token(token)
        if not payload['success']:
            return JSONResponse(content={"success": False, "message": payload['message'], "status_code": payload['status_code'] }, status_code=payload['status_code'])

        return await call_next(request)
