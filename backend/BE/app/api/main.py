from fastapi import APIRouter

from app.api.v1.router import auth_router, quiz_router, note_router

api_router = APIRouter()
api_router.include_router(
    auth_router.router,
)

api_router.include_router(
    auth_router.logout_router,
)

api_router.include_router(
    quiz_router.router,
)

api_router.include_router(
    note_router.router
)