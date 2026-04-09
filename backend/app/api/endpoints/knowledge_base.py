"""知識庫瀏覽器 API

提供知識地圖、ADR、架構圖的瀏覽功能，以及向量搜尋。

@version 2.0.0
@date 2026-03-19
"""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.database import get_async_db
from app.schemas.knowledge_base import (
    AdrInfo,
    AdrListResponse,
    DiagramInfo,
    DiagramListResponse,
    FileContentResponse,
    FileInfo,
    FileRequest,
    KBEmbedResponse,
    KBSearchRequest,
    KBSearchResponse,
    KBSearchResult,
    KBStatsResponse,
    SectionInfo,
    TreeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Project root: backend/ is at depth 1 from project root
DOCS_DIR = Path(__file__).resolve().parents[4] / "docs"
ALLOWED_SUBDIRS = {"knowledge-map", "adr", "diagrams"}


def _validate_path(user_path: str) -> Path:
    """Three-layer path validation."""
    # Layer 1: reject path traversal and absolute paths
    if ".." in user_path or user_path.startswith(("/", "\\")):
        raise HTTPException(status_code=400, detail="非法路徑")

    # Layer 2: whitelist allowed subdirectories
    parts = Path(user_path).parts
    if not parts or parts[0] not in ALLOWED_SUBDIRS:
        raise HTTPException(status_code=400, detail="不允許的路徑")

    # Only allow .md / .mmd files
    if not (user_path.endswith(".md") or user_path.endswith(".mmd")):
        raise HTTPException(status_code=400, detail="僅允許 .md / .mmd 檔案")

    # Layer 3: resolve and verify containment
    resolved = (DOCS_DIR / user_path).resolve()
    if not resolved.is_relative_to(DOCS_DIR.resolve()):
        raise HTTPException(status_code=403, detail="路徑越界")

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="檔案不存在")

    return resolved


