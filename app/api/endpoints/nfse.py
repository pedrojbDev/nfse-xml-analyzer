from fastapi import APIRouter, Request

from app.services.nfse_pipeline import run_nfse_extract_pipeline

router = APIRouter(tags=["nfse"])

@router.post("/nfse-service-extract-raw")
async def nfse_service_extract_raw(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.pdf")
    return run_nfse_extract_pipeline(raw=raw, filename=filename)
