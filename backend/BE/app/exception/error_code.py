# app/exception/error_code.py

from enum import Enum


class ErrorCode:
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return f"[{self.code}] {self.message}"


class Error:
    # Auth
    AUTH_UNAUTHORIZED = ErrorCode(
        "AUTH-001", "인증되지 않은 사용자입니다. 로그인 후 다시 시도하세요."
    )
    AUTH_INVALID_TOKEN = ErrorCode("AUTH-002", "유효하지 않은 Access Token입니다.")
    AUTH_EXPIRED_TOKEN = ErrorCode("AUTH-003", "만료된 Access Token입니다.")
    AUTH_TOKEN_MISSING = ErrorCode("AUTH-004", "Access Token이 누락되었습니다.")
    AUTH_DUPLICATE_USER = ErrorCode("AUTH-005", "이미 존재하는 아이디입니다.")
    AUTH_USER_NOT_FOUND = ErrorCode("AUTH-006", "존재하지 않는 사용자입니다.")
    AUTH_INVALID_PASSWORD = ErrorCode("AUTH-007", "유효하지 않은 비밀번호입니다.")
    AUTH_CANVAS_VERIFICATION_FAILED  = ErrorCode("AUTH-008", "경희대 Canvas LMS 로그인 검증에 실패했습니다. 아이디와 비밀번호를 확인해주세요.")
    # Quiz
    QUIZ_NOT_FOUND = ErrorCode("QUIZ-001", "해당 문제를 찾을 수 없습니다.")
    QUIZ_INTERNAL_ERROR = ErrorCode("QUIZ-002", "퀴즈 저장이 실패했습니다.")
    QUIZ_CREATION_FAILED = ErrorCode("QUIZ-003", "퀴즈 생성에 실패했습니다.")
    QUIZ_INVALID_REQUEST = ErrorCode("QUIZ-004", "잘못된 퀴즈 요청입니다.")
    
    # File
    FILE_NOT_FOUND = ErrorCode("FILE-001", "파일을 찾을 수 없습니다.")
    FILE_UPLOAD_FAILED = ErrorCode("FILE-002", "파일 업로드에 실패했습니다.")
    FILE_INVALID_FORMAT = ErrorCode("FILE-003", "지원하지 않는 파일 형식입니다.")
    FILE_TOO_LARGE = ErrorCode("FILE-004", "파일 크기가 너무 큽니다.")
    FILE_EXTRACTION_FAILED = ErrorCode("FILE-005", "파일에서 텍스트 추출에 실패했습니다.")
    
    # URL
    URL_NOT_FOUND = ErrorCode("URL-001", "URL을 찾을 수 없습니다.")
    URL_INVALID = ErrorCode("URL-002", "유효하지 않은 URL입니다.")
    URL_FETCH_FAILED = ErrorCode("URL-003", "URL에서 데이터를 가져오는데 실패했습니다.")
    URL_EXTRACTION_FAILED = ErrorCode("URL-004", "URL에서 텍스트 추출에 실패했습니다.")
    
    # GPT/AI
    GPT_API_ERROR = ErrorCode("GPT-001", "GPT API 호출에 실패했습니다.")
    GPT_INVALID_RESPONSE = ErrorCode("GPT-002", "GPT API 응답이 유효하지 않습니다.")
    GPT_QUOTA_EXCEEDED = ErrorCode("GPT-003", "GPT API 할당량을 초과했습니다.")
    
    # Database
    DB_CONNECTION_ERROR = ErrorCode("DB-001", "데이터베이스 연결에 실패했습니다.")
    DB_QUERY_ERROR = ErrorCode("DB-002", "데이터베이스 쿼리 실행에 실패했습니다.")
    DB_COMMIT_ERROR = ErrorCode("DB-003", "데이터베이스 커밋에 실패했습니다.")
    
    # User
    USER_NOT_FOUND = ErrorCode("USER-001", "사용자를 찾을 수 없습니다.")
    
    CANVAS_CREDENTIALS_MISSING = ErrorCode("CANVAS-001", "CANVAS에서 사용자를 찾을 수 업습니다.")