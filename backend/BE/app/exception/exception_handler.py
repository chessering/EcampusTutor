# app/exception/exception_handler.py

import traceback

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.exception.custom_exceptions import APIException
from app.exception.error_code import Error


async def api_exception_handler(request: Request, exc: APIException):
    """
    커스텀 API 예외 핸들러
    """
    # ⭐ exc.detail이 딕셔너리로 되어 있음
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    
    print("=" * 60)
    print(f"🚨 API Exception Caught!")
    print(f"📍 Path: {request.method} {request.url.path}")
    print(f"🔴 Status Code: {exc.status_code}")
    print(f"💬 Error Code: {detail.get('errorCode', 'N/A')}")
    print(f"💬 Message: {detail.get('message', 'N/A')}")
    print("=" * 60)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=detail  # ⭐ detail을 그대로 반환
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    SQLAlchemy 예외 핸들러
    """
    print("=" * 60)
    print(f"🚨 Database Exception Caught!")
    print(f"📍 Path: {request.method} {request.url.path}")
    print(f"🔴 Error Type: {type(exc).__name__}")
    print(f"💬 Error Message: {str(exc)}")
    print("📚 Traceback:")
    print(traceback.format_exc())
    print("=" * 60)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": 500,
            "errorCode": Error.DB_QUERY_ERROR.code,
            "message": Error.DB_QUERY_ERROR.message,
            "detail": str(exc) if hasattr(exc, '__str__') else "Database error occurred"
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    일반 예외 핸들러 (모든 예외 처리)
    """
    print("=" * 60)
    print(f"🚨 Unexpected Exception Caught!")
    print(f"📍 Path: {request.method} {request.url.path}")
    print(f"🔴 Error Type: {type(exc).__name__}")
    print(f"💬 Error Message: {str(exc)}")
    print("📚 Full Traceback:")
    print(traceback.format_exc())
    print("=" * 60)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": 500,
            "errorCode": "INTERNAL-ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
            "detail": str(exc)
        }
    )