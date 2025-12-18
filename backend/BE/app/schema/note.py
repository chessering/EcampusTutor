
from typing import List

from pydantic import BaseModel, Field

from app.util.base import CamelCaseModel

# 파일로 요약노트 생성
class FileSummaryRequest(BaseModel):
    files: List[str] = Field(..., min_items=1, max_items=5, description="PDF 파일 경로 (최대 5개)")

class FileSummaryResponse(CamelCaseModel):
    task_id: str
    status: str
    pdf_url: str
    created_at: str

# url로 요약노트 생성
class UrlSummaryRequest(CamelCaseModel):
    url: str = Field(..., description="Canvas LMS 강의 URL")

class UrlSummaryResponse(CamelCaseModel):
    task_id: str
    status: str
    pdf_url: str
    created_at:str

# 파일로 빈칸 채우기 노트 생성
class FileFillBlankRequest(CamelCaseModel):
    files: List[str] = Field(..., max_items=5, description="PDF 파일 경로 (최대 5개)")

class FileFillBlankResponse(CamelCaseModel):
    task_id: str
    status: str
    pdf_url: str
    created_at: str

# url로 빈칸 채우기 노트 생성
class UrlFillBlankRequest(CamelCaseModel):
    url: str = Field(..., description="Canvas LMS 강의 URL")

class UrlFillBlankResponse(CamelCaseModel):
    task_id: str
    status: str
    pdf_url: str
    created_at: str