from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    status: int
    message: str
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    status: int
    message: str
    errorCode: str