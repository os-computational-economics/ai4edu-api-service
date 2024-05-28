import jwt
import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def fix_key(broken_key):
    """
    Fix the broken key by removing 'n' every 64 characters, and reformatting the key
    :param broken_key:
    :return:
    """
    # Step 1: Find the header and footer
    header_start = broken_key.find("-----BEGIN")
    header_end = broken_key.find("-----", header_start + len("-----BEGIN")) + len("-----")
    header = broken_key[header_start:header_end]

    footer_start = broken_key.find("-----END")
    footer_end = broken_key.find("-----", footer_start + len("-----END")) + len("-----")
    footer = broken_key[footer_start:footer_end]

    # Step 2: Extract the body between header and footer
    body_start = header_end
    body_end = footer_start
    body = broken_key[body_start:body_end]

    # Step 3: Remove 'n' every 64 characters in the body
    body = body[1:]  # remove the first 'n'
    body_chunks = [body[i:i + 65] for i in range(0, len(body), 65)]  # split the body into 65-character chunks
    body_chunks = [chunk[:-1] for chunk in body_chunks]  # remove the last 'n' in each chunk
    formatted_body = '\n'.join(body_chunks)

    # Step 4: Assemble everything
    fixed_key = f"{header}\n{formatted_body}\n{footer}"

    return fixed_key


private_key = os.getenv("JWT_PRIVATE_KEY")
# if the key starts with a lower case n after the header, it is broken
header_start = private_key.find("-----BEGIN")
header_end = private_key.find("-----", header_start + len("-----BEGIN")) + len("-----")
if private_key[header_end] == 'n':
    private_key = fix_key(private_key)
public_key = os.getenv("JWT_PUBLIC_KEY")
# if the key starts with a lower case n after the header, it is broken
header_start = public_key.find("-----BEGIN")
header_end = public_key.find("-----", header_start + len("-----BEGIN")) + len("-----")
if public_key[header_end] == 'n':
    public_key = fix_key(public_key)
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
