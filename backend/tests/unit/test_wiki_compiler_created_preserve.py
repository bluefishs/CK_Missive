# -*- coding: utf-8 -*-
"""
Wiki Compiler `created` Preserve Regression（2026-06-09 / v6.15）

鎖定缺陷：compiler.py 17 處頁面寫檔皆內嵌 `created: {datetime.now()}`，
每次 cron 重編譯都把 entity 的 frontmatter `created` 重設為當日
→ 166 個 entity 首見日期被污染（溯源語意失真）。

修法：集中式 `WikiCompiler._write_page(path, content)` 在覆寫前讀取既有檔
的 `created`，若存在則沿用，僅首次建立時用今日。

本測試鎖定：
1. 既有檔案重寫時，frontmatter `created` 必須 preserve 原值（非當日）。
2. 不存在的檔案（首次建立）保留 content 帶入的 created。
3. 只替換 frontmatter 第一個 created，不誤動 body 內的 created 文字。
"""
from pathlib import Path

from app.services.wiki.compiler import WikiCompiler


def _entity(created: str, body_extra: str = "") -> str:
    return (
        "---\n"
        "title: 測試派工\n"
        "type: entity\n"
        "entity_type: dispatch\n"
        f"created: {created}\n"
        f"updated: {created}\n"
        "---\n\n"
        "# 測試派工\n"
        f"{body_extra}"
    )


class TestWikiCompilerCreatedPreserve:
    def test_preserve_existing_created(self, tmp_path: Path):
        """既有檔重寫 → created 沿用原值。"""
        p = tmp_path / "entity.md"
        p.write_text(_entity("2026-01-01"), encoding="utf-8")

        # 重編譯內容帶今日 created（模擬 datetime.now()）
        WikiCompiler._write_page(p, _entity("2026-06-09"))

        out = p.read_text(encoding="utf-8")
        assert "created: 2026-01-01" in out, "created 應 preserve 原始首見日期"
        assert "created: 2026-06-09" not in out, "created 不得被重設為當日"

    def test_first_create_keeps_new_created(self, tmp_path: Path):
        """首次建立（檔不存在）→ 保留 content 帶入的 created。"""
        p = tmp_path / "new_entity.md"
        WikiCompiler._write_page(p, _entity("2026-06-09"))

        out = p.read_text(encoding="utf-8")
        assert "created: 2026-06-09" in out

    def test_only_frontmatter_created_replaced(self, tmp_path: Path):
        """body 內若出現 created 字樣不得被誤改（只換 frontmatter 第一個）。"""
        p = tmp_path / "entity.md"
        p.write_text(_entity("2026-01-01"), encoding="utf-8")

        body = "| 欄位 | created: 2026-06-09 在表格內 |\n"
        WikiCompiler._write_page(p, _entity("2026-06-09", body_extra=body))

        out = p.read_text(encoding="utf-8")
        # frontmatter 沿用原值
        assert out.count("created: 2026-01-01") == 1
        # body 內的 created 文字保留（不被 preserve 邏輯波及）
        assert "created: 2026-06-09 在表格內" in out
