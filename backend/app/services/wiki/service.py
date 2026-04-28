"""
LLM Wiki Service — 基於 Karpathy LLM Wiki Pattern 的知識 wiki 管理

三大操作:
- ingest: 來源 → KG + wiki 頁面 (自動建立/更新)
- query: wiki 頁面搜尋 → 綜合回答 (有價值的存入 synthesis/)
- lint: wiki 健康檢查 (孤立頁面、矛盾、缺失)

與 KG 互補: KG=結構化關係(機器), Wiki=敘述性知識(人類)

Version: 1.0.0
Created: 2026-04-09
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Wiki 根目錄
WIKI_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "wiki"


def _slugify(text: str) -> str:
    """將中文/英文標題轉為安全檔名"""
    text = text.strip()
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    text = re.sub(r'\s+', '_', text)
    return text[:80]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class WikiService:
    """LLM Wiki 管理服務"""

    def __init__(self):
        self.root = WIKI_ROOT
        self.index_path = self.root / "index.md"
        self.log_path = self.root / "log.md"

    # =========================================================================
    # Ingest — 來源攝入 → wiki 頁面
    # =========================================================================

    async def ingest_entity(
        self,
        name: str,
        entity_type: str,
        description: str,
        sources: List[str],
        tags: List[str],
        related_entities: Optional[List[str]] = None,
        confidence: str = "medium",
        kg_entity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """將實體寫入 wiki 頁面 (建立或更新)"""
        slug = _slugify(name)
        page_path = self.root / "entities" / f"{slug}.md"
        is_update = page_path.exists()

        # 建構 wiki links
        links = ""
        if related_entities:
            links = "\n".join(
                f"- [[entities/{_slugify(e)}|{e}]]"
                for e in related_entities
            )

        kg_line = f"\nkg_entity_id: {kg_entity_id}" if kg_entity_id else ""
        content = f"""---
title: {name}{kg_line}
type: entity
entity_type: {entity_type}
created: {_now_str()}
updated: {_now_str()}
sources: {sources}
tags: {tags}
confidence: {confidence}
---

# {name}

{description}

## 相關實體

{links or '*尚無關聯*'}

## 來源

{chr(10).join(f'- {s}' for s in sources) if sources else '*無來源*'}
"""
        page_path.write_text(content, encoding="utf-8")

        # 更新 log
        action = "update" if is_update else "ingest"
        self._append_log(action, f"entity | {name} ({entity_type})")

        logger.info("Wiki %s: entities/%s.md", action, slug)
        return {
            "action": action,
            "path": f"entities/{slug}.md",
            "name": name,
            "type": entity_type,
        }

    async def ingest_source(
        self,
        title: str,
        source_type: str,
        summary: str,
        key_points: List[str],
        entities_mentioned: List[str],
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """將來源摘要寫入 wiki"""
        slug = _slugify(title)
        page_path = self.root / "sources" / f"{slug}.md"

        entity_links = "\n".join(
            f"- [[entities/{_slugify(e)}|{e}]]"
            for e in entities_mentioned
        ) if entities_mentioned else "*無實體引用*"

        points_md = "\n".join(f"- {p}" for p in key_points) if key_points else "*無*"

        content = f"""---
title: {title}
type: source
source_type: {source_type}
source_id: {source_id or ''}
created: {_now_str()}
tags: {tags or []}
---

# {title}

## 摘要

{summary}

## 關鍵要點

{points_md}

## 提及的實體

{entity_links}
"""
        page_path.write_text(content, encoding="utf-8")
        self._append_log("ingest", f"source | {title} ({source_type})")

        logger.info("Wiki ingest: sources/%s.md", slug)
        return {"action": "ingest", "path": f"sources/{slug}.md", "title": title}

    async def save_synthesis(
        self,
        title: str,
        content_md: str,
        sources: List[str],
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """將綜合分析存入 wiki (查詢結果回存)"""
        slug = _slugify(title)
        page_path = self.root / "synthesis" / f"{slug}.md"

        full_content = f"""---
