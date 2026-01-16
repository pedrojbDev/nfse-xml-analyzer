from fastapi import FastAPI
from app.api.router import api_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Document Processor API (MVP)",
    version="0.2.2",
)

app.include_router(api_router)

