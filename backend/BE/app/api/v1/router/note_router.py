from app.core.base_router import BaseRouter
from app.schema.common import APIResponse
from app.schema.note import (
    FileSummaryRequest, FileSummaryResponse,
    UrlSummaryRequest, UrlSummaryResponse,
    FileFillBlankRequest, FileFillBlankResponse,
    UrlFillBlankRequest, UrlFillBlankResponse
)
from fastapi.responses import FileResponse
from app.schema.common import APIResponse
from app.api.v1.endpoints.note import (
    create_summary_from_files,
    create_summary_from_url,
    create_blank_from_files,
    create_blank_from_url,
    download_pdf,
    get_note_task_status
)


router = BaseRouter(prefix ="/notes", tags=["note"])

router.api_doc(
    path="/summary/files",
    endpoint=create_summary_from_files,
    methods=["POST"],
    request_model=None,
    response_model=APIResponse[FileSummaryResponse],
    success_model=FileSummaryResponse,
    success_example={
        "status": 200,
        "message": "PDF 파일로 요약 노트가 생성되었습니다.",
        "data": {
            "taskId": "baf500f8-335b-4fb6-b421-5f458b15f18b",
            "status": "PROCESSING",
            "pdfUrl": "",
            "createdAt": "2025-12-17"
        }
    },
    errors={},
    summary="📝 PDF 파일로 요약 노트 생성",
    description="PDF 파일들(최대 5개)로 요약 노트를 생성합니다."
)



router.api_doc(
    path="/summary/url",
    endpoint=create_summary_from_url,
    methods=["POST"],
    request_model=UrlSummaryRequest,
    response_model=APIResponse[UrlSummaryResponse],
    success_model=UrlSummaryResponse,
    success_example={
        "status": 200,
        "message": "URL로 요약 노트가 생성되었습니다.",
        "data": {
            "taskId": "14568a4b-28ff-45bf-8a3d-51cf0fbdfe20",
            "status": "PROCESSING",
            "pdfUrl": "",
            "createdAt": "2025-12-17"
        }
    },
    errors={},
    summary="🎥 URL로 요약 노트 생성",
    description="Canvas 강의 URL에서 동영상을 추출하여 요약 노트를 생성합니다."
)

router.api_doc(
    path="/blank/files",
    endpoint=create_blank_from_files,
    methods=["POST"],
    request_model=None,
    response_model=APIResponse[FileFillBlankResponse],
    success_model=FileFillBlankResponse,
    success_example={
        "status": 200,
        "message": "PDF 파일로 빈칸 채우기 노트가 생성되었습니다.",
        "data": {
            "taskId": "812a18f5-bdb5-434e-a23e-d51b3a9933d9",
            "status": "PROCESSING",
            "pdfUrl": "",
            "createdAt": "2025-12-17"
        }
    },
    errors={},
    summary="📝 PDF 파일로 빈칸 채우기 노트 생성",
    description="PDF 파일들로 빈칸 채우기 노트를 생성합니다."
)

router.api_doc(
    path="/blank/url",
    endpoint=create_blank_from_url,
    methods=["POST"],
    request_model=UrlFillBlankRequest,
    response_model=APIResponse[UrlFillBlankResponse],
    success_model=UrlFillBlankResponse,
    success_example={
        "status": 200,
        "message": "URL로 빈칸 채우기 노트가 생성되었습니다.",
        "data": {
            "taskId": "15a29c33-2fe0-462b-b793-9c734da0b352",
            "status": "PROCESSING",
            "pdfUrl": "",
            "createdAt": "2025-12-17"
        }
    },
    errors={},
    summary="🎥 URL로 빈칸 채우기 노트 생성",
    description="Canvas 강의 URL로 빈칸 채우기 노트를 생성합니다."
)

router.api_doc(
    path="/download/{job_id}/{filename}",
    endpoint=download_pdf,
    methods=["GET"],
    request_model=None, 
    response_model=None,
    success_model=None, 
    success_example=None,
    errors={
        404: {
            "message": "PDF를 찾을 수 없습니다.",
            "code": "FILE_NOT_FOUND"
        }
    },
    summary="📄 생성된 PDF 다운로드",
    description="생성된 PDF 파일을 다운로드합니다. job_id와 filename은 노트 생성 시 반환된 pdfUrl에서 추출할 수 있습니다."
)


router.api_doc(
    path="/task/{task_id}",
    endpoint=get_note_task_status,
    methods=["GET"],
    request_model=None,
    response_model=APIResponse[dict],
    success_model=dict,
    success_example={
        "status": 200,
        "message": "작업 상태 조회 성공",
        "data": {
            "status": "PROCESSING",
            "progress": 0,
            "message": "처리 중..."
        }
    },
    errors={},
    summary="📊 노트 생성 작업 상태 조회",
    description="Celery 작업의 진행 상태를 조회합니다."
)