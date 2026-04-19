#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wiki Narrative Batch Generator — 為 top 實體批次生成 synthesis narrative。

2026-04-19 新建。延續晨報 narrative 的突破血脈 — 把 KG 乾資料
升級為「有洞察」的 wiki synthesis 頁面，讓 agent 讀 wiki 時真正獲得價值。

流程：
1. 從 KG 抓 top N 機關（mention_count desc）+ top N 案件
2. 每個實體收集 context：mention_count + entity_type + 已有 wiki entity 頁摘要
3. LLM（Groq 70b）寫成 200-300 字 synthesis narrative
4. 存到 wiki/synthesis/{slug}.md

用法：
    python scripts/wiki_narrative_batch.py                  # 跑 top 10 機關 + top 10 案件
    python scripts/wiki_narrative_batch.py --agencies 20    # 調整數量
    python scripts/wiki_narrative_batch.py --dry-run        # 只輸出不存檔

env:
    WIKI_NARRATIVE_ENTITY_TYPES=org,project  # 可限定 type
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("wiki_narrative")

# Ensure backend importable
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))


_SYSTEM_PROMPT = """你是乾坤測繪公文系統的 wiki 編輯。你的工作是為知識圖譜裡的實體
（機關、案件、人物）寫一段 200-300 字的 narrative summary，讓 AI 助理在查詢時
能獲得「有洞察的背景」，而非只有乾資料。

**寫作原則**：
- 繁體中文，段落自然，不用列點
- 重點：這個實體在我們系統中扮演什麼角色（主要往來 / 重要案件 / 歷史脈絡）
- 若提供了歷史公文/案件線索，要點出模式（如「此機關多與某類型案件相關」）
- 實事求是：沒提供的資訊就別編（禁止發明統計數字、日期、人名）
- 結尾可留一句「關注點」（如「此機關案件多涉及 X，處理時留意 Y」）

**禁止**：
- 套話（如「本機關為重要合作夥伴」）
- 純 metadata 堆疊（如「mention_count: 283」）
- 用 # ## 等 markdown 標題
"""


def _build_user_prompt(entity: Dict[str, Any], context_snippets: List[str]) -> str:
    ent_type_cn = {
        "org": "機關",
        "project": "案件",
        "agency": "機關",
        "person": "人物",
    }.get(entity.get("entity_type", ""), "實體")

    snippets_block = "\n".join(f"- {s}" for s in context_snippets) if context_snippets else "（無）"

    return f"""實體名稱：{entity['canonical_name']}
實體類型：{ent_type_cn}
系統內被提及次數：{entity.get('mention_count', 0)}（代表與本系統業務關聯強度）

系統中有關此實體的線索（來自其他 wiki 頁 / 公文摘要）：
{snippets_block}

請為此實體寫一段 200-300 字 narrative summary。"""


async def _fetch_top_entities(
    db, entity_type: str, limit: int, domain: str = "knowledge",
) -> List[Dict[str, Any]]:
    from sqlalchemy import text
    rows = (await db.execute(
        text(
            "SELECT id, canonical_name, entity_type, mention_count, description "
            "FROM canonical_entities "
            "WHERE graph_domain=:d AND entity_type=:t AND mention_count > 0 "
            "ORDER BY mention_count DESC LIMIT :n"
        ),
        {"d": domain, "t": entity_type, "n": limit},
    )).all()
    return [
        {
            "id": r[0], "canonical_name": r[1],
            "entity_type": r[2], "mention_count": r[3],
            "description": r[4] or "",
        }
        for r in rows
    ]


