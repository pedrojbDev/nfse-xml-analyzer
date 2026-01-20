from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.nfse import router as nfse_router
from app.api.endpoints.nfse_xml import router as nfse_xml_router
from app.api.endpoints.nfe_xml import router as nfe_xml_router
from app.api.endpoints.nfe_batch import router as nfe_batch_router
from app.api.endpoints.nfe_batch_export import router as nfe_batch_export_router




api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(nfse_router)
api_router.include_router(nfse_xml_router)
api_router.include_router(nfe_xml_router)
api_router.include_router(nfe_batch_router)
api_router.include_router(nfe_batch_export_router)



