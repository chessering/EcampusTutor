import asyncio
import os, time, subprocess
from datetime import datetime
from typing import List
from app.schema.note import (
    FileSummaryResponse,
    UrlSummaryResponse,
    FileFillBlankResponse,
    UrlFillBlankResponse
)
from app.exception.custom_exceptions import APIException
from app.exception.error_code import Error
from app.core.config import settings
from PyPDF2 import PdfMerger
from app.model.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys

class NoteService:
    
    def __init__(self):
        self.workdir = settings.SUMMARY_WORKDIR
        self.pdf_script = settings.PDF_SCRIPT_PATH
        self.url_script = settings.URL_SCRIPT_PATH
        self.canvas_downloader_script = settings.CANVAS_DOWNLOADER_PATH
        
        self.python_executable = sys.executable
        os.makedirs(self.workdir, exist_ok=True)
    
    # 요약 노트 생성
    async def create_summary_from_files(
        self,
        user_id: int,
        files: List[str]
    ) -> FileSummaryResponse:
        
        from app.tasks.note_tasks import generate_summary_task
        
        if not files or len(files) > 5:
            raise APIException(400, Error.FILE_NOT_FOUND)

        task = generate_summary_task.apply_async(
            args=[user_id, files, "summary"]
        )
            
        return FileSummaryResponse(
            task_id=task.id,
            status="PROCESSING",
            pdf_url="",
            created_at=datetime.now().strftime("%Y-%m-%d")
        )
        
    async def create_summary_from_url(
        self, 
        user_id: int,
        url: str,
        db: AsyncSession
    ) -> UrlSummaryResponse:
        
        from app.tasks.note_tasks import generate_summary_from_url_task
        
        if not url:
            raise APIException(400, Error.URL_NOT_FOUND)
    
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.id or not user.password:
            raise APIException(400, Error.CANVAS_CREDENTIALS_MISSING)
        
        canvas_pw = settings.fernet.decrypt(user.password.encode()).decode()
        
        # Celery 작업 시작
        task = generate_summary_from_url_task.apply_async(
            args=[user_id, url, user.id, canvas_pw, "summary"]
        )
        
        return UrlSummaryResponse(
            task_id=task.id,
            status="PROCESSING",
            pdf_url="",
            created_at=datetime.now().strftime("%Y-%m-%d")
        )
        
  
    # 빈칸 채우기
    async def create_blank_from_files(
        self,
        user_id: int,
        files: List[str]
    ) -> FileFillBlankResponse:
        
        from app.tasks.note_tasks import generate_summary_task
        if not files or len(files) > 5:
            raise APIException(400, Error.FILE_NOT_FOUND)
        
        # Celery 작업 시작
        task = generate_summary_task.apply_async(
            args=[user_id, files, "blank"]
        )
        
        return FileFillBlankResponse(
            task_id=task.id,
            status="PROCESSING",
            pdf_url="",
            created_at=datetime.now().strftime("%Y-%m-%d")
        )
    
        
    async def create_blank_from_url(
        self, 
        user_id: int,
        url: str,
        db: AsyncSession
    ) -> UrlFillBlankResponse:
        
        from app.tasks.note_tasks import generate_summary_from_url_task
        
        # 사용자 Canvas 인증 정보
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.id or not user.password:
            raise APIException(400, Error.CANVAS_CREDENTIALS_MISSING)
        
        canvas_pw = settings.fernet.decrypt(user.password.encode()).decode()
        
        # Celery 작업 시작
        task = generate_summary_from_url_task.apply_async(
            args=[user_id, url, user.id, canvas_pw, "blank"]
        )
        
        return UrlFillBlankResponse(
            task_id=task.id,
            status="PROCESSING",
            pdf_url="",
            created_at=datetime.now().strftime("%Y-%m-%d")
        )
    
    async def get_task_status(self, task_id: str):
        """Celery 작업 상태 확인 (Quiz와 동일)"""
        from celery.result import AsyncResult

        from app.celery_config import celery_app
        
        task = AsyncResult(task_id, app=celery_app)
        
        try:
            if task.ready():
                if task.successful():
                    result = task.result
                    if isinstance(result, dict):
                        return {
                            "status": result.get('status', 'COMPLETED'),
                            "pdf_url": result.get('pdf_url'),
                            "job_id": result.get('job_id'),
                            "progress": 100
                        }
                    else:
                        return {
                            "status": "COMPLETED",
                            "progress": 100,
                            "message": str(result)
                        }
                else:
                    error_info = task.info
                    error_message = str(error_info) if error_info else "Unknown error"
                    
                    return {
                        "status": "FAILED",
                        "error": error_message,
                        "progress": 0
                    }
            else:
                info = task.info or {}
                
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
        
        except Exception as e:
            print(f"🔥 get_task_status Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "UNKNOWN",
                "error": f"상태 조회 실패: {str(e)}",
                "progress": 0
            }