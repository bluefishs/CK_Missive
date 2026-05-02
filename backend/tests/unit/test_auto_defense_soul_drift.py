# -*- coding: utf-8 -*-
"""Auto Defense SOUL drift tests (v6.5 C2)

驗證 auto_defense 加上跨 repo SOUL 一致性防線：
- C1 cron 兜底：cron 跑失敗或還沒到 04:45 就被讀到時，至少能警示
- planner 收到此 defensive rule 時可調整人格相關回應的保守度
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_drift_cache(monkeypatch):
    """每個 test 前清快取，避免互相污染。"""
    from app.services.memory import auto_defense as ad
    monkeypatch.setattr(ad, "_SOUL_DRIFT_CACHE", None)
    monkeypatch.setattr(ad, "_CACHE", None)
    yield


def test_check_soul_drift_returns_none_when_source_missing(tmp_path, monkeypatch):
    """source SOUL 不存（dev env）→ 回 None。"""
    from app.services.memory import auto_defense as ad
    monkeypatch.setattr(ad, "SOUL_SOURCE_PATH", tmp_path / "nonexistent_source.md")
    monkeypatch.setattr(ad, "SOUL_MIRROR_PATH", tmp_path / "nonexistent_mirror.md")
    assert ad.check_soul_drift_defense() is None


def test_check_soul_drift_returns_none_when_identical(tmp_path, monkeypatch):
    """兩端內容相同（C1 cron 同步成功）→ 回 None。"""
    from app.services.memory import auto_defense as ad
    src = tmp_path / "soul_src.md"
    mir = tmp_path / "soul_mir.md"
    src.write_text("identical content", encoding="utf-8")
    mir.write_text("identical content", encoding="utf-8")
    monkeypatch.setattr(ad, "SOUL_SOURCE_PATH", src)
    monkeypatch.setattr(ad, "SOUL_MIRROR_PATH", mir)
    assert ad.check_soul_drift_defense() is None


def test_check_soul_drift_returns_rule_when_diverged(tmp_path, monkeypatch):
    """兩端不同 → 回 defensive rule 文字含關鍵警示詞。"""
    from app.services.memory import auto_defense as ad
    src = tmp_path / "soul_src.md"
    mir = tmp_path / "soul_mir.md"
    src.write_text("missive newer SOUL content xxxxx", encoding="utf-8")
    mir.write_text("aaap older SOUL content", encoding="utf-8")
    monkeypatch.setattr(ad, "SOUL_SOURCE_PATH", src)
    monkeypatch.setattr(ad, "SOUL_MIRROR_PATH", mir)

    rule = ad.check_soul_drift_defense()
    assert rule is not None
    assert "跨通道人格防線" in rule
    assert "drift" in rule.lower() or "drift" in rule
    # 字節大小資訊存在
    assert str(len(src.read_bytes())) in rule
    assert str(len(mir.read_bytes())) in rule


@pytest.mark.asyncio
async def test_get_defensive_rules_block_includes_soul_drift_first(tmp_path, monkeypatch):
    """drift 存在時，soul defense 排在 failures rule 之前（人格優先）。"""
    from app.services.memory import auto_defense as ad

    # 設兩端 SOUL 不同
    src = tmp_path / "src.md"
    mir = tmp_path / "mir.md"
    src.write_text("new SOUL", encoding="utf-8")
    mir.write_text("old SOUL different size", encoding="utf-8")
    monkeypatch.setattr(ad, "SOUL_SOURCE_PATH", src)
    monkeypatch.setattr(ad, "SOUL_MIRROR_PATH", mir)

    # 模擬 _scan_active_failures 回兩條
    monkeypatch.setattr(
        ad.AutoDefenseLoader,
        "_scan_active_failures",
        staticmethod(lambda max_items: [
            "### 失敗教訓 [tool_a]\nrule body 1",
            "### 失敗教訓 [tool_b]\nrule body 2",
        ]),
    )

    block = await ad.get_defensive_rules_block()
    # 人格防線在前
    soul_pos = block.find("跨通道人格防線")
    fail_pos = block.find("rule body 1")
    assert soul_pos > 0
    assert fail_pos > 0
    assert soul_pos < fail_pos


@pytest.mark.asyncio
async def test_get_defensive_rules_block_no_drift_no_soul_section(tmp_path, monkeypatch):
    """無 drift → block 不含人格防線（避免誤導）。"""
    from app.services.memory import auto_defense as ad

    src = tmp_path / "src.md"
    mir = tmp_path / "mir.md"
    src.write_text("same content", encoding="utf-8")
    mir.write_text("same content", encoding="utf-8")
    monkeypatch.setattr(ad, "SOUL_SOURCE_PATH", src)
    monkeypatch.setattr(ad, "SOUL_MIRROR_PATH", mir)

    monkeypatch.setattr(
        ad.AutoDefenseLoader,
        "_scan_active_failures",
        staticmethod(lambda max_items: ["### 失敗教訓 [tool_a]\nrule body 1"]),
    )

    block = await ad.get_defensive_rules_block()
    assert "跨通道人格防線" not in block
    assert "rule body 1" in block


def test_check_soul_drift_uses_cache(tmp_path, monkeypatch):
    """快取生效：第一次讀檔，第二次同 cache 不再讀。"""
    from app.services.memory import auto_defense as ad
    src = tmp_path / "src.md"
    mir = tmp_path / "mir.md"
    src.write_text("a", encoding="utf-8")
    mir.write_text("b", encoding="utf-8")
    monkeypatch.setattr(ad, "SOUL_SOURCE_PATH", src)
    monkeypatch.setattr(ad, "SOUL_MIRROR_PATH", mir)

    rule1 = ad.check_soul_drift_defense()
    # 假裝改檔（cache hit 應仍回原值）
    src.write_text("changed", encoding="utf-8")
    rule2 = ad.check_soul_drift_defense()
    # cache hit → 內容相同（即使檔案變了）
    assert rule1 == rule2
