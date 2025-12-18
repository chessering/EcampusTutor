from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.exception.custom_exceptions import APIException
from app.schema.auth import LoginRequest, LogoutRequest, SignupRequest
from app.schema.common import APIResponse
from app.service.auth_service import AuthService

auth_service = AuthService()

async def create_user(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.signup(db, request)
        return APIResponse(
            status=200,
            message="회원가입에 성공했습니다.",
            data=user
        )
    
    except APIException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="회원가입에 실패했습니다."
        )

async def login(
        request: LoginRequest, 
        db: AsyncSession = Depends(get_db)
):
    try:
        user = await auth_service.login(db, request)
        return APIResponse(
            status=200,
            message="로그인에 성공했습니다.",
            data=user
        )

    except APIException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="로그인에 실패했습니다."
        )


async def logout(
        request: LogoutRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    try:
        result = await auth_service.logout(
            db=db,
            user_id=current_user["user_id"],
            refresh_token=request.refresh_token
        )

        return APIResponse(
            status=200,
            message="로그아웃에 성공했습니다.",
            data=result
        )

    except APIException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="로그아웃에 실패했습니다."
        )