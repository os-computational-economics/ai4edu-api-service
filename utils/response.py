from fastapi import HTTPException

def response(success: bool, data: None = None, message: str = None, status_code: int = 400):
    """
    :param success: Indicates if the request was successful.
    :param data: The payload to return in case of success.
    :param message: Optional message describing the success or the reason for error.
    :param status_code: HTTP status code to use for errors.
    :return: A JSON representing the success response structure, or raises HTTPException for errors.
    """
    if success:
        return {
            "status": "success",
            "data": data,
            "message": message
        }
    else:
        raise HTTPException(status_code=status_code, detail=message)
