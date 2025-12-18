from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.exception.custom_exceptions import APIException
from app.exception.error_code import Error

bearer_scheme = HTTPBearer(auto_error=False)  # 토큰이 없을 때도 우리가 처리


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    
    """
    JWT 토큰 검증 및 사용자 정보 반환
    """
    print("\n" + "="*60)
    print("🔍 JWT Token Verification Started")
    print("="*60)
    
    if not credentials:
        print("❌ No credentials provided")
        raise APIException(401, Error.AUTH_TOKEN_MISSING)

    token = credentials.credentials
    print(f"Token (first 30 chars): {token[:30]}...")
    print(f"Token length: {len(token)}")
    print(f"JWT_SECRET (first 10 chars): {settings.JWT_SECRET[:10]}...")
    print(f"JWT_ALGORITHM: {settings.JWT_ALGORITHM}")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        print(f"✅ Token decoded successfully!")
        print(f"Payload: {payload}")

        # sub 에서 user_id 추출
        user_id = payload.get("sub")
        token_type = payload.get("type")

        print(f"✅ Token decoded successfully!")
        print(f"Payload: {payload}")

        # 타입 검증
        if token_type != "access":
            print(f"❌ Invalid token type: {token_type}")
            raise APIException(401, Error.AUTH_INVALID_TOKEN)

        if user_id is None:
            print(f"❌ Invalid token type: {token_type}")
            raise APIException(401, Error.AUTH_INVALID_TOKEN)
        
        return {"user_id" : int(user_id)}
    
    except ExpiredSignatureError as e:
        print(f"❌ Token EXPIRED: {e}")
        raise APIException(401, Error.AUTH_EXPIRED_TOKEN)
    except JWTError as e:
        print(f"❌ JWT Error: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("="*60 + "\n")
        raise APIException(401, Error.AUTH_INVALID_TOKEN)
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("="*60 + "\n")
        raise APIException(401, Error.AUTH_INVALID_TOKEN)