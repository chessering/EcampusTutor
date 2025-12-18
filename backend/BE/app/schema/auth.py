from pydantic import BaseModel


# 회원 가입 RequestDTO
class SignupRequest(BaseModel):
    id: str
    password: str

# 회원가입 ResponseDTO
class SignupResponse(BaseModel):
    user_id: int
    id: str

# 로그인 request
class LoginRequest(BaseModel):
    id: str
    password: str

# 로그인 response
class LoginResponse(BaseModel):
    user_id: int
    id: str
    access_token: str
    refresh_token: str

# 로그아웃
class LogoutResponse(BaseModel):
    success: bool

class LogoutRequest(BaseModel):
    refresh_token: str