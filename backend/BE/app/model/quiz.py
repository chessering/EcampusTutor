from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.util.datetime_utils import now_kst


class Quiz(Base):
    __tablename__ = "quiz"

    quiz_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("user.user_id"), nullable=False)
    status = Column(String(20), default="PROCESSING")
    title = Column(String(200), nullable=True, comment="사용자가 입력한 제목")
    include_short_answer = Column(Boolean, nullable=True, comment="단답형 포함인지")
    correct_number = Column(Integer, nullable=True, default=0, comment="맞춘 문제 수")
    total_questions = Column(Integer, nullable=True, comment="전체 문제 수")
    is_saved = Column(Boolean, nullable=False, default=False, comment="문제를 저장했는 지")
    created_at = Column(DateTime(timezone=True), default=now_kst, server_default=func.now(), comment="저장 시간")
    
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")