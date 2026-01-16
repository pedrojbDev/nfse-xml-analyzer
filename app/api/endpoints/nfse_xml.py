from fastapi import APIRouter, Request, Response

from app.services.nfse_xml_extract import (
    parse_nfse_xml_abrasf,
    parse_nfse_xml_abrasf_paged,
    export_nfse_items_to_csv,
)

router = APIRouter(tags=["nfse-xml"])


@router.post("/nfse-xml-extract")
async def nfse_xml_extract(request: Request, page: int = 1, page_size: int = 50):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")
    return parse_nfse_xml_abrasf_paged(raw, filename=filename, page=page, page_size=page_size)


@router.post("/nfse-xml-extract/summary")
async def nfse_xml_extract_summary(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfse_xml_abrasf(xml_bytes=raw, filename=filename)
    return {
        "received": result.received,
        "filename": result.filename,
        "sha256": result.sha256,
        "count": result.count,
        "summary": result.summary,
    }


@router.post("/nfse-xml-extract/export-csv")
async def nfse_xml_export_csv(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfse_xml_abrasf(xml_bytes=raw, filename=filename)
    if not result.received:
        return {
            "received": False,
            "filename": result.filename,
            "sha256": result.sha256,
            "summary": result.summary,
        }

    csv_text = export_nfse_items_to_csv(result.items)

    out_name = filename.rsplit(".", 1)[0] + ".csv"
    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return Response(content=csv_text, media_type="text/csv; charset=utf-8", headers=headers)
