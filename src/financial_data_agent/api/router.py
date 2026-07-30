from fastapi import APIRouter

from financial_data_agent.api.v1.cowsay import router as v1_cowsay_router

router = APIRouter()
router.include_router(v1_cowsay_router, prefix="/api/v1")
