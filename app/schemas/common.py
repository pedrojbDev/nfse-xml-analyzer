from typing import Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])

class RawPdfAckResponse(BaseModel):
    received: bool
    source: str
    filename: str
    content_type: str
    bytes: int
    sha256: str

class ErrorResponse(BaseModel):
    received: bool = False
    filename: str
    bytes: int
    sha256: str
    error: str
    hint: Optional[str] = None
    head_ascii: Optional[str] = None
    head_hex: Optional[str] = None
