from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exception.custom_exceptions import APIException
from app.exception.error_code import Error
from app.model.question import Question
from app.model.quiz import Quiz
from app.repository.quiz_repository import QuizRepository
from app.schema.quiz import (
    QuestionItem,
    QuestionResponse,
    QuizDetailResponse,
    QuizFileResponse,
    QuizItem,
    QuizSaveResponse,
    QuizSubmitItem,
    QuizSubmitQuestionItem,
    QuizSubmitResponse,
    QuizUrlResponse,
)


class QuizService:

    def __init__(self):
        self.quiz_repo = QuizRepository()

    # 사용자의 노트 목록 조회
    async def get_user_quizzes(self, db: AsyncSession, user_id: int) -> List[QuizItem]:
        quizzes = await self.quiz_repo.get_quizzes(db, user_id)

        return [
            QuizItem(
                quiz_id=quiz.quiz_id,
                title=quiz.title,
                is_saved=quiz.is_saved
            )
            for quiz in quizzes
        ]
    
    # 노트 상세 정보 조회
    async def get_quiz_detail(self, db: AsyncSession, quiz_id: int) -> QuizDetailResponse:
        
        try:
            quiz = await self.quiz_repo.get_quiz_by_id(db, quiz_id)
            if not quiz:
                return None
            
            return QuizDetailResponse(
                quiz_id=quiz.quiz_id,
                total_questions=quiz.total_questions,
                correct_number=quiz.correct_number,
                created_at=quiz.created_at.isoformat(),
                questions=[
                    QuestionResponse(
                        question_number=q.question_number,
                        question_text=q.question_text,
                        question_type=q.question_type,
                        choices=q.choices or [],
                        correct_answer=int(q.correct_answer) if q.question_type == "MULTIPLE" else q.correct_answer,
                        user_answer=int(q.user_answer) if q.question_type == "MULTIPLE" and q.user_answer else q.user_answer,
                        is_correct=q.is_correct,
                        explanation=q.explanation or ""
                    )
                    for q in quiz.questions
                ]
            )
        
        except Exception as e:
            print("=" * 60)
            print(f"🔥 ERROR in get_quiz_detail")
            print(f"🔥 Error Type: {type(e).__name__}")
            print(f"🔥 Error Message: {str(e)}")
            import traceback
            print("📚 Full Traceback:")
            print(traceback.format_exc())
            print("=" * 60)
            raise
    
    # pdf로 퀴즈 생성
    async def create_quiz_file(
        self, 
        db: AsyncSession, 
        user_id: int, 
        files: List[str], 
        include_short_answer: bool, 
        total_questions: int
    ) -> QuizFileResponse:

        from app.tasks.quiz_tasks import generate_quiz_task
    
        if not files:
            raise APIException(400, Error.FILE_NOT_FOUND)
        if total_questions <= 0:
            raise APIException(400, Error.AUTH_INVALID_TOKEN)

        try:
            new_quiz = Quiz(
                user_id=user_id,
                title="",
                is_saved=False,
                status="PROCESSING",
                include_short_answer=include_short_answer,
                total_questions=0
            )
           
            db.add(new_quiz)
            await db.commit()
            await db.refresh(new_quiz)
            
            # Celery 작업 시작
            task = generate_quiz_task.apply_async(
                args=[new_quiz.quiz_id, user_id, files, include_short_answer]
            )
            
            return QuizFileResponse(
                quiz_id=new_quiz.quiz_id,
                task_id=task.id,
                status="PROCESSING",
                total_questions=0,
                created_at=datetime.now().strftime("%Y-%m-%d"),
                questions=[]
            )
    
        except APIException:
            raise
        except SQLAlchemyError as e:
            print(f"🔥 Database Error: {str(e)}")
            raise APIException(500, Error.DB_QUERY_ERROR)
        except Exception as e:
            print("🔥 Unexpected error in create_quiz_from_file:", str(e))
            raise APIException(500, Error.QUIZ_CREATION_FAILED)
    """
    # url로 퀴즈 생성
    async def create_quiz_url(self, 
            db: AsyncSession,
            user_id: int, 
            url: str,
            include_short_answer: bool,
            total_questions: int = 10
    ) -> QuizUrlResponse:
        
        if not url:
            raise APIException(400, Error.URL_NOT_FOUND)
        
        try:
            # TODO: GPT API로 문제 생성
            # questions = await self._create_questions(url, total_questions, include_short_answer)
            
            
            # 임시 더미 데이터
            questions = [
                {
                    "questionNumber": 1,
                    "questionText": "URL 샘플 문제입니다",
                    "questionType": "SHORT",
                    "choices": [],
                    "correctAnswer": "정답",
                    "explanation": "해설입니다"
                }
            ]
            
            total_questions = len(questions)
            quiz: Quiz = await self.quiz_repo.create_quiz_url(
                db=db,
                user_id=user_id,
                include_short_answer=include_short_answer,
                total_questions=total_questions,
                questions=questions,
            )

            result = QuizUrlResponse(
                quiz_id=quiz.quiz_id,
                status="COMPLETED",
                total_questions=quiz.total_questions,
                created_at=quiz.created_at.strftime("%Y-%m-%d"),
                questions=[
                    QuestionItem(
                        question_number=q["questionNumber"],
                        question_text=q["questionText"],
                        question_type=q["questionType"],
                        choices=q.get("choices"),
                    )
                    for q in questions
                ],           
            )
            return result
        except APIException:
            raise
        except SQLAlchemyError as e:
            print(f"🔥 Database Error: {str(e)}")
            raise APIException(500, Error.DB_QUERY_ERROR)
        except Exception as e:
            print("🔥 Unexpected error in create_quiz_from_file:", str(e))
            raise APIException(500, Error.QUIZ_CREATION_FAILED)
    
    """
    async def create_quiz_url(
        self,
        db: AsyncSession,
        user_id: int,
        url: str,
        include_short_answer: bool,
        total_questions: int = 10
    ) -> QuizUrlResponse:
        """
        Canvas URL로 퀴즈 생성 (Celery 비동기)
        """
        from app.tasks.quiz_tasks import generate_quiz_from_url_task
        
        if not url:
            raise APIException(400, Error.URL_NOT_FOUND)
        
        # 1. Quiz를 PROCESSING 상태로 먼저 저장
        new_quiz = Quiz(
            user_id=user_id,
            title="",
            is_saved=False,
            status="PROCESSING",
            include_short_answer=include_short_answer,
            total_questions=0
        )
        db.add(new_quiz)
        await db.commit()
        await db.refresh(new_quiz)
        
        # 2. Celery 작업 시작
        task = generate_quiz_from_url_task.apply_async(
            args=[new_quiz.quiz_id, user_id, url, include_short_answer]
        )
        
        # 3. 즉시 반환
        return QuizUrlResponse(
            quiz_id=new_quiz.quiz_id,
            task_id=task.id,  # ✅ task_id 추가
            status="PROCESSING",
            total_questions=0,
            created_at=datetime.now().strftime("%Y-%m-%d"),
            questions=[]
        )
    
    async def get_task_status(self, task_id: str):
        """Celery 작업 상태 확인"""
        from celery.exceptions import TimeLimitExceeded, TimeoutError
        from celery.result import AsyncResult

        from app.celery_config import celery_app
        
        task = AsyncResult(task_id, app=celery_app)
        
        try:
            # 작업 완료 여부 확인
            if task.ready():
                # 성공적으로 완료된 경우
                if task.successful():
                    result = task.result
                    # result가 dict인지 확인
                    if isinstance(result, dict):
                        return {
                            "status": result.get('status', 'COMPLETED'),
                            "quiz_id": result.get('quiz_id'),
                            "total_questions": result.get('total_questions'),
                            "progress": 100
                        }
                    else:
                        return {
                            "status": "COMPLETED",
                            "progress": 100,
                            "message": str(result)
                        }
                # 실패한 경우
                else:
                    # task.info는 예외 객체일 수 있음
                    error_info = task.info
                    error_message = str(error_info) if error_info else "Unknown error"
                    
                    return {
                        "status": "FAILED",
                        "error": error_message,
                        "progress": 0
                    }
            
            # 아직 진행 중인 경우
            else:
                info = task.info or {}
                
                # info가 dict가 아닌 경우 (예외 객체 등)
                if not isinstance(info, dict):
                    return {
                        "status": "PROCESSING",
                        "progress": 0,
                        "message": "처리 중..."
                    }
                
                return {
                    "status": "PROCESSING",
                    "progress": info.get('progress', 0),
                    "message": info.get('status', '처리 중...')
                }
        
        except (TimeoutError, TimeLimitExceeded) as e:
            return {
                "status": "FAILED",
                "error": f"작업 시간 초과: {str(e)}",
                "progress": 0
            }
        
        except Exception as e:
            print(f"🔥 get_task_status Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "UNKNOWN",
                "error": f"상태 조회 실패: {str(e)}",
                "progress": 0
            }
        
    # 문제 저장
    async def save_quiz_answers(
        self,
        db: AsyncSession,
        quiz_id: int,
        user_id: int,
        title: str
    ) -> QuizSaveResponse :
        
        try:
            
            # quiz = await self.quiz_repo.get_quiz_by_id(db, quiz_id)
            # 제목 저장
            saved_quiz = await self.quiz_repo.save_quiz_answers(
                db=db,
                quiz_id=quiz_id,
                title=title,
                user_id=user_id
            )
            
            if not saved_quiz:
                raise APIException(500, Error.QUIZ_INTERNAL_ERROR)

            return QuizSaveResponse(
                quiz_id=saved_quiz.quiz_id,
                title=saved_quiz.title,
                is_saved=saved_quiz.is_saved,
                created_at=saved_quiz.created_at.strftime("%Y-%m-%d")
            )
            
        except APIException:
            raise
        except SQLAlchemyError as e:
            print(f"🔥 Database Error: {str(e)}")
            raise APIException(500, Error.DB_QUERY_ERROR)
        except Exception as e:
            print("🔥 Unexpected error in save_quiz_answers:", str(e))
            raise APIException(500, Error.QUIZ_INTERNAL_ERROR)


    # 정답 제출
    async def submit_answer(
            self,
            db: AsyncSession,
            quiz_id: int,
            answers: List[QuizSubmitItem]
    ) -> QuizSubmitResponse:
        
        try:
            questions: List[Question] = await self.quiz_repo.submit_quiz(
                db=db,
                quiz_id=quiz_id,
                answers=answers
            )

            total = len(questions)
            correct_cnt = 0
            graded_questions: List[QuizSubmitQuestionItem] = []

            for q in questions:
                if q.user_answer is None:
                    is_correct = False
                elif q.question_type == "MULTIPLE":
                    is_correct = int(q.user_answer) == int(q.correct_answer)
                else:
                    is_correct = q.user_answer.strip().lower() == q.correct_answer.strip().lower()

                if is_correct:
                    correct_cnt += 1

                graded_questions.append(
                    QuizSubmitQuestionItem(
                        question_number=q.question_number,
                        question_text=q.question_text,
                        question_type=q.question_type,
                        choices=q.choices,
                        correct_answer=q.correct_answer,
                        user_answer=q.user_answer,
                        is_correct=is_correct,
                        explanation=q.explanation
                    )
                )

            return QuizSubmitResponse(
                total_questions=total,
                correct_number=correct_cnt,
                score=int(correct_cnt / total * 100) if total > 0 else 0,
                created_at=datetime.now().isoformat(),
                questions=graded_questions
            )

        except APIException:
            raise
        except SQLAlchemyError as e:
            print(f"🔥 Database Error: {str(e)}")
            raise APIException(500, Error.DB_QUERY_ERROR)
        except Exception as e:
            print("=" * 60)
            print("🔥 Unexpected error in submit_answer:")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print("=" * 60)
            raise APIException(500, Error.QUIZ_INTERNAL_ERROR)