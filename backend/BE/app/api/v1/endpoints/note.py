
import shutil
from typing import List

from app.core.base_router import BaseRouter
from app.schema.common import APIResponse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import os

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.core.config import settings 
from app.schema.note import (
    FileSummaryRequest,
    UrlSummaryRequest, 
    FileFillBlankRequest,
    UrlFillBlankRequest,
)
from app.service.note_service import NoteService
from app.auth.dependencies import get_current_user
from app.schema.common import APIResponse


note_service = NoteService()

async def get_current_user_id(user: dict = Depends(get_current_user)) -> int:
    return user["user_id"]

# PDF 파일들로 요약 노트 생성
async def create_summary_from_files(
    files: List[UploadFile] = File(...),
    current_user_id: int = Depends(get_current_user_id)
):
    
    temp_dir = os.path.join(settings.SUMMARY_WORKDIR, "temp_uploads", str(current_user_id))
    os.makedirs(temp_dir, exist_ok=True)
    saved_paths = []
    
    # 파일 저장
    for file in files:
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(file_path)
                
    result = await note_service.create_summary_from_files(
        user_id=current_user_id,
        files=saved_paths
    )
        
    return APIResponse(
        status=200,
        message="PDF 파일로 요약 노트가 생성되었습니다.",
        data=result
    )


async def create_summary_from_url(
    request: UrlSummaryRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await note_service.create_summary_from_url(
        user_id=current_user_id,
        url=request.url,
        db=db
    )
    
    return APIResponse(
        status=200,
        message="URL로 요약 노트가 생성되었습니다.",
        data=result
    )
    
async def create_blank_from_files(
    files: List[UploadFile] = File(...),
    current_user_id: int = Depends(get_current_user_id)
):
    temp_dir = os.path.join(settings.SUMMARY_WORKDIR, "temp_uploads", str(current_user_id))
    os.makedirs(temp_dir, exist_ok=True)
    
    saved_paths = []
    
    for file in files:
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(file_path)
        
    result = await note_service.create_blank_from_files(
        user_id=current_user_id,
        files=saved_paths
    )
        
    return APIResponse(
        status=200,
        message="PDF 파일로 빈칸 채우기 노트가 생성되었습니다.",
        data=result
    )


async def create_blank_from_url(
    request: UrlFillBlankRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db) 
):
    result = await note_service.create_blank_from_url(
        user_id=current_user_id,
        url=request.url,
        db=db
    )
    
    return APIResponse(
        status=200,
        message="URL로 빈칸 채우기 노트가 생성되었습니다.",
        data=result
    )

# 생성된 PDF 다운
async def download_pdf(job_id: str, filename: str):
    file_path = os.path.join(settings.SUMMARY_WORKDIR, f"job_{job_id}", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF를 찾을 수 없습니다")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )

async def get_note_task_status(
    task_id: str,
    current_user_id: int = Depends(get_current_user_id)
):
    result = await note_service.get_task_status(task_id)
    return APIResponse(
        status=200,
        message="작업 상태 조회 성공",
        data=result
    )