import jwt
import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

private_key = os.getenv("JWT_PRIVATE_KEY")
public_key = os.getenv("JWT_PUBLIC_KEY")
algorithm = "RS256"


def jwt_generator(user_id: str, first_name: str, last_name: str, student_id: str, role: dict, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "student_id": student_id,
        "role": role,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, private_key, algorithm=algorithm)


def parse_token(jwt_token: str) -> dict:
    logger.info(f"Parsing token: {jwt_token}")
    if not jwt_token:
        logger.error("Token missing")
        return {"success": False, "status_code": 401000,
                "message": "Token missing"}
    try:
        decoded = jwt.decode(jwt_token, public_key, algorithms=[algorithm])
        return {"success": True, "status_code": 200, "message": "",
                "data": decoded}
    except jwt.ExpiredSignatureError:
        logger.error(f"Token has expired")
        return {"success": False, "status_code": 401001,
                "message": "Token has expired"}
    except jwt.InvalidTokenError:
        logger.error(f"Invalid Token")
        return {"success": False, "status_code": 401002,
                "message": "Invalid token"}
