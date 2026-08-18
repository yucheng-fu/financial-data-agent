from fastapi import APIRouter

from financial_data_agent.api.v1.import_company import router as v1_company_router
from financial_data_agent.api.v1.import_filings import router as v1_filings_router
from financial_data_agent.api.v1.cowsay import router as v1_cowsay_router

router = APIRouter()
router.include_router(v1_cowsay_router, prefix="/api/v1")
router.include_router(v1_company_router, prefix="/api/v1")
router.include_router(v1_filings_router, prefix="/api/v1")
