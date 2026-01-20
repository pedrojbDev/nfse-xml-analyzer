from fastapi import APIRouter, Request, Response
import hashlib

from app.services.nfe_batch_export import export_nfe_zip_batch_to_csv
from app.services.audit_log import append_audit_event

router = APIRouter(tags=["nfe-batch"])


@router.post("/nfe-xml-batch/export-csv")
async def nfe_xml_batch_export_csv(request: Request):
    """
    Recebe um ZIP com múltiplas NF-e XML e retorna um CSV consolidado por ITEM.
    """
    zip_bytes = await request.body()
    filename = request.headers.get("x-filename", "nfe_batch.zip")

    # Auditoria leve
    try:
        zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
        append_audit_event(
            {
                "kind": "nfe_batch_export_csv",
                "filename": filename,
                "zip_sha256": zip_sha256,
            }
        )
    except Exception:
        pass

    csv_text = export_nfe_zip_batch_to_csv(zip_bytes)

    out_name = filename.rsplit(".", 1)[0] + "_itens.csv"
    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}

    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
