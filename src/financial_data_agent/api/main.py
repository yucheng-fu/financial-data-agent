from dotenv import load_dotenv
from fastapi import FastAPI

from financial_data_agent.api.router import router

load_dotenv()

app = FastAPI(title="Financial Data Agent API")
app.include_router(router)
