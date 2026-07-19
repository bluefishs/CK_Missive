"""KnowledgeBaseService — 知識庫瀏覽器檔案系統邏輯（DDD 標準化，2026-07-20）

標準化收斂：原 endpoints/knowledge_base.py 的 tree/file/adr/diagrams/text-search
在端點內直接 Path.glob/read_text + regex 解析，繞過 service 層。抽出本 service 封裝
docs/ 檔案系統瀏覽與解析邏輯，端點薄委派。行為保真（含三層路徑驗證）。

search/embed 走 KBEmbeddingService（向量），本 service 僅負責檔案系統瀏覽 + 文字兜底。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

from fastapi import HTTPException

from app.core.paths import DOCS_DIR
from app.schemas.knowledge_base import (
    AdrInfo, DiagramInfo, FileInfo, KBSearchResult, SectionInfo,
)

logger = logging.getLogger(__name__)

ALLOWED_SUBDIRS = {"knowledge-map", "adr", "diagrams"}
# search 允許目錄（涵蓋所有 KB 內容，superset of ALLOWED_SUBDIRS）
SEARCH_DIRS = ["knowledge-map", "adr", "diagrams", "reports", "specifications"]


class KnowledgeBaseService:
    """docs/ 知識庫檔案系統瀏覽/解析（純檔案讀取，無 DB）。"""

    # ── 路徑安全（三層驗證）─────────────────────────────────────────
    @staticmethod
    def validate_path(user_path: str) -> Path:
        # Layer 1: 拒絕 traversal / 絕對路徑
        if ".." in user_path or user_path.startswith(("/", "\\")):
            raise HTTPException(status_code=400, detail="非法路徑")
        # Layer 2: 白名單子目錄 + 副檔名
        parts = Path(user_path).parts
        if not parts or parts[0] not in ALLOWED_SUBDIRS:
            raise HTTPException(status_code=400, detail="不允許的路徑")
        if not (user_path.endswith(".md") or user_path.endswith(".mmd")):
            raise HTTPException(status_code=400, detail="僅允許 .md / .mmd 檔案")
        # Layer 3: resolve + containment
        resolved = (DOCS_DIR / user_path).resolve()
        if not resolved.is_relative_to(DOCS_DIR.resolve()):
            raise HTTPException(status_code=403, detail="路徑越界")
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="檔案不存在")
        return resolved

    def read_file(self, user_path: str) -> tuple[str, str]:
        """回傳 (content, filename)；驗證失敗拋 HTTPException。"""
        resolved = self.validate_path(user_path)
        try:
            content = resolved.read_text(encoding="utf-8")
        except Exception:
            logger.exception("讀取知識庫檔案失敗: %s", user_path)
            raise HTTPException(status_code=500, detail="讀取檔案失敗")
        return content, resolved.name

    # ── 知識地圖目錄樹 ─────────────────────────────────────────────
    def build_tree(self) -> List[SectionInfo]:
        km_dir = DOCS_DIR / "knowledge-map"
        if not km_dir.is_dir():
            return []
        sections: List[SectionInfo] = []
        root_files = sorted(km_dir.glob("*.md"), key=lambda p: p.name)
        if root_files:
            sections.append(SectionInfo(
                name="_Root", path="knowledge-map",
                files=[FileInfo(name=f.name, path=f"knowledge-map/{f.name}") for f in root_files],
            ))
        subdirs = sorted([d for d in km_dir.iterdir() if d.is_dir()], key=lambda d: d.name)
        for subdir in subdirs:
            md_files = sorted(subdir.glob("*.md"), key=lambda p: p.name)
            if md_files:
                sections.append(SectionInfo(
                    name=subdir.name, path=f"knowledge-map/{subdir.name}",
                    files=[FileInfo(name=f.name, path=f"knowledge-map/{subdir.name}/{f.name}") for f in md_files],
                ))
        return sections

    # ── ADR 列表 ───────────────────────────────────────────────────
    def list_adrs(self) -> List[AdrInfo]:
        adr_dir = DOCS_DIR / "adr"
        if not adr_dir.is_dir():
            return []
        title_re = re.compile(r"^#\s+ADR-(\d+):\s*(.+)")
        status_re = re.compile(r">\s*\*\*狀態\*\*:\s*(.+)")
        date_re = re.compile(r">\s*\*\*日期\*\*:\s*(.+)")
        items: List[AdrInfo] = []
        for f in sorted(adr_dir.glob("0*.md"), key=lambda p: p.name):
            try:
                lines = f.read_text(encoding="utf-8").splitlines()[:10]
            except Exception:
                logger.warning("無法讀取 ADR 檔案: %s", f.name)
                continue
            number, title, status, date = "", f.stem, "", ""
            for line in lines:
                m = title_re.match(line)
                if m:
                    number, title = m.group(1), m.group(2).strip()
                    continue
                m = status_re.match(line)
                if m:
                    status = m.group(1).strip()
                    continue
                m = date_re.match(line)
                if m:
                    date = m.group(1).strip()
                    continue
            items.append(AdrInfo(number=number, title=title, status=status, date=date, path=f"adr/{f.name}"))
        return items

    # ── 架構圖列表 ─────────────────────────────────────────────────
    def list_diagrams(self) -> List[DiagramInfo]:
        diagrams_dir = DOCS_DIR / "diagrams"
        if not diagrams_dir.is_dir():
            return []
        heading_re = re.compile(r"^#\s+(.+)")
        items: List[DiagramInfo] = []
        for f in sorted([*diagrams_dir.glob("*.md"), *diagrams_dir.glob("*.mmd")], key=lambda p: p.name):
            if f.name == "README.md":
                continue
            title = f.stem
            try:
                for line in f.read_text(encoding="utf-8").splitlines()[:10]:
                    m = heading_re.match(line)
                    if m:
                        title = m.group(1).strip()
                        break
                    if line.strip().startswith("title:"):
                        title = line.strip().split("title:", 1)[1].strip()
                        break
            except Exception:
                logger.warning("無法讀取架構圖檔案: %s", f.name)
            items.append(DiagramInfo(name=f.name, path=f"diagrams/{f.name}", title=title))
        return items

    # ── 文字搜尋（向量兜底）────────────────────────────────────────
    def text_search(self, query: str, limit: int) -> tuple[List[KBSearchResult], int]:
        query_lower = query.lower()
        results: List[KBSearchResult] = []
        for subdir_name in SEARCH_DIRS:
            subdir = DOCS_DIR / subdir_name
            if not subdir.is_dir():
                continue
            for md_file in subdir.rglob("*.md"):
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
                        start, end = max(0, i - 2), min(len(lines), i + 3)
                        excerpt = "\n".join(lines[start:end])
                        score = 2.0 if query in line else 1.0
                        results.append(KBSearchResult(
                            file_path=rel_path, filename=md_file.name, excerpt=excerpt,
                            line_number=i + 1, relevance_score=score,
                        ))
        results.sort(key=lambda r: (-r.relevance_score, r.file_path, r.line_number))
        return results[:limit], len(results)
