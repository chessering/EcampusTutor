# app/auth/custom_oauth2.py

from fastapi import Request
from fastapi.security import OAuth2PasswordBearer

from app.exception.custom_exceptions import APIException
from app.exception.error_code import Error


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str:
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise APIException(401, Error.AUTH_TOKEN_MISSING)
        scheme, _, param = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise APIException(401, Error.AUTH_INVALID_TOKEN)
        return param