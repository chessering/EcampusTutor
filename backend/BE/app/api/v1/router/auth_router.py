from app.api.v1.endpoints.auth import create_user, login, logout
from app.core.base_router import BaseRouter
from app.schema.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    SignupRequest,
    SignupResponse,
)
from app.schema.common import APIResponse

router = BaseRouter(prefix ="/auth", tags=["auth"], require_auth=False)

# 회원가입
router.api_doc(
    path="/signup",
    endpoint=create_user,
    methods=["POST"],
    request_model=SignupRequest,
    success_model=SignupResponse,
    response_model=APIResponse[SignupResponse],
    success_example={
        "status": 200,
        "message": "회원 가입이 완료되었습니다.",
        "data": {
            "userId": 1,
            "id": "test1234"
        }
    },
    errors={ },
    summary="회원 가입",
    description="회원 가입 요청의 성공/실패 응답"
)

# 로그인
router.api_doc(
    path="/login",
    endpoint=login,
    methods=["POST"],
    request_model=LoginRequest,
    response_model=APIResponse[LoginResponse],
    success_model=LoginResponse,
    success_example={
        "userId": 1,
		"id": "test1234",
		"accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30",
		"refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30" 
    },
    errors={

    },
    summary="로그인",
    description="로그인 요청에 성공/실패 여부 응답",
)

# logout
logout_router = BaseRouter(prefix="/auth", tags=["auth"], require_auth=True)
logout_router.api_doc(
    path="/logout",
    endpoint=logout,
    methods=["POST"],
    request_model=LogoutRequest,
    response_model=APIResponse[LogoutResponse],
    success_model=LogoutResponse,
    success_example={
        "success" : True
    },
    errors={},
    summary="로그아웃",
    description="Refresh Token을 무효화하여 로그아웃 처리합니다."
)