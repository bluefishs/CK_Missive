# -*- coding: utf-8 -*-
"""
Wiki Entity Ingest Preserve Regression（2026-06-15）

鎖定缺陷：entity 頁面由 `WikiService.ingest_entity` 寫，原無條件
`created: {now}` 且 `kg_entity_id=None` 即省略該行 → 每週 wiki_compile
重編譯沖刷掉 backfill 補的 kg_entity_id（wiki↔KG 212→86 反覆回歸）
並重設首見日期。v6.15 的 `created` preserve 只補在 compiler._write_page
（topic/index 路徑），從未涵蓋 entity ingest 路徑。

修法：ingest_entity 更新既有頁面時，讀既有 frontmatter 保留
1. `created`（溯源首見日期）
2. `kg_entity_id`（新值 None 時保留舊連結，不以 None 沖掉）

本測試鎖定此兩項 preserve 行為。
"""
import asyncio
from pathlib import Path

import pytest

from app.services.wiki.service import WikiService


@pytest.fixture
def wiki_svc(tmp_path: Path) -> WikiService:
    svc = WikiService()
    svc.root = tmp_path
    svc.index_path = tmp_path / "index.md"
    svc.log_path = tmp_path / "log.md"
    (tmp_path / "entities").mkdir(parents=True, exist_ok=True)
    return svc


def _ingest(svc: WikiService, **kw):
    base = dict(
        name="112年_派工單號001",
        entity_type="dispatch",
        description="說明",
        sources=["dispatch #39"],
        tags=["派工單"],
    )
    base.update(kw)
    return asyncio.get_event_loop().run_until_complete(svc.ingest_entity(**base))


class TestWikiEntityIngestPreserve:
    def test_preserve_kg_entity_id_when_recompile_passes_none(self, wiki_svc: WikiService):
        """backfill 補 kg_entity_id 後，recompile（kg_entity_id=None）不得沖掉。"""
        _ingest(wiki_svc, kg_entity_id=261744)
        page = wiki_svc.root / "entities" / "112年_派工單號001.md"
        assert "kg_entity_id: 261744" in page.read_text(encoding="utf-8")

        # 模擬下次 wiki_compile：compile 期 _lookup_kg_id 配不到 → 傳 None
        _ingest(wiki_svc, kg_entity_id=None, description="說明（重編譯）")

        out = page.read_text(encoding="utf-8")
        assert "kg_entity_id: 261744" in out, "recompile 不得沖掉 backfill 既有連結"

    def test_preserve_created_on_update(self, wiki_svc: WikiService):
        """更新既有頁面 → created 沿用首見日期，非當日。"""
        _ingest(wiki_svc, kg_entity_id=100)
        page = wiki_svc.root / "entities" / "112年_派工單號001.md"
        # 手動把 created 改成過去日，模擬既有溯源
        txt = page.read_text(encoding="utf-8").replace(
            f"created: {__import__('app.services.wiki.service', fromlist=['_now_str'])._now_str()}",
            "created: 2026-01-01",
            1,
        )
        page.write_text(txt, encoding="utf-8")

        _ingest(wiki_svc, kg_entity_id=100, description="更新")

        out = page.read_text(encoding="utf-8")
        assert "created: 2026-01-01" in out, "created 應 preserve 首見日期"

    def test_explicit_kg_id_overrides_old(self, wiki_svc: WikiService):
        """明確傳新 kg_entity_id → 採新值（非 None 不觸發 preserve）。"""
        _ingest(wiki_svc, kg_entity_id=100)
        _ingest(wiki_svc, kg_entity_id=200)
        page = wiki_svc.root / "entities" / "112年_派工單號001.md"
        out = page.read_text(encoding="utf-8")
        assert "kg_entity_id: 200" in out
        assert "kg_entity_id: 100" not in out
