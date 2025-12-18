from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.util.datetime_utils import now_kst


class Question(Base):
    __tablename__ = "question"

    question_id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    quiz_id = Column(BigInteger, ForeignKey("quiz.quiz_id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False, comment="문제 번호")
    question_text = Column(Text, nullable=False, comment="문제")
    question_type = Column(String(20), nullable=False, comment="MULTIPLE or SHORT")
    choices = Column(JSON, nullable=True, comment="선택지 (객관식만)")
    correct_answer = Column(String(500), nullable=False, comment="정답")
    user_answer = Column(String(500), nullable=True, comment="사용자 답변")
    is_correct = Column(Boolean, nullable=True, default=False, comment="정답 여부")
    explanation = Column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")