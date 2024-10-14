from typing import Any
from starlette.responses import JSONResponse


def response(
    success: bool,
    data: None | dict[str, Any] = None,
    message: str = "Success",
    status_code: int = 400,
):
    """
    :param success: Indicates if the request was successful.
    :param data: The payload to return in case of success.
    :param message: Optional message describing the success or the reason for error.
    :param status_code: HTTP status code to use for errors.
    :return: A JSON representing the success response structure, or raises HTTPException for errors.
    """
    if success:
        return {"status": 200, "data": data, "message": message or "Success"}
    else:
        return JSONResponse(
            content={"success": False, "message": message, "status_code": status_code},
            status_code=status_code,
        )
        # raise HTTPException(status_code=status_code, detail=message)
