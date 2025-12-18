from app.api.v1.endpoints.quiz import (
    create_quiz_file,
    create_quiz_url,
    get_quiz_detail,
    get_quizzes,
    get_task_status,
    save_quiz_answers,
    submit_quiz,
)
from app.core.base_router import BaseRouter
from app.schema.common import APIResponse
from app.schema.quiz import (
    QuizDetailResponse,
    QuizFileRequest,
    QuizFileResponse,
    QuizListResponse,
    QuizSaveRequest,
    QuizSaveResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizUrlRequest,
    QuizUrlResponse,
)

router = BaseRouter(prefix ="/quiz", tags=["quiz"])

# 저장된 퀴즈 리스트
router.api_doc(
    path="",
    endpoint=get_quizzes,
    methods=["GET"],
    request_model=None,
    response_model=APIResponse[QuizListResponse],
    success_model=list[QuizListResponse],
    success_example=[
        {"quizId": 1, "title": "메타버스 01"},
        {"quizId": 2, "title": "메타버스 02"},
    ],
    errors={

    },
    summary="🗒️ 저장된 퀴즈 노트 목록 조회",
    description="저장된 모든 노트 목록을 반환합니다.",
)
"""
        500: {
            "message": Error.NOTE_INTERNAL_ERROR.message,
            "code": Error.NOTE_INTERNAL_ERROR.code,
        }
"""

# 노트 상세 정보
router.api_doc(
    path="/{quiz_id}",
    endpoint=get_quiz_detail,
    methods=["GET"],
    request_model=None,
    response_model=APIResponse[QuizDetailResponse],
    success_model=QuizDetailResponse,
    success_example={
        "quizId": 1,
        "isSaved" : True,
        "totalQuestions": 20,
        "correctAnswers": 19,
        "createdAt": "2025-10-20T10:30:00",
        "questions": [
            {
                "questionNumber": 3,
                "questionText": "데이터베이스 시스템 관리에서 가장 옳은 설명은?",
                "questionType": "MULTIPLE",
                "choices": [
                    "로그 파일이 가득 차면 데이터베이스 사용을 제한한다",
                    "모든 사용자가 모든 파일에 대한 데이터베이스 사용권을 할 수 있다",
                    "데이터베이스 사용자 마드 온라인에 반드 쓰 해법을 허락한다",
                    "데이터베이스 사용자의 접근을 제어할 수 있다"
                ],
                "correctAnswer": 3,
                "userAnswer": 3,
                "isCorrect": True,
                "explanation": "데이터베이스 접근 제어는 보안의 핵심입니다..."
            },
            {
                "questionNumber": 5,
                "questionText": "SQL에서 테이블을 생성하는 명령어는?",
                "questionType": "SHORT",
                "choices": [],
                "correctAnswer": "CREATE TABLE",
                "userAnswer": "create table",
                "isCorrect": True,
                "explanation": "CREATE TABLE은 새로운 테이블을 생성하는 DDL 명령어입니다..."
            }
        ]
    },
    errors={

    },
    summary="📝 저장된 퀴즈 상세 조회",
    description="특정 퀴즈의 상세 정보(문항, 정답, 해설 등)를 조회합니다.",
)

"""
        404: {
            "message": Error.NOTE_NOT_FOUND.message,
            "code": Error.NOTE_NOT_FOUND.code,
        },
        500: {
            "message": Error.NOTE_INTERNAL_ERROR.message,
            "code": Error.NOTE_INTERNAL_ERROR.code,
        },
"""