@router.post("/tree", response_model=TreeResponse)
async def get_knowledge_tree(
    _admin: dict = Depends(require_admin),
) -> TreeResponse:
    """取得知識地圖目錄結構。"""
    km_dir = DOCS_DIR / "knowledge-map"
    if not km_dir.is_dir():
        return TreeResponse(success=True, sections=[])

    sections: list[SectionInfo] = []

    # Collect root-level .md files as a special "_Root" section
    root_files = sorted(km_dir.glob("*.md"), key=lambda p: p.name)
    if root_files:
        sections.append(
            SectionInfo(
                name="_Root",
                path="knowledge-map",
                files=[
                    FileInfo(
                        name=f.name,
                        path=f"knowledge-map/{f.name}",
                    )
                    for f in root_files
                ],
            )
        )

    # Walk subdirectories sorted by name
    subdirs = sorted(
        [d for d in km_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    for subdir in subdirs:
        md_files = sorted(subdir.glob("*.md"), key=lambda p: p.name)
        if md_files:
            sections.append(
                SectionInfo(
                    name=subdir.name,
                    path=f"knowledge-map/{subdir.name}",
                    files=[
                        FileInfo(
                            name=f.name,
                            path=f"knowledge-map/{subdir.name}/{f.name}",
                        )
                        for f in md_files
                    ],
                )
            )

    return TreeResponse(success=True, sections=sections)


@router.post("/file", response_model=FileContentResponse)
async def get_file_content(
    req: FileRequest,
    _admin: dict = Depends(require_admin),
) -> FileContentResponse:
    """讀取知識庫檔案內容。"""
    resolved = _validate_path(req.path)

    try:
        content = resolved.read_text(encoding="utf-8")
    except Exception:
        logger.exception("讀取知識庫檔案失敗: %s", req.path)
        raise HTTPException(status_code=500, detail="讀取檔案失敗")

    return FileContentResponse(
        success=True,
        content=content,
        filename=resolved.name,
    )


@router.post("/adr/list", response_model=AdrListResponse)
async def list_adrs(
    _admin: dict = Depends(require_admin),
) -> AdrListResponse:
    """列出所有 ADR 文件。"""
    adr_dir = DOCS_DIR / "adr"
    if not adr_dir.is_dir():
        return AdrListResponse(success=True, items=[])

    title_re = re.compile(r"^#\s+ADR-(\d+):\s*(.+)")
    status_re = re.compile(r">\s*\*\*狀態\*\*:\s*(.+)")
    date_re = re.compile(r">\s*\*\*日期\*\*:\s*(.+)")

    items: list[AdrInfo] = []
    for f in sorted(adr_dir.glob("0*.md"), key=lambda p: p.name):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()[:10]
        except Exception:
            logger.warning("無法讀取 ADR 檔案: %s", f.name)
            continue

        number = ""
        title = f.stem
        status = ""
        date = ""

        for line in lines:
            m_title = title_re.match(line)
            if m_title:
                number = m_title.group(1)
                title = m_title.group(2).strip()
                continue
            m_status = status_re.match(line)
            if m_status:
                status = m_status.group(1).strip()
                continue
            m_date = date_re.match(line)
            if m_date:
                date = m_date.group(1).strip()
                continue

        items.append(
            AdrInfo(
                number=number,
                title=title,
                status=status,
                date=date,
                path=f"adr/{f.name}",
            )
        )

    return AdrListResponse(success=True, items=items)


@router.post("/diagrams/list", response_model=DiagramListResponse)
async def list_diagrams(
    _admin: dict = Depends(require_admin),
) -> DiagramListResponse:
    """列出所有架構圖文件。"""
    diagrams_dir = DOCS_DIR / "diagrams"
    if not diagrams_dir.is_dir():
        return DiagramListResponse(success=True, items=[])

    heading_re = re.compile(r"^#\s+(.+)")

    items: list[DiagramInfo] = []
    for f in sorted(
        [*diagrams_dir.glob("*.md"), *diagrams_dir.glob("*.mmd")],
        key=lambda p: p.name,
    ):
        if f.name == "README.md":
            continue

        title = f.stem
        try:
            lines = f.read_text(encoding="utf-8").splitlines()[:10]
            for line in lines:
                m = heading_re.match(line)
                if m:
                    title = m.group(1).strip()
                    break
                # Mermaid frontmatter: title: xxx
                if line.strip().startswith("title:"):
                    title = line.strip().split("title:", 1)[1].strip()
                    break
        except Exception:
            logger.warning("無法讀取架構圖檔案: %s", f.name)

        items.append(
            DiagramInfo(
                name=f.name,
                path=f"diagrams/{f.name}",
                title=title,
            )
        )

    return DiagramListResponse(success=True, items=items)


# Allowed directories for search (superset of ALLOWED_SUBDIRS to cover all KB content)
_SEARCH_DIRS = ["knowledge-map", "adr", "diagrams", "reports", "specifications"]


@router.post("/search", response_model=KBSearchResponse)
async def search_knowledge_base(
    req: KBSearchRequest,
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
) -> KBSearchResponse:
    """混合搜尋知識庫內容：向量搜尋優先，文字搜尋兜底。"""
    from app.services.kb_embedding_service import KBEmbeddingService

    # Try vector search first
    kb_service = KBEmbeddingService(db)
    vector_results = await kb_service.search(req.query, limit=req.limit)

    if vector_results:
        results = [
            KBSearchResult(
                file_path=r["file_path"],
                filename=r["filename"],
                excerpt=r["content"][:500],
                line_number=0,
                relevance_score=r["score"],
            )
            for r in vector_results
        ]
        return KBSearchResponse(
            success=True,
            results=results,
            total=len(results),
            search_mode="vector",
        )

    # Fallback: text search on filesystem
    return _text_search_filesystem(req)


def _text_search_filesystem(req: KBSearchRequest) -> KBSearchResponse:
    """原始文字搜尋（檔案系統掃描）。"""
    query_lower = req.query.lower()
    results: list[KBSearchResult] = []

    for subdir_name in _SEARCH_DIRS:
        subdir = DOCS_DIR / subdir_name
        if not subdir.is_dir():
            continue

        for md_file in subdir.rglob("*.md"):
            # Security: ensure file is within DOCS_DIR
            try:
                md_file.resolve().relative_to(DOCS_DIR.resolve())
            except ValueError:
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                logger.warning("搜尋時無法讀取檔案: %s", md_file)
                continue

            lines = content.splitlines()
            rel_path = md_file.relative_to(DOCS_DIR).as_posix()

            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    excerpt = "\n".join(lines[start:end])

                    score = 2.0 if req.query in line else 1.0
                    results.append(
                        KBSearchResult(
                            file_path=rel_path,
                            filename=md_file.name,
                            excerpt=excerpt,
                            line_number=i + 1,
                            relevance_score=score,
                        )
                    )

    results.sort(key=lambda r: (-r.relevance_score, r.file_path, r.line_number))
    limited = results[: req.limit]
    return KBSearchResponse(
        success=True, results=limited, total=len(results), search_mode="text"
    )


@router.post("/embed", response_model=KBEmbedResponse)
async def trigger_kb_embedding(
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
) -> KBEmbedResponse:
    """觸發知識庫 Embedding 管線（掃描 docs/ → 分段 → 向量化）。"""
    from app.services.kb_embedding_service import KBEmbeddingService

    kb_service = KBEmbeddingService(db)
    try:
        stats = await kb_service.scan_and_embed()
    except Exception:
        logger.exception("KB embedding 管線失敗")
        raise HTTPException(status_code=500, detail="Embedding 管線執行失敗")

    return KBEmbedResponse(success=True, **stats)


@router.post("/code-wiki/module")
async def get_module_wiki(
    request: Request,
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """生成模組 Wiki (Gemma 4)"""
    body = await request.json()
    module_name = body.get("module_name", "")
    if not module_name:
        return JSONResponse({"success": False, "error": "缺少 module_name"})

    from app.services.ai.misc.code_wiki_generator import CodeWikiGenerator

    svc = CodeWikiGenerator(db)
    result = await svc.generate_module_wiki(module_name)
    return JSONResponse({"success": True, "data": result})


@router.post("/code-wiki/overview")
async def get_code_wiki_overview(
    request: Request,
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """程式碼 Wiki 總覽"""
    body = await request.json()
    limit = body.get("limit", 50)
    if not isinstance(limit, int) or limit < 1:
        limit = 50
    limit = min(limit, 200)

    from app.services.ai.misc.code_wiki_generator import CodeWikiGenerator

    svc = CodeWikiGenerator(db)
    result = await svc.generate_overview(limit=limit)
    return JSONResponse({"success": True, "data": result})


@router.post("/stats", response_model=KBStatsResponse)
async def get_kb_stats(
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
) -> KBStatsResponse:
    """取得知識庫 Embedding 統計資訊。"""
    from app.services.kb_embedding_service import KBEmbeddingService

    kb_service = KBEmbeddingService(db)
    stats = await kb_service.get_stats()
    return KBStatsResponse(success=True, **stats)


@router.post("/summarize-card")
async def summarize_knowledge_card(
    request: Request,
    _admin: dict = Depends(require_admin),
):
    """Gemma 4 生成知識卡片摘要"""
    body = await request.json()
    content = body.get("content", "")
    title = body.get("title", "")

    if not content and not title:
        return JSONResponse({"success": False, "error": "缺少 content 或 title"})

    from app.core.ai_connector import get_ai_connector

    ai = get_ai_connector()
    prompt = (
        f"為以下知識卡片生成 2-3 句摘要：\n\n"
        f"標題: {title}\n內容:\n{content[:1000]}\n\n"
        "摘要:"
    )
    try:
        summary = await ai.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
            task_type="summary",
        )
        return JSONResponse({"success": True, "summary": summary})
    except Exception as e:
        logger.error("summarize_knowledge_card failed: %s", e, exc_info=True)
        return JSONResponse({"success": False, "error": "摘要生成失敗，請稍後再試"})
