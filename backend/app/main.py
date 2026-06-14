from __future__ import annotations

import io
import logging
import os
import uuid
from pathlib import Path
from tempfile import gettempdir

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import config_loader
from app.core import boq_builder, dxf_reader, excel_export
from app.models.schemas import ExportRequest, ExtractRequest, LayerMappingUpdate, PipeSizesUpdate, PriceTableUpdate, SettingsUpdate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dxf-boq")

app = FastAPI(title="DXF BOQ Extractor")

# ALLOWED_ORIGINS: comma-separated list ของ origin ที่อนุญาต เช่น
# "https://your-frontend.pages.dev,https://your-frontend.vercel.app"
# ถ้าไม่ตั้ง จะอนุญาตทุก origin (เหมาะกับ dev เท่านั้น)
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
allow_origins = ["*"] if _allowed_origins == "*" else [o.strip() for o in _allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(gettempdir()) / "dxf_boq_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# session_id -> {"path": Path, "filename": str}
SESSIONS: dict[str, dict] = {}


def _merge(base: dict, override: dict | None) -> dict:
    if not override:
        return base
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_doc(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="ไม่พบ session นี้ กรุณาอัปโหลดไฟล์ใหม่")
    try:
        return dxf_reader.load_dxf(str(session["path"]))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"อ่านไฟล์ DXF ไม่ได้: {exc}") from exc


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_dxf(file: UploadFile = File(...)):
    filename = file.filename or "upload.dxf"
    if not filename.lower().endswith(".dxf"):
        raise HTTPException(
            status_code=400,
            detail="รองรับเฉพาะไฟล์ .dxf เท่านั้น หากมีไฟล์ .dwg กรุณา Save As เป็น DXF จาก AutoCAD/ZWCAD ก่อน",
        )

    session_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{session_id}.dxf"
    content = await file.read()
    dest.write_bytes(content)

    SESSIONS[session_id] = {"path": dest, "filename": filename}

    try:
        doc = dxf_reader.load_dxf(str(dest))
    except Exception as exc:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        del SESSIONS[session_id]
        raise HTTPException(status_code=400, detail=f"อ่านไฟล์ DXF ไม่ได้: {exc}") from exc

    layers = dxf_reader.list_layers(doc)
    return {"session_id": session_id, "filename": filename, "layers": layers}


@app.get("/api/config")
def get_config():
    return {
        "layer_mapping": config_loader.load_layer_mapping(),
        "pipe_sizes": config_loader.load_pipe_sizes(),
        "price_table": config_loader.load_price_table(),
        "settings": config_loader.load_settings(),
    }


@app.put("/api/config/layer-mapping")
def update_layer_mapping(body: LayerMappingUpdate):
    config_loader.save_layer_mapping(body.mapping)
    return {"status": "ok"}


@app.put("/api/config/price-table")
def update_price_table(body: PriceTableUpdate):
    config_loader.save_price_table(body.price_table)
    return {"status": "ok"}


@app.put("/api/config/pipe-sizes")
def update_pipe_sizes(body: PipeSizesUpdate):
    config_loader.save_pipe_sizes(body.pipe_sizes)
    return {"status": "ok"}


@app.put("/api/config/settings")
def update_settings(body: SettingsUpdate):
    config_loader.save_settings(body.settings)
    return {"status": "ok"}


@app.get("/api/sessions/{session_id}/layers")
def get_layers(session_id: str):
    doc = _load_doc(session_id)
    return {"layers": dxf_reader.list_layers(doc)}


def _build(session_id: str, req: ExtractRequest):
    doc = _load_doc(session_id)

    layer_mapping = _merge(config_loader.load_layer_mapping(), req.layer_mapping)
    pipe_sizes = _merge(config_loader.load_pipe_sizes(), req.pipe_sizes)
    price_table = _merge(config_loader.load_price_table(), req.price_table)
    settings = _merge(config_loader.load_settings(), req.settings)
    legend_bbox = req.legend_bbox.as_tuple() if req.legend_bbox else None

    try:
        return boq_builder.build_boq(
            doc, layer_mapping, pipe_sizes, price_table, settings, legend_bbox_override=legend_bbox
        ), settings
    except Exception as exc:  # noqa: BLE001
        logger.exception("extraction failed")
        raise HTTPException(status_code=500, detail=f"ถอดวัสดุไม่สำเร็จ: {exc}") from exc


@app.post("/api/sessions/{session_id}/extract")
def extract(session_id: str, req: ExtractRequest):
    result, _ = _build(session_id, req)
    return result


@app.post("/api/sessions/{session_id}/export")
def export(session_id: str, req: ExportRequest):
    result, settings = _build(session_id, req)

    garden_location = req.garden_location or settings.get("garden_location", "")
    garden_phone = req.garden_phone or settings.get("garden_phone", "")

    xlsx_bytes = excel_export.build_workbook(
        result["plants"], garden_location=garden_location, garden_phone=garden_phone
    )

    filename = SESSIONS[session_id]["filename"].rsplit(".", 1)[0] + "_BOQ.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
