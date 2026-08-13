from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from financial_data_agent.api.router import router

app = FastAPI(title="Financial Data Agent API")
app.include_router(router)
