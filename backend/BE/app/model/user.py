from sqlalchemy import BigInteger, Column, DateTime, String, func

from app.db.session import Base
from app.util.datetime_utils import now_kst


class User(Base):
    __tablename__ = "user"

    user_id = Column(BigInteger, primary_key=True, index=True)
    id = Column(String(100), nullable=False,  unique=True, comment="아이디")
    password = Column(String(255), nullable=False, comment="암호화된 비밀번호")
    created_at = Column(DateTime(timezone=True), default=now_kst, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst, nullable=False, server_default=func.now())
