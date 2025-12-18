import json
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.model.question import Question
from app.model.quiz import Quiz
from app.schema.quiz import QuizSubmitItem


class QuizRepository:

    # 유저의 저장된 퀴즈 목록 조회
    async def get_quizzes(self, db: AsyncSession, user_id: int) -> List[Quiz]:
        result = await db.execute(
            select(Quiz)
            .where(
                Quiz.user_id == user_id,
                   Quiz.is_saved == True)
            .order_by(desc(Quiz.created_at))  # 최신순 정렬
            )
        return result.scalars().all()
    
    # 저장된 퀴즈 내용 상세 조회
    async def get_quiz_by_id(self, db: AsyncSession, quiz_id: int) -> Quiz | None:

        # 퀴즈 조회
        result = await db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .where(Quiz.quiz_id == quiz_id)
        )
        quiz = result.scalar_one_or_none()  # 하나 or None
        if not quiz:
            print(f"⚠️ Quiz not found: quiz_id={quiz_id}")
            return None

        print(f"✅ Quiz found!")
        print(f"   - quiz_id: {quiz.quiz_id}")
        print(f"   - title: {quiz.title}")
        print(f"   - is_saved: {quiz.is_saved}")
        print(f"   - total_questions: {quiz.total_questions}")
        print(f"   - correct_number: {quiz.correct_number}")
        print(f"   - created_at: {quiz.created_at}")
        print(f"   - questions loaded: {len(quiz.questions) if quiz.questions else 0}")
        
        # questions 상세 확인
        if quiz.questions:
            print(f"\n📋 Questions detail:")
            for q in quiz.questions:
                print(f"   Q{q.question_number}: type={q.question_type}, "
                      f"correct={q.correct_answer}, user={q.user_answer}, "
                      f"is_correct={q.is_correct}")
                print(f"      choices: {q.choices}")
                print(f"      explanation: {q.explanation}")
        else:
            print(f"⚠️ No questions found for quiz_id={quiz_id}")
            
        # 질문 목록 조회
        if quiz.questions:
            quiz.questions.sort(key=lambda q: q.question_number)
            
        return quiz
    

    # 예상 문제 생성(파일/URL 공통)
    async def create_quiz(
        self, 
        db: AsyncSession, 
        user_id: int,
        include_short_answer: bool,
        total_questions: int,
        questions: List[dict]
    ) -> Quiz:
        
        try:
            new_quiz = Quiz(
                user_id=user_id,
                title="",
                is_saved=False,
                include_short_answer=include_short_answer,
                total_questions=total_questions
            )

            db.add(new_quiz)
            await db.flush() # 변경 사항 반영 but 커밋x
            
            # question 생성
            for q in questions:
                explanation_value = q.get("explanation")
                print(f"   - explanation: {explanation_value} (type: {type(explanation_value)})")
                
                question = Question(
                    quiz_id = new_quiz.quiz_id,
                    question_number=q["questionNumber"],
                    question_text=q["questionText"],
                    question_type=q["questionType"],
                    choices=q.get("choices", []),
                    correct_answer=str(q["correctAnswer"]),
                    explanation=q.get("explanation", "")
                )
                db.add(question)

            await db.commit()
            await db.refresh(new_quiz)

            print("🔸 db.commit() 호출...")
            await db.commit()
            
            print("🔸 db.refresh() 호출...")
            await db.refresh(new_quiz)
            
            print(f"✅ Quiz 저장 완료! ID: {new_quiz.quiz_id}")
            return new_quiz

        except Exception as e:
            await db.rollback()
            print("=" * 60)
            print(f"🔥 ERROR in create_quiz")
            print(f"🔥 Error Type: {type(e).__name__}")
            print(f"🔥 Error Message: {str(e)}")
            print(f"🔥 Error repr: {repr(e)}")
            
            # SQLAlchemy 에러인 경우 더 자세한 정보
            if hasattr(e, 'orig'):
                print(f"🔥 Original Error: {e.orig}")
            if hasattr(e, 'params'):
                print(f"🔥 Params: {e.params}")
            if hasattr(e, 'statement'):
                print(f"🔥 Statement: {e.statement}")
            
            import traceback
            print("📚 Full Traceback:")
            print(traceback.format_exc())
            print("=" * 60)
            raise   
    
    # 예상 문제 생성(파일용)
    async def create_quiz_file(
            self, 
            db: AsyncSession, 
            user_id: int,
            include_short_answer: bool,
            total_questions: int,
            questions: List[dict]
    ) -> Quiz:
        return await self.create_quiz(
            db, user_id, include_short_answer, total_questions, questions
        )
        

    # 예상 문제 생성(url용)
    async def create_quiz_url(
        self,
        db: AsyncSession,
        user_id: int,
        include_short_answer: bool,
        total_questions: int,
        questions: List[dict]
    ) -> Quiz:
        # 위의 파일용과 동일
        return await self.create_quiz(
            db, user_id, include_short_answer, total_questions, questions
        )

    # 예상 문제 풀이 저장
    async def save_quiz_answers(
            self,
            db: AsyncSession,
            quiz_id,
            title: str,
            user_id: int
    ) -> Optional[Quiz]:
        
        # 퀴즈에 제목 저장 및 is_saved = True
        try:
            stmt = select(Quiz).where(
                Quiz.quiz_id == quiz_id,
                Quiz.user_id==user_id
            )
            result = await db.execute(stmt)
            quiz = result.scalar_one_or_none()

            if not quiz:
                return None
            
            quiz.title = title
            quiz.is_saved = True
            
            await db.commit()
            await db.refresh(quiz)
            return quiz
        
        except Exception as e:
            await db.rollback()
            print(f"🔥 Repository Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise e

    # 예상 문제 정답 제출(사용자 답안)
    async def submit_quiz(
            self,
            db: AsyncSession,
            quiz_id: int,
            answers: List[QuizSubmitItem]
    ) -> List[Question]:
        
        try:
            for answer in answers:
                question_number = answer.question_number
                user_answer = answer.answer
                
                stmt = select(Question).where(
                    Question.quiz_id == quiz_id,
                    Question.question_number == question_number
                )

                result = await db.execute(stmt)
                question = result.scalar_one_or_none()
                
                if question:
                    # question.user_answer = str(user_answer)
                
                    # 정답 여부
                    if question.question_type == "MULTIPLE":
                        # 객관식(숫자 비교)
                        question.is_correct = (
                            str(user_answer).strip() == str(question.correct_answer)
                        )
                        
                    else:
                        # 단답형
                        question.is_correct = (
                            str(user_answer).strip().lower() ==
                            str(question.correct_answer).strip().lower()
                        )

            # 정답 갯수
            correct_count_result = await db.execute(
                select(Question).where(
                    Question.quiz_id == quiz_id,
                    Question.is_correct == True
                )
            )
            
            correct_count = len(correct_count_result.scalars().all())
            
            print(f"✅ 정답 개수: {correct_count}")
            
            stmt = update(Quiz).where(
                Quiz.quiz_id == quiz_id
            ).values(
                correct_number = correct_count
            )
            
            await db.execute(stmt)
            await db.commit()
            
            update_result = await db.execute(
                    select(Question)
                    .where(Question.quiz_id == quiz_id)
                    .order_by(Question.question_number)
                )
            questions = update_result.scalars().all()
            return questions

        except Exception as e:
            await db.rollback()
            print("=" * 60)
            print("🔥 Repository Error in submit_quiz")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print("=" * 60)
            raise 
