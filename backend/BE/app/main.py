from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.main import api_router
from app.core.config import settings
from app.db.session import init_db
from app.exception.custom_exceptions import APIException
from app.exception.exception_handler import (
    api_exception_handler,
    general_exception_handler,
    sqlalchemy_exception_handler,
)


# lifespan 정의
# 앱 시작 전 한번만 실행
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

# fastapi 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="강의 학습을 도와주는 학습 AI",
    version="1.0.0",
    docs_url="/docs",    # Swagger 경로
    redoc_url="/redoc",
    lifespan=lifespan
)

# cors 설정: 다른 도메인에서 API 호출 허용
app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],         # 모든 도메인 허용
        allow_credentials=True,     # 쿠키 포함 허용
        allow_methods=["*"],        # 모든 HTTP 메서드 허용
        allow_headers=["*"]         # 모든 헤더 허용
)

# 라우터 등록
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX
)


# root
@app.get("/")
def root():
    """API 루트 엔드포인트"""
    return {
        "message": f"{settings.PROJECT_NAME} API에 오신 것을 환영합니다!",
        "version": settings.VERSION,
        "docs": "/docs"
    }

# 예외처리 핸들러 등록
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 시작
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
