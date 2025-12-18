import asyncio

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import bearer_scheme, get_current_user
from app.core.config import settings
from app.exception.custom_exceptions import APIException
from app.exception.error_code import Error
from app.repository.auth_repository import AuthRepository
from app.schema.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    SignupRequest,
    SignupResponse,
)
from app.service.canvas_service import CanvasService
from app.util.jwt_utils import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self):
        self.auth_repo = AuthRepository()
        self.canvas_service = CanvasService()

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    async def signup(self, db: AsyncSession, request: SignupRequest):
        
        # Selenium은 동기 함수이므로 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        is_canvas_valid = await loop.run_in_executor(
            None, 
            self.canvas_service.verify_canvas_login,
            request.id,
            request.password
        )
        
        if not is_canvas_valid:
            print(f"❌ Canvas 로그인 검증 실패")
            raise APIException(401, Error.AUTH_CANVAS_VERIFICATION_FAILED)
        
        print(f"✅ Canvas 로그인 검증 성공")
        
        if not is_canvas_valid:
            print(f"❌ Canvas 로그인 검증 실패")
            raise APIException(401, Error.AUTH_CANVAS_VERIFICATION_FAILED)
        
        print(f"✅ Canvas 로그인 검증 성공")
        
        # 중복 이메일 체크
        existing_user = await self.auth_repo.get_by_id(db, request.id)
        if existing_user:
            raise APIException(400, Error.AUTH_DUPLICATE_USER)
    
        # hashed_password = self.hash_password(request.password)
        encrypted_canvas_pw = settings.fernet.encrypt(request.password.encode()).decode()
        user = await self.auth_repo.create_user(db, request.id, encrypted_canvas_pw)
        return SignupResponse(
            user_id=user.user_id,
            id=user.id
        )
    
    async def login(self, db: AsyncSession, request: LoginRequest):
        user = await self.auth_repo.get_by_id(db, request.id)
        if not user:
            raise APIException(404, Error.AUTH_USER_NOT_FOUND)
        
        # if not self.verify_password(request.password, user.password):
        #     raise APIException(401, Error.AUTH_INVALID_PASSWORD)

        access_token = create_access_token({"sub" : user.user_id})
        refresh_token = create_refresh_token({"sub":user.user_id})

        return LoginResponse(
            user_id=user.user_id,
            id=user.id,
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def logout(self, db: AsyncSession, user_id: int, refresh_token: str):
        print("💡 LOGOUT START")
        print("💡 user_id from access token:", user_id)
        print("💡 refresh_token (first 30 chars):", refresh_token[:30], "...")

        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            print("💡 decoded refresh token payload:", payload)

            token_type = payload.get("type")
            token_user_id = payload.get("sub")

            # 타입 검증
            if token_type != "refresh":
                print("❌ Invalid token type:", token_type)
                raise APIException(400, Error.AUTH_INVALID_TOKEN)

            # 토큰 소유자 검증
            if int(token_user_id) != user_id:
                print(f"❌ Token user_id {token_user_id} does not match access token user_id {user_id}")
                raise APIException(401, Error.AUTH_UNAUTHORIZED)

            print("✅ Logout successful")
            return LogoutResponse(success=True)

        except ExpiredSignatureError:
            print("⚠️ Refresh token expired, but logout allowed")
            return LogoutResponse(success=True)
        except JWTError as e:
            print("❌ JWTError during logout:", str(e))
            raise APIException(400, Error.AUTH_INVALID_TOKEN)
        except Exception as e:
            import traceback
            print("🔥 Unexpected error in logout:", type(e).__name__, str(e))
            print(traceback.format_exc())
            raise e
