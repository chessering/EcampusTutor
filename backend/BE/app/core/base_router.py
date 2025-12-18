from typing import Any, Dict, List, Type

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.util.docs.swagger_response import error_response, success_response


class BaseRouter(APIRouter):
    def __init__(self, *args, require_auth: bool = True, **kwargs):
        # 공통 dependencies 자동 적용
        if require_auth:
            kwargs.setdefault("dependencies", []).append(Depends(get_current_user))
        super().__init__(*args, **kwargs)

    def api_doc(
        self,
        path: str,
        endpoint,
        methods: List[str],
        request_model: Type[BaseModel],
        response_model: Type[BaseModel],
        success_model: Type[BaseModel],
        request_example: Dict = None,
        success_example: Dict = None,
        errors: Dict[int, Dict[str, Any]] = {},
        **kwargs
    ):
        """
        공통 응답 구조 자동 적용: success + errors
        """
        if errors is None:
            errors = {}
        
        responses = {}
        if success_model:
            responses.update(success_response(success_model, example=success_example))

        for status_code, info in errors.items():
            responses.update(error_response(status_code, info["message"], info["code"]))

        # request body 예시가 있으면 설정
        if request_model and request_example:
            if "openapi_extra" not in kwargs:
                kwargs["openapi_extra"] = {}
            kwargs["openapi_extra"]["requestBody"] = {
                "content": {"application/json": {"example": request_example}}
            }

        super().add_api_route(
            path, 
            endpoint,
            methods=methods,
            response_model=response_model, 
            responses=responses, 
            **kwargs
        )