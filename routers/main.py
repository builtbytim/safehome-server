from fastapi import APIRouter
from .users import router as users_router
from .uploads import router as uploads_router


router = APIRouter()


@router.get("", status_code=200)
async def root():
    return {"message": "Hello World"}


router.include_router(users_router, prefix="/users")
router.include_router(uploads_router, prefix="/uploads")
