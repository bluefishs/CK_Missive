"""
工程圖/測量圖/地籍圖分析 API 端點 (Gemma 4 Vision)

Version: 1.0.0
Created: 2026-04-05
"""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()

_ALLOWED_TYPES = {"survey", "cadastral", "engineering", "blueprint"}
_MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/diagram/analyze")
async def analyze_diagram(
    image: UploadFile = File(...),
    diagram_type: str = Form("survey"),
    context: str = Form(""),
):
    """分析工程圖/測量圖/地籍圖 (Gemma 4 Vision)

    - **image**: 圖片檔案 (PNG/JPG/TIFF, max 10MB)
    - **diagram_type**: survey|cadastral|engineering|blueprint
    - **context**: 可選背景資訊 (如專案名稱、位置)
    """
    if diagram_type not in _ALLOWED_TYPES:
        return JSONResponse(
            status_code=400,
            content={"error": f"不支援的圖面類型: {diagram_type}，允許: {', '.join(_ALLOWED_TYPES)}"},
        )

    image_bytes = await image.read()
    if not image_bytes:
        return JSONResponse(status_code=400, content={"error": "圖片資料為空"})
    if len(image_bytes) > _MAX_SIZE:
        return JSONResponse(status_code=400, content={"error": "圖片超過 10MB 限制"})

    from app.services.ai.engineering_diagram_service import EngineeringDiagramService

    service = EngineeringDiagramService()
    result = await service.analyze_diagram(
        image_bytes=image_bytes,
        diagram_type=diagram_type,
        context=context,
    )

    if "error" in result:
        return JSONResponse(status_code=422, content=result)
    return result


@router.post("/diagram/extract-coordinates")
async def extract_coordinates(
    image: UploadFile = File(...),
):
    """提取座標表 (測量圖控制點)

    - **image**: 含座標表的測量圖 (PNG/JPG/TIFF, max 10MB)
    """
    image_bytes = await image.read()
    if not image_bytes:
        return JSONResponse(status_code=400, content={"error": "圖片資料為空"})
    if len(image_bytes) > _MAX_SIZE:
        return JSONResponse(status_code=400, content={"error": "圖片超過 10MB 限制"})

    from app.services.ai.engineering_diagram_service import EngineeringDiagramService

    service = EngineeringDiagramService()
    result = await service.extract_coordinates_table(image_bytes=image_bytes)

    if "error" in result:
        return JSONResponse(status_code=422, content=result)
    return result


@router.post("/diagram/compare")
async def compare_diagrams(
    image_a: UploadFile = File(...),
    image_b: UploadFile = File(...),
    comparison_type: str = Form("change"),
):
    """比較兩張圖面差異 (如施工前後)

    - **image_a**: 第一張圖 (PNG/JPG/TIFF, max 10MB)
    - **image_b**: 第二張圖 (PNG/JPG/TIFF, max 10MB)
    - **comparison_type**: change(變更)|overlay(疊圖)
    """
    bytes_a = await image_a.read()
    bytes_b = await image_b.read()
    if not bytes_a or not bytes_b:
        return JSONResponse(status_code=400, content={"error": "圖片資料為空"})
    if len(bytes_a) > _MAX_SIZE or len(bytes_b) > _MAX_SIZE:
        return JSONResponse(status_code=400, content={"error": "圖片超過 10MB 限制"})

    from app.services.ai.engineering_diagram_service import EngineeringDiagramService

    service = EngineeringDiagramService()
    result = await service.compare_diagrams(
        image_bytes_a=bytes_a,
        image_bytes_b=bytes_b,
        comparison_type=comparison_type,
    )
    return result
