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

    from app.services.ai.document.engineering_diagram_service import EngineeringDiagramService

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

    from app.services.ai.document.engineering_diagram_service import EngineeringDiagramService

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

    from app.services.ai.document.engineering_diagram_service import EngineeringDiagramService

    service = EngineeringDiagramService()
    result = await service.compare_diagrams(
        image_bytes_a=bytes_a,
        image_bytes_b=bytes_b,
        comparison_type=comparison_type,
    )
    return result


# v5.15 Phase 2a：通用 image-to-text endpoint（Gap 6 multi-modal）

@router.post("/vision/describe")
async def describe_image(
    image: UploadFile = File(...),
    context: str = Form(""),
):
    """通用 image-to-text — 給 ChatTab paste handler 用（Gap 6 真活）。

    用 Gemma 4 Vision 描述任意圖片內容（不限工程圖類型）。
    供前端 RAGChatPanel onPaste 流程：
      使用者貼圖 → 上傳此 endpoint → 取得 description → 自動填進 query input

    - **image**: 任意圖片 (PNG/JPG/WebP, max 10MB)
    - **context**: 可選上下文（如「這是費用單據」）
    """
    image_bytes = await image.read()
    if not image_bytes:
        return JSONResponse(status_code=400, content={"error": "圖片資料為空"})
    if len(image_bytes) > _MAX_SIZE:
        return JSONResponse(status_code=400, content={"error": "圖片超過 10MB 限制"})

    from app.core.ai_connector import get_ai_connector

    ai = get_ai_connector()
    prompt = "用繁體中文簡潔描述這張圖片的內容（100-200 字）。如果圖中有可讀文字，請列出。"
    if context:
        prompt = f"背景：{context}\n\n{prompt}"

    try:
        result = await ai.vision_completion(
            prompt=prompt,
            image_bytes=image_bytes,
            temperature=0.3,
            max_tokens=512,
            task_type="vision",
        )
        return {
            "success": True,
            "description": result.strip() if result else "",
            "size_bytes": len(image_bytes),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )
