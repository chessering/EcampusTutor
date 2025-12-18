import os
import shutil
import traceback
from typing import List

from fastapi import Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.exception.custom_exceptions import APIException
from app.schema.common import APIResponse
from app.schema.quiz import (
    QuizFileRequest,
    QuizListResponse,
    QuizSaveRequest,
    QuizSubmitRequest,
    QuizUrlRequest,
)
from app.service.quiz_service import QuizService

quiz_service = QuizService()

async def get_current_user_id(user: dict = Depends(get_current_user)) -> int:
    print(user)
    return user["user_id"]

# 노트 목록
async def get_quizzes(
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id)
):
    try:
        quizzes = await quiz_service.get_user_quizzes(db, current_user_id)
        
        if quizzes is None:
            quizzes = []
        return APIResponse(
            status=200,
            message="저장된 문제 목록 조회 성공",
            data=QuizListResponse(data=quizzes)
        )
    
    except APIException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        print("🔥 REAL ERROR:", type(e).__name__)
        print("🔥 ERROR MESSAGE:", str(e))
        raise HTTPException(
            status_code=500,
            detail="저장된 문제 목록을 불러오는데 실패했습니다."
        )
    

# 퀴즈 상세 정보
async def get_quiz_detail(
    quiz_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        quizzes = await quiz_service.get_quiz_detail(db, quiz_id)
        if not quizzes:
            raise HTTPException(
                status_code=404,
                detail="문제 내용을 찾을 수 없습니다."
            )
    
        return APIResponse(
                status=200,
                message="문제 내용 조회 성공",
                data=quizzes
            )
    
    except APIException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="문제의 상세정보를 불러오는데 실패했습니다."
        )

# pdf로 퀴즈 생성
async def create_quiz_file(
        files: List[UploadFile] = File(...),
        include_short_answer: bool = True,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id)
):

    temp_dir = os.path.join(settings.SUMMARY_WORKDIR, "temp_uploads", str(current_user_id))
    os.makedirs(temp_dir, exist_ok=True)
    
    saved_paths = []
    
    try:
        
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(file_path)
        
        print(f"✅ {len(saved_paths)}개 파일 임시 저장 완료: {[os.path.basename(p) for p in saved_paths]}")
        
        quiz = await quiz_service.create_quiz_file(
            db=db,
            user_id=current_user_id,
            files=saved_paths,
            include_short_answer=include_short_answer,
            total_questions=10
        )

        return APIResponse(
            status=202,
            message="PDF로 퀴즈 생성을 시작했습니다. 잠시 후 상태를 확인해주세요.",
            data=quiz
        )
    
    except APIException as e:
        print("=" * 60)
        print("🔥 API Exception in create_quiz_file")
        print(f"🔴 Status Code: {e.status_code}")
        print(f"💬 Detail: {e.detail}")
        print("=" * 60)
        
        for path in saved_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🗑️ 에러로 인한 임시 파일 정리: {os.path.basename(path)}")
            except Exception as cleanup_err:
                print(f"[WARN] 임시 파일 정리 실패: {path}, {cleanup_err}")
        
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        print("=" * 60)
        print("🔥 UNEXPECTED ERROR in create_quiz_file")
        print(f"🔥 Error Type: {type(e).__name__}")
        print(f"🔥 Error Message: {str(e)}")
        print("📚 Full Traceback:")
        print(traceback.format_exc())
        print("=" * 60)
        
        for path in saved_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🗑️ 에러로 인한 임시 파일 정리: {os.path.basename(path)}")
            except Exception as cleanup_err:
                print(f"[WARN] 임시 파일 정리 실패: {path}, {cleanup_err}")
        
        raise HTTPException(
            status_code=500,
            detail="pdf로 퀴즈를 만드는데 실패했습니다."
        )
    
# url로 퀴즈 생성
async def create_quiz_url(
        request: QuizUrlRequest,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id)
):
    try:
        quiz = await quiz_service.create_quiz_url(
            db=db,
            user_id=current_user_id,
            include_short_answer=request.include_short_answer,
            url=request.url
        )

        return APIResponse(
            status=202,  
            message="URL로 퀴즈 생성을 시작했습니다. 잠시 후 상태를 확인해주세요.",
            data=quiz
        )

    except APIException as e:
        print("=" * 60)
        print("🔥 API Exception in create_quiz_url")
        print(f"🔴 Status Code: {e.status_code}")
        print(f"💬 Detail: {e.detail}")
        print("=" * 60)
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        print("=" * 60)
        print("🔥 UNEXPECTED ERROR in create_quiz_url")
        print(f"🔥 Error Type: {type(e).__name__}")
        print(f"🔥 Error Message: {str(e)}")
        print("📚 Full Traceback:")
        print(traceback.format_exc())
        print("=" * 60)
        raise HTTPException(
            status_code=500,
            detail="url로 퀴즈를 만드는데 실패했습니다."
        )


# 문제 저장(제목 입력)
async def save_quiz_answers(
        request: QuizSaveRequest,
        db: AsyncSession = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id)
):
    try:
        result = await quiz_service.save_quiz_answers(
            db=db,
            quiz_id=request.quiz_id,
            user_id=current_user_id,
            title=request.title
        )
        
        return APIResponse(
            status=200,
            message="퀴즈가 성공적으로 저장되었습니다.",
            data=result
        )
        
    except APIException as e:
        print("=" * 60)
        print("🔥 API Exception in save_quiz_answers")
        print(f"🔴 Status Code: {e.status_code}")
        print(f"💬 Detail: {e.detail}")
        print("=" * 60)
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        print("=" * 60)
        print("🔥 UNEXPECTED ERROR in save_quiz_answers")
        print(f"🔥 Error Type: {type(e).__name__}")
        print(f"🔥 Error Message: {str(e)}")
        print("📚 Full Traceback:")
        print(traceback.format_exc())
        print("=" * 60)
        print(f"❌ 퀴즈 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="퀴즈 저장에 실패했습니다."
        )


# 문제 정답 제출
async def submit_quiz(
    request: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    
    try:
        
        # todo: 작성중
        result = await quiz_service.submit_answer(
            db=db,
            quiz_id=request.quiz_id,
            answers=request.answers
        )
        
        return APIResponse(
            status=200,
            message="퀴즈가 성공적으로 저장되었습니다.",
            data=result
        )
        
    except APIException as e:
        print("=" * 60)
        print("🔥 API Exception in submit_quiz")
        print(f"🔴 Status Code: {e.status_code}")
        print(f"💬 Detail: {e.detail}")
        print("=" * 60)
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        print("=" * 60)
        print("🔥 UNEXPECTED ERROR in submit_quiz")
        print(f"🔥 Error Type: {type(e).__name__}")
        print(f"🔥 Error Message: {str(e)}")
        print("📚 Full Traceback:")
        print(traceback.format_exc())
        print("=" * 60)
        print(f"❌ 정답 제출 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="정답 제출에 실패했습니다."
        )


async def get_task_status(task_id: str):
    """Celery 작업 상태 확인"""
    status = await quiz_service.get_task_status(task_id)
    
    return APIResponse(
        status=200,
        message="작업 상태 조회 성공",
        data=status
    )