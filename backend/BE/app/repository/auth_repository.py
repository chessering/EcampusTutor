from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.model.user import User


class AuthRepository:

    async def get_by_id(self, db: AsyncSession, id: str) -> User | None:
        result = await db.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_user(self, db: AsyncSession, id: str, hashed_password: str) -> User:
        user = User(id=id, password=hashed_password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    