title: {title}
type: synthesis
created: {_now_str()}
sources: {sources}
tags: {tags or []}
---

# {title}

{content_md}
"""
        page_path.write_text(full_content, encoding="utf-8")
        self._append_log("synthesis", f"query → synthesis | {title}")

        return {"action": "synthesis", "path": f"synthesis/{slug}.md"}

    # =========================================================================
    # Query — wiki 搜尋
    # =========================================================================

    async def search_wiki(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜尋 wiki 頁面 (BM25-style keyword match on frontmatter + content)"""
        results = []
        query_lower = query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 1]

        for subdir in ["entities", "topics", "sources", "synthesis"]:
            dir_path = self.root / subdir
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                text_lower = text.lower()
                score = sum(
                    text_lower.count(kw) for kw in keywords
                )
                if score > 0:
                    # Extract title from frontmatter
                    title_match = re.search(r'^title:\s*(.+)$', text, re.MULTILINE)
                    title = title_match.group(1).strip() if title_match else f.stem
                    type_match = re.search(r'^type:\s*(.+)$', text, re.MULTILINE)
                    page_type = type_match.group(1).strip() if type_match else subdir

                    results.append({
                        "path": f"{subdir}/{f.name}",
                        "title": title,
                        "type": page_type,
                        "score": score,
                        "snippet": text[200:400].strip()[:150],
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def read_page(self, page_path: str) -> Optional[str]:
        """讀取指定 wiki 頁面"""
        full_path = self.root / page_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return None

    # =========================================================================
    # Lint — wiki 健康檢查
    # =========================================================================

    async def lint(self) -> Dict[str, Any]:
        """Wiki 健康檢查"""
        all_pages = []
        all_links = set()
        orphans = []
        broken_links = []
        page_count = {"entities": 0, "topics": 0, "sources": 0, "synthesis": 0}

        # 收集所有頁面
        for subdir in ["entities", "topics", "sources", "synthesis"]:
            dir_path = self.root / subdir
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                rel = f"{subdir}/{f.name}"
                all_pages.append(rel)
                page_count[subdir] = page_count.get(subdir, 0) + 1

        all_page_set = set(all_pages)

        # 檢查連結
        inbound: Dict[str, int] = {p: 0 for p in all_pages}
        for subdir in ["entities", "topics", "sources", "synthesis"]:
            dir_path = self.root / subdir
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                # 找 [[wiki links]]
                links = re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', text)
                for link in links:
                    link_path = link if link.endswith(".md") else f"{link}.md"
                    if link_path in all_page_set:
                        inbound[link_path] = inbound.get(link_path, 0) + 1
                    else:
                        broken_links.append({
                            "from": f"{subdir}/{f.name}",
                            "to": link_path,
                        })

        # 孤立頁面 (0 入站連結, 排除 index/log)
        orphans = [p for p, count in inbound.items() if count == 0]

        self._append_log("lint", f"pages={sum(page_count.values())} orphans={len(orphans)} broken={len(broken_links)}")

        return {
            "total_pages": sum(page_count.values()),
            "page_count": page_count,
            "orphan_pages": orphans,
            "broken_links": broken_links[:20],
            "health": "good" if not broken_links and len(orphans) < 3 else "needs_attention",
        }

    # =========================================================================
    # Graph — wiki 頁面圖譜 (force-graph 格���)
    # =========================================================================

    async def get_graph(self) -> Dict[str, Any]:
        """取得 wiki 頁面圖譜 — nodes + edges，供前端 force-graph 視覺化。

        Node 屬性: id, label, type (entity/topic/source/synthesis), doc_count
        Edge 屬性: source, target (wiki link 方向)
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        page_meta: Dict[str, Dict[str, Any]] = {}

        # Phase 1: 收集所有頁面 metadata
        for subdir in ["entities", "topics", "sources", "synthesis"]:
            dir_path = self.root / subdir
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                rel_path = f"{subdir}/{f.name}"
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue

                # 解析 frontmatter
                title = f.stem
                entity_type = subdir
                confidence = "medium"
                title_m = re.search(r'^title:\s*(.+)$', text, re.MULTILINE)
                if title_m:
                    title = title_m.group(1).strip()
                et_m = re.search(r'^entity_type:\s*(.+)$', text, re.MULTILINE)
                if et_m:
                    entity_type = et_m.group(1).strip()
                conf_m = re.search(r'^confidence:\s*(.+)$', text, re.MULTILINE)
                if conf_m:
                    confidence = conf_m.group(1).strip()

                # 統計公文數 (從描述中提取)
                doc_count = 0
                dc_m = re.search(r'共\s*(\d+)\s*件', text)
                if dc_m:
                    doc_count = int(dc_m.group(1))

                page_meta[rel_path] = {
                    "title": title[:50],
                    "type": subdir,
                    "entity_type": entity_type,
                    "confidence": confidence,
                    "doc_count": doc_count,
                    "content": text,
                }

        all_paths = set(page_meta.keys())

        # Phase 2: 建構 nodes + edges
        for path, meta in page_meta.items():
            nodes.append({
                "id": path,
                "label": meta["title"],
                "type": meta["type"],
                "entity_type": meta["entity_type"],
                "confidence": meta["confidence"],
                "doc_count": meta["doc_count"],
            })

            # 解析 wiki links
            links = re.findall(
                r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', meta["content"]
            )
            for link in links:
                target = link if link.endswith(".md") else f"{link}.md"
                if target in all_paths and target != path:
                    edges.append({"source": path, "target": target})

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "by_type": {
                    t: sum(1 for n in nodes if n["type"] == t)
                    for t in ["entities", "topics", "sources", "synthesis"]
                },
            },
        }

    # =========================================================================
    # Index — 更新索引
    # =========================================================================

    async def rebuild_index(self) -> Dict[str, int]:
        """重建 index.md"""
        sections = {}
        for subdir in ["entities", "topics", "sources", "synthesis"]:
            dir_path = self.root / subdir
            if not dir_path.exists():
                continue
            pages = []
            for f in sorted(dir_path.glob("*.md")):
                try:
                    text = f.read_text(encoding="utf-8")
                except Exception:
                    continue
                title_match = re.search(r'^title:\s*(.+)$', text, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else f.stem
                pages.append(f"- [{title}]({subdir}/{f.name})")
            sections[subdir] = pages

        labels = {
            "entities": "Entities (實體)",
            "topics": "Topics (主題)",
            "sources": "Sources (來源摘要)",
            "synthesis": "Synthesis (綜合分析)",
        }

        lines = ["# CK_Missive Wiki Index\n"]
        for subdir, label in labels.items():
            lines.append(f"\n## {label}\n")
            if sections.get(subdir):
                lines.extend(sections[subdir])
            else:
                lines.append("*尚無頁面*")
        lines.append(f"\n---\n**統計**: {' | '.join(f'{len(sections.get(k, []))} {k}' for k in labels)}")
        lines.append(f"**最後更新**: {_now_str()}")

        self.index_path.write_text("\n".join(lines), encoding="utf-8")

        counts = {k: len(v) for k, v in sections.items()}
        logger.info("Wiki index rebuilt: %s", counts)
        return counts

    # =========================================================================
    # Internal
    # =========================================================================

    def _append_log(self, action: str, detail: str):
        """追加操作日誌"""
        entry = f"\n## [{_now_str()}] {action} | {detail}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def get_stats(self) -> Dict[str, int]:
        """快速統計"""
        counts = {}
        for subdir in ["entities", "topics", "sources", "synthesis"]:
            dir_path = self.root / subdir
            if dir_path.exists():
                counts[subdir] = len(list(dir_path.glob("*.md")))
            else:
                counts[subdir] = 0
        counts["total"] = sum(counts.values())
        return counts


# Singleton
_wiki_service: Optional[WikiService] = None


def get_wiki_service() -> WikiService:
    global _wiki_service
    if _wiki_service is None:
        _wiki_service = WikiService()
    return _wiki_service
