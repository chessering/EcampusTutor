from datetime import datetime
from typing import List, Optional, Union

from app.util.base import CamelCaseModel


# 퀴즈 제목
class QuizItem(CamelCaseModel):
    quiz_id: int
    title: str
    is_saved: bool

# 저장된 퀴즈 제목 리스트 응답 DTO
class QuizListResponse(CamelCaseModel):
    data: List[QuizItem] = []

# 저장된 퀴즈 제목 리스트
class QuestionResponse(CamelCaseModel):
    question_number: int
    question_text: str
    question_type: str    # MULTIPLE(객관식) | SHORT(주관식)
    choices: List[str]
    correct_answer: int | str
    user_answer: int | str | None = None
    is_correct: bool
    explanation: Optional[str] = ""


# 저장된 퀴즈 상세 정보
class QuizDetailResponse(CamelCaseModel):
    quiz_id: int
    total_questions: int
    correct_number: int
    created_at: str  
    questions: List[QuestionResponse]


# 예상 문제 정답 - PDF파일 용
class QuestionItem(CamelCaseModel):
    question_number: int
    question_text: str
    question_type: str  # MULTIPLE or SHORT
    choices: Optional[List[str]] = None  # 주관식이면 None

class QuizFileRequest(CamelCaseModel):
    files: List[str]
    include_short_answer: bool = False  # 단답형

class QuizFileResponse(CamelCaseModel):
    quiz_id: int
    task_id: Optional[str] = None 
    status: str
    total_questions: int
    created_at: str
    questions: List[QuestionItem]

# 예상 문제 정답 - url용
class QuizUrlRequest(CamelCaseModel):
    url: str
    include_short_answer: bool

class QuizUrlResponse(CamelCaseModel):
    quiz_id: int
    task_id: str
    status: str
    total_questions: int
    created_at: str
    questions: List[QuestionItem]

# 예상 문제 정답 제출
# request
class QuizSubmitItem(CamelCaseModel):
    question_number: int
    question_type: str
    answer: str | int

class QuizSubmitRequest(CamelCaseModel):
    quiz_id: int
    answers: List[QuizSubmitItem]

# response
class QuizSubmitQuestionItem(CamelCaseModel):
    question_number: int
    question_text: str
    question_type: str
    choices: Optional[List[str]]
    correct_answer: str | int
    user_answer: Optional[Union[int, str]] = None
    is_correct: bool
    explanation: Optional[str]

class QuizSubmitResponse(CamelCaseModel):
    total_questions: int
    correct_number: int
    score: int                   
    created_at: str
    questions: List[QuizSubmitQuestionItem]


# 예상 문제 풀이 저장
class QuizSaveRequest(CamelCaseModel):
    quiz_id: int
    title: str

class QuizSaveResponse(CamelCaseModel):
    quiz_id: int
    title: str
    is_saved: bool
    created_at: str

