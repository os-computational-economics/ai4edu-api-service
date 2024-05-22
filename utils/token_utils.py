import jwt
from datetime import datetime, timedelta, timezone

secret_key = "ai4edu"
algorithm = "HS256"


def jwt_generator() -> str:
    payload = {
        "user_id": "caseid",
        "name": "username",
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(seconds=1),
        "data": {"user_name": "张三", "uid": 1234567, "phone": "17600000000"}
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def parse_token(jwt_token: str) -> dict:
    if not jwt_token:
        return {"success": False, "status_code": 401,
                "message": "Token missing"}
    try:
        decoded = jwt.decode(jwt_token, secret_key, algorithms=[algorithm])
        return {"success": True, "status_code": 200, "message": "",
                "data": decoded}
    except jwt.ExpiredSignatureError:
        return {"success": False, "status_code": 401,
                "message": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"success": False, "status_code": 401,
                "message": "Invalid token"}
