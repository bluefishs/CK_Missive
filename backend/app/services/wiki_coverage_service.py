"""
Wiki ↔ KG 交叉比對服務

獨立雙源比對，不建立運行時依賴:
- KG 有但 Wiki 缺 → 潛在 wiki 擴充候選
- Wiki 有但 KG 缺 → KG NER 可能遺漏的實體
- 名稱模糊匹配 → 同一實體在兩系統的命名差異

Version: 1.0.0
Created: 2026-04-13
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.wiki_service import WIKI_ROOT

logger = logging.getLogger(__name__)


class WikiCoverageService:
    """Wiki ↔ KG 覆蓋率比對"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wiki_root = WIKI_ROOT

    async def compare(self) -> Dict[str, Any]:
        """全面比對 Wiki 與 KG 的覆蓋差異"""
        wiki_entities = self._scan_wiki_entities()
        kg_entities = await self._scan_kg_entities()

        # 正規化名稱比對
        wiki_names = {self._normalize(e["title"]): e for e in wiki_entities}
        kg_names = {self._normalize(e["name"]): e for e in kg_entities}

        wiki_set = set(wiki_names.keys())
        kg_set = set(kg_names.keys())

        # 完全匹配
        matched = wiki_set & kg_set
        wiki_only = wiki_set - kg_set
        kg_only = kg_set - wiki_set

        # 模糊匹配 (wiki_only 中可能有 KG 近似名)
        fuzzy_matches = []
        remaining_wiki_only = set()
        for wn in wiki_only:
            best = self._fuzzy_find(wn, kg_set)
            if best:
                fuzzy_matches.append({
                    "wiki": wiki_names[wn]["title"],
                    "kg": kg_names[best]["name"],
                    "wiki_type": wiki_names[wn].get("entity_type", ""),
                    "kg_type": kg_names[best].get("type", ""),
                })
            else:
                remaining_wiki_only.add(wn)

        return {
            "summary": {
                "wiki_total": len(wiki_entities),
                "kg_total": len(kg_entities),
                "exact_match": len(matched),
                "fuzzy_match": len(fuzzy_matches),
                "wiki_only": len(remaining_wiki_only),
                "kg_only": len(kg_only),
                "coverage_pct": round(
                    (len(matched) + len(fuzzy_matches)) / max(len(wiki_entities), 1) * 100, 1
                ),
            },
            "exact_matches": [
                {
                    "name": wiki_names[n]["title"],
                    "wiki_type": wiki_names[n].get("entity_type", ""),
                    "kg_type": kg_names[n].get("type", ""),
                    "kg_mentions": kg_names[n].get("mention_count", 0),
                }
                for n in sorted(matched)
            ][:50],
            "fuzzy_matches": fuzzy_matches[:30],
            "wiki_only": [
                {
                    "name": wiki_names[n]["title"],
                    "type": wiki_names[n].get("entity_type", ""),
                    "path": wiki_names[n].get("path", ""),
                }
                for n in sorted(remaining_wiki_only)
            ][:50],
            "kg_only_top": [
                {
                    "name": kg_names[n]["name"],
                    "type": kg_names[n].get("type", ""),
                    "mentions": kg_names[n].get("mention_count", 0),
                }
                for n in sorted(kg_only, key=lambda x: -(kg_names[x].get("mention_count") or 0))
            ][:50],
        }

    # =========================================================================
    # Internal
    # =========================================================================

    def _scan_wiki_entities(self) -> List[Dict]:
        """掃描 wiki/entities/ 所有頁面"""
        entities = []
        edir = self.wiki_root / "entities"
        if not edir.exists():
            return entities
        for f in edir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            title = f.stem
            tm = re.search(r'^title:\s*(.+)$', text, re.MULTILINE)
            if tm:
                title = tm.group(1).strip()
            etm = re.search(r'^entity_type:\s*(.+)$', text, re.MULTILINE)
            etype = etm.group(1).strip() if etm else "unknown"
            entities.append({
                "title": title,
                "entity_type": etype,
                "path": f"entities/{f.name}",
            })
        return entities

    async def _scan_kg_entities(self) -> List[Dict]:
        """查詢 KG canonical_entities (knowledge domain, mention_count > 0)"""
        from app.extended.models.knowledge_graph import CanonicalEntity

        stmt = (
            select(
                CanonicalEntity.canonical_name,
                CanonicalEntity.entity_type,
                CanonicalEntity.mention_count,
            )
            .where(
                CanonicalEntity.graph_domain == "knowledge",
                CanonicalEntity.mention_count > 0,
            )
            .order_by(desc(CanonicalEntity.mention_count))
            .limit(2000)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "name": r.canonical_name,
                "type": r.entity_type,
                "mention_count": r.mention_count,
            }
            for r in result.all()
        ]

    @staticmethod
    def _normalize(name: str) -> str:
        """正規化名稱 (去除空白/標點/括號內容)"""
        s = name.strip()
        s = re.sub(r'[（(][^)）]*[)）]', '', s)  # 去括號
        s = re.sub(r'[\s\u3000]+', '', s)  # 去空白
        s = re.sub(r'[，。、；：「」『』""''！？…—─\x2d]', '', s)  # 去標點
        return s.lower()

    @staticmethod
    def _fuzzy_find(target: str, candidates: Set[str], threshold: int = 3) -> Optional[str]:
        """簡易模糊匹配 — 找 candidates 中最短編輯距離者"""
        if len(target) < 4:
            return None
        best, best_score = None, threshold + 1
        # 用 substring 包含關係代替完整 edit distance (效能)
        for c in candidates:
            if target in c or c in target:
                overlap = len(target) if target in c else len(c)
                score = abs(len(target) - len(c))
                if score < best_score:
                    best, best_score = c, score
        return best