# pdf로 문제 생성
router.api_doc(
    path="/generate/files",
    endpoint=create_quiz_file,
    methods=["POST"],
    request_model=None,
    response_model=APIResponse[QuizFileResponse],
    success_model=QuizFileResponse,
    success_example={
        "quizId" : 1,
        "status": "COMPLETED",
	    "totalQuestions": 20,
	    "createdAt": "2025-10-20",
	    "questions": [
	        {
	        "questionNumber": 1,
	        "questionText": "데이터베이스 시스템 관리에서 가장 옳은 설명은?",
	        "questionType": "MULTIPLE",
	        "choices": [
	            "로그 파일이 가득 차면 데이터베이스 사용을 제한한다",
	            "모든 사용자가 모든 파일에 대한 접근권을 가진다",
	            "데이터베이스 사용자는 온라인에서만 접근할 수 있다",
	            "데이터베이스 사용자의 접근을 제어할 수 있다"
	        ],
	        },
            {
            "questionNumber": 2,
            "questionText": "SQL에서 테이블을 생성하는 명령어는?",
            "questionType": "SHORT",
            "choices": [],
            }
	    ]
	},
    errors={},
    summary="📝 pdf 파일들로 예상 문제 생성",
    description="pdf 파일들(최대 5개)로 예상 문제를 생성합니다.",
)

# URL로 문제 생성
router.api_doc(
    path="/generate/url",
    endpoint=create_quiz_url,
    methods=["POST"],
    request_model=QuizUrlRequest,
    response_model=APIResponse[QuizUrlResponse],
    success_model=QuizUrlResponse,
    success_example={
        "quizId" : 1,
        "status": "COMPLETED",
        "total_questions": 10,
        "created_at": "2025-10-20",
        "questions": [
            {
                "question_number": 1,
                "question_text": "데이터베이스 시스템 관리에서 가장 옳은 설명은?",
                "question_type": "MULTIPLE",
                "choices": [
                    "로그 파일이 가득 차면 데이터베이스 사용을 제한한다",
                    "모든 사용자가 모든 파일에 대한 접근권을 가진다",
                    "데이터베이스 사용자는 온라인에서만 접근할 수 있다",
                    "데이터베이스 사용자의 접근을 제어할 수 있다"
                ],
            },
            {
                "question_number": 2,
                "question_text": "SQL에서 테이블을 생성하는 명령어는?",
                "question_type": "SHORT",
                "choices": [],
            }
        ]
    },
    errors={},
    summary="📝 URL로 예상 문제 생성",
    description="URL에서 학습 자료를 가져와 예상 문제를 생성합니다.",
)

# 퀴즈 저장
router.api_doc(
    path="/save",
    endpoint=save_quiz_answers,
    methods=["POST"],
    request_model=QuizSaveRequest,
    response_model=APIResponse[QuizSaveResponse],
    success_model=QuizSaveResponse,
    success_example={
        "quiz_id": 1,
        "title": "데이터베이스 1주차 예상문제",
        "is_saved": True,
        "created_at": "2025-10-20"
    },
    errors={
        404: {
            "message": "퀴즈를 찾을 수 없습니다.",
            "code": "QUIZ_NOT_FOUND"
        },
        500: {
            "message": "퀴즈 저장에 실패했습니다.",
            "code": "QUIZ_INTERNAL_ERROR"
        }
    },
    summary="💾 퀴즈 저장",
    description="생성된 퀴즈에 제목을 입력하여 저장합니다.",
)

# 퀴즈 정답 제출
router.api_doc(
    path="/submit",
    endpoint=submit_quiz,
    methods=["POST"],
    request_model=QuizSubmitRequest,
    response_model=APIResponse[QuizSubmitResponse],
    success_model=QuizSubmitResponse,
    success_example={
        "quizId" : 1,
        "answers": [
            {
            "questionNumber": 1,
            "questionType": "MULTIPLE",
            "answer": 4
            },
            {
            "questionNumber": 2,
            "questionType": "SHORT",
            "answer": "CREATE TABLE"
            }
        ]
    },
    errors={},
    summary="💾 퀴즈 정답 제출",
    description="유저가 작성한 답을 제출하고 결과를 조회합니다.",
)


# task 로그
router.api_doc(
    path="/task-status/{task_id}",
    endpoint=get_task_status,
    methods=["GET"],
    request_model=None, 
    response_model=None,
    success_model=None, 
    success_example=None,
)