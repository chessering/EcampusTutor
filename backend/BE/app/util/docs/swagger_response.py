from typing import Any, Dict, Type

from pydantic import BaseModel

from app.schema.common import APIResponse, ErrorResponse


def success_response(model: Type[BaseModel], example: Any = None) -> Dict:
    return {
        200: {
            "model": APIResponse[model],  # Generic 응답 구조
            "description": "요청이 성공적으로 처리되었습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "요청이 성공적으로 처리되었습니다.",
                        "data": example or {},
                    }
                }
            },
        }
    }


def error_response(status: int, message: str, error_code: str) -> Dict:
    return {
        status: {
            "model": ErrorResponse,
            "description": message,
            "content": {
                "application/json": {
                    "example": {
                        "status": status,
                        "message": message,
                        "errorCode": error_code,
                    }
                }
            },
        }
    }