import jwt
import os
from datetime import datetime, timedelta, timezone

private_key = os.getenv("PRIVATE_KEY")
public_key = os.getenv("PUBLIC_KEY")
algorithm = "RS256"


def jwt_generator(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        # "name": "username",
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, private_key, algorithm=algorithm)


def parse_token(jwt_token: str) -> dict:
    if not jwt_token:
        return {"success": False, "status_code": 401,
                "message": "Token missing"}
    try:
        decoded = jwt.decode(jwt_token, public_key, algorithms=[algorithm])
        return {"success": True, "status_code": 200, "message": "",
                "data": decoded}
    except jwt.ExpiredSignatureError:
        return {"success": False, "status_code": 401001,
                "message": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"success": False, "status_code": 401002,
                "message": "Invalid token"}
