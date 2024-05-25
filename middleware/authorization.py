from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from utils.whitelist import whitelist
from utils.endpoint_access_map import endpoint_access_map
from utils.token_utils import parse_token
import logging

logger = logging.getLogger(__name__)

def extract_token(auth_header) -> dict:
    access_token = None
    refresh_token = None
    if auth_header and auth_header.startswith('Bearer '):
        logger.info(f"Extracting token from header: {auth_header}")
        # Remove the 'Bearer ' prefix
        token_string = auth_header[7:]
        # Split the token string into key-value pairs
        token_pairs = token_string.split('&')
        # Extract tokens from key-value pairs
        for pair in token_pairs:
            if '=' in pair:
                key, value = pair.split('=')
                if key == 'access':
                    access_token = value if value != '' else None
                elif key == 'refresh':
                    refresh_token = value if value != '' else None
    return {"access_token": access_token, "refresh_token": refresh_token}


def has_access(endpoint_access_map, user_access, current_path):
    # Check if the current path exists in the endpoint_access_map
    if current_path in endpoint_access_map:
        access_roles = endpoint_access_map[current_path]
        # Check if the user has access based on their roles
        for role, has_role in user_access.items():
            if has_role and access_roles.get(role, False):
                return True
    else:
        # Check if the current path matches any dynamic endpoint pattern
        for endpoint_pattern in endpoint_access_map:
            if "{" in endpoint_pattern:
                # Split the endpoint pattern and current path into parts
                pattern_parts = endpoint_pattern.split("/")
                path_parts = current_path.split("/")

                # Check if the number of parts matches
                if len(pattern_parts) == len(path_parts):
                    # Check if all non-dynamic parts match
                    for i in range(len(pattern_parts)):
                        if "{" not in pattern_parts[i] and pattern_parts[i] != path_parts[i]:
                            break
                    else:
                        # All non-dynamic parts matched, check user access
                        access_roles = endpoint_access_map[endpoint_pattern]
                        for role, has_role in user_access.items():
                            if has_role and access_roles.get(role, False):
                                return True

    # If no matching endpoint found or user doesn't have access, return False
    return False


def extract_actual_path(path):
    # Split the path by the forward slash (/)
    path_parts = path.split("/")
    # Remove the first three elements from the path_parts list
    actual_path_parts = path_parts[4:]
    # Join the remaining elements back together with a forward slash (/)
    actual_path = "/" + "/".join(actual_path_parts)
    return actual_path


class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = extract_actual_path(request.url.path)
        print('path', path)
        # if path in whitelist:
        #     return await call_next(request)
        if path not in endpoint_access_map:
            return await call_next(request)

        # print('auth', request.headers.get('Authorization', ''))

        tokens = extract_token(request.headers.get('Authorization', ''))
        if tokens['access_token'] is not None:
            parse_result = parse_token(tokens['access_token'])
            if parse_result['success']:
                user_access = parse_result['data']['role']
                if has_access(endpoint_access_map, user_access, path):
                    return await call_next(request)
            else:
                return JSONResponse(content={"success": False, "message": parse_result['message'], "status_code": parse_result['status_code']}, status_code=401)
        return JSONResponse(content={"success": False, "message": "unauthorized", "status_code": 401}, status_code=401)
