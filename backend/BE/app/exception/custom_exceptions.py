from fastapi import HTTPException

from app.exception.error_code import Error


class APIException(HTTPException):
    def __init__(self, status_code: int, error: Error):
        super().__init__(
            status_code=status_code,
            detail={
                "status": status_code,
                "message" : error.message,
                "errorCode" : error.code
            }
        )