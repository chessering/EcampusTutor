from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# base 클래스 생성
Base = declarative_base()

# 비동기 엔진 생성
engine = create_async_engine(settings.DATABASE_URL, echo=True, future = True)

# 비동기 세션 메이커 구성
# 객체를 세션에 연결해 유지
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# 비동기 db 세션을 얻기 위한 종속성 (fastapi의 'Depends(get_db)'에서 사용)
# 요청마다 DB 세션을 자동으로 열고 닫는 역할
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 데이터 베이스 초기화 (테이블 생성)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)