async def _gather_context(wiki_svc, entity: Dict[str, Any], limit: int = 3) -> List[str]:
    """從既有 wiki entity 頁抓關聯線索。"""
    snippets = []
    try:
        # 搜 wiki 包含此名稱的頁面
        results = await wiki_svc.search_wiki(entity["canonical_name"], limit=limit)
        for r in results:
            try:
                content = await wiki_svc.read_page(r["path"])
                if not content:
                    continue
                # 取 frontmatter 後、前 200 字
                body = content.split("---", 2)[-1].strip()
                first_lines = body.splitlines()[:15]
                summary = " ".join(line.strip() for line in first_lines if line.strip())[:200]
                if summary:
                    snippets.append(f"[{r['title']}] {summary}")
            except Exception:
                continue
    except Exception as e:
        logger.debug("gather_context error for %s: %s", entity["canonical_name"], e)

    # 若描述非空也加入
    if entity.get("description"):
        snippets.append(f"[description] {entity['description'][:200]}")

    return snippets[:5]


async def _generate_narrative(ai, entity: Dict[str, Any], context: List[str]) -> str:
    user_prompt = _build_user_prompt(entity, context)
    result = await asyncio.wait_for(
        ai.chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=600,
            task_type="summary",
        ),
        timeout=45,
    )
    return (result or "").strip()


async def process_entity(
    ai, db, wiki_svc, entity: Dict[str, Any], *, dry_run: bool = False,
) -> Dict[str, Any]:
    name = entity["canonical_name"]
    try:
        context = await _gather_context(wiki_svc, entity)
        narrative = await _generate_narrative(ai, entity, context)

        if not narrative or len(narrative) < 80:
            return {"name": name, "status": "skipped", "reason": "narrative too short"}

        if "<think>" in narrative or "<start_of_thinking>" in narrative:
            return {"name": name, "status": "skipped", "reason": "thinking tags"}

        if dry_run:
            return {"name": name, "status": "dry_run", "preview": narrative[:200]}

        # 存 wiki/synthesis/
        sources = [f"kg_entity_id:{entity['id']} mention_count:{entity['mention_count']}"]
        tags = [entity["entity_type"], f"mention_{entity['mention_count']}"]
        r = await wiki_svc.save_synthesis(
            title=name, content_md=narrative, sources=sources, tags=tags,
        )
        return {"name": name, "status": "saved", "path": r.get("path", ""),
                "chars": len(narrative)}

    except asyncio.TimeoutError:
        return {"name": name, "status": "timeout"}
    except Exception as e:
        return {"name": name, "status": "error", "reason": str(e)[:100]}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agencies", type=int, default=10, help="top N agencies (org)")
    parser.add_argument("--projects", type=int, default=10, help="top N projects")
    parser.add_argument("--dry-run", action="store_true", help="不實際寫檔，只 preview")
    args = parser.parse_args()

    from app.db.database import AsyncSessionLocal
    from app.core.ai_connector import get_ai_connector
    from app.services.wiki_service import get_wiki_service

    ai = get_ai_connector()
    wiki_svc = get_wiki_service()

    async with AsyncSessionLocal() as db:
        agencies = await _fetch_top_entities(db, "org", args.agencies)
        projects = await _fetch_top_entities(db, "project", args.projects)

    targets = agencies + projects
    logger.info("目標實體: %d 機關 + %d 案件 = %d 總", len(agencies), len(projects), len(targets))

    results = []
    async with AsyncSessionLocal() as db:
        for i, ent in enumerate(targets, 1):
            logger.info("[%d/%d] %s (mention=%d)", i, len(targets),
                        ent["canonical_name"], ent["mention_count"])
            r = await process_entity(ai, db, wiki_svc, ent, dry_run=args.dry_run)
            logger.info("    → %s", {k: v for k, v in r.items() if k != "preview"})
            if "preview" in r:
                logger.info("    preview: %s...", r["preview"][:120])
            results.append(r)
            # 避免 Groq TPM 壓力，每筆間隔 1.5 秒
            await asyncio.sleep(1.5)

    # Summary
    from collections import Counter
    stats = Counter(r["status"] for r in results)
    logger.info("=" * 50)
    logger.info("Batch 完成統計: %s", dict(stats))
    if not args.dry_run:
        logger.info("Wiki synthesis 新增頁面數: %d", stats.get("saved", 0))

    return 0 if stats.get("saved", 0) > 0 or args.dry_run else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n中斷")
        sys.exit(130)
