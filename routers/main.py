from fastapi import APIRouter
from .users import router as users_router
from .uploads import router as uploads_router
from .misc import router as miscellaneous_router
from .notifications import router as notifications_router
from .payments import router as payments_router
from .wallets import router as wallets_router
from .investments import router as investments_router
from .savings import router as savings_router
from .referrals import router as referrals_router
from .affiliates import router as affiliates_router


router = APIRouter()


@router.get("", status_code=200)
async def root():
    return {"message": "Hello World"}


router.include_router(users_router, prefix="/users")
router.include_router(wallets_router, prefix="/wallet")
router.include_router(notifications_router, prefix="/notifications")
router.include_router(uploads_router, prefix="/uploads")
router.include_router(payments_router, prefix="/payments")
router.include_router(investments_router, prefix="")
router.include_router(savings_router, prefix="/savings")
router.include_router(referrals_router, prefix="/refer")
router.include_router(affiliates_router, prefix="/affiliate")
router.include_router(miscellaneous_router, prefix="/misc")
