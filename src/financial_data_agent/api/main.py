from fastapi import FastAPI

from financial_data_agent.api.router import router


app = FastAPI(title="Financial Data Agent API")
app.include_router(router)
