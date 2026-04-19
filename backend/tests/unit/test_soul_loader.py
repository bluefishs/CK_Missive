# -*- coding: utf-8 -*-
"""SoulLoader unit tests — Memory Wiki Phase 0 身份層驗證。"""
from __future__ import annotations

import pytest
from pathlib import Path


SAMPLE_SOUL = """---
title: Test SOUL
version: 1.2.3
last_modified_by: test
last_modified_at: 2026-04-19
agent_writable_sections:
  - "我的成長"
  - "我學到的偏好"
tags: [test]
---

# CK 助理 — 測試人格

你是測試版 CK 助理。

## 身份

- 你的名字是 **CK 助理**
- 專業、可靠

## 語言

- 繁體中文

## 語氣與風格

- 簡潔優先

## 行為準則

1. 第一條
2. 第二條

## 我的成長

<!-- agent_writable: true -->

_待首次週自傳生成_

## 我學到的偏好

_待首次結晶_
"""


@pytest.fixture
def temp_soul(tmp_path, monkeypatch):
    """Write sample SOUL.md to temp path and patch SOUL_PATH."""
    soul_file = tmp_path / "SOUL.md"
    soul_file.write_text(SAMPLE_SOUL, encoding="utf-8")

    # Also create proposals dir
    (tmp_path / "memory" / "proposals").mkdir(parents=True)

    from app.services.memory import soul_loader as sl
    monkeypatch.setattr(sl, "SOUL_PATH", soul_file)
    monkeypatch.setattr(sl, "PROPOSALS_DIR", tmp_path / "memory" / "proposals")

    # 清除 singleton 快取
    sl.SoulLoader._instance = None
    sl.SoulLoader._cache = None

    return soul_file


@pytest.mark.asyncio
async def test_load_parses_frontmatter(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul  # override

    schema = await loader.load_soul(force=True)

    assert schema.version == "1.2.3"
    assert schema.last_modified_by == "test"
    assert schema.last_modified_at == "2026-04-19"
    assert "我的成長" in schema.agent_writable_sections
    assert "我學到的偏好" in schema.agent_writable_sections
    assert len(schema.agent_writable_sections) == 2


@pytest.mark.asyncio
async def test_load_extracts_identity_block(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    schema = await loader.load_soul(force=True)

    assert "CK 助理" in schema.identity_block
    assert "專業、可靠" in schema.identity_block
    assert "繁體中文" in schema.identity_block
    assert "簡潔優先" in schema.identity_block


@pytest.mark.asyncio
async def test_load_extracts_behavior_block(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    schema = await loader.load_soul(force=True)

    assert "行為準則" in schema.behavior_block
    assert "第一條" in schema.behavior_block


@pytest.mark.asyncio
async def test_build_system_prompt_includes_identity(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    schema = await loader.load_soul(force=True)
    prompt = schema.build_system_prompt(role_context="agent")

    assert "CK 助理" in prompt
    assert "繁體中文" in prompt
    assert "行為準則" in prompt


@pytest.mark.asyncio
async def test_build_system_prompt_with_role_specific(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    schema = await loader.load_soul(force=True)
    prompt = schema.build_system_prompt(
        role_context="doc",
        role_specific_block="專門處理公文查詢，優先用 search_documents 工具。",
    )

    assert "CK 助理" in prompt
    assert "本次角色 (doc)" in prompt
    assert "search_documents" in prompt


@pytest.mark.asyncio
async def test_load_caches_by_mtime(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    first = await loader.load_soul(force=True)
    second = await loader.load_soul(force=False)  # 應該命中快取
    assert first is second  # 同一 instance


@pytest.mark.asyncio
async def test_load_invalidates_on_mtime_change(temp_soul):
    import time as _time
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    first = await loader.load_soul(force=True)
    # Modify file → 改變 mtime
    _time.sleep(0.1)
    temp_soul.write_text(SAMPLE_SOUL.replace("1.2.3", "1.3.0"), encoding="utf-8")

    second = await loader.load_soul(force=False)
    assert second.version == "1.3.0"
    assert first is not second  # 重新載入


@pytest.mark.asyncio
async def test_load_fallback_when_missing(tmp_path, monkeypatch):
    from app.services.memory import soul_loader as sl
    missing_path = tmp_path / "nonexistent.md"
    monkeypatch.setattr(sl, "SOUL_PATH", missing_path)
    sl.SoulLoader._instance = None
    sl.SoulLoader._cache = None

    loader = sl.SoulLoader(soul_path=missing_path)
    schema = await loader.load_soul(force=True)

    assert schema.version == "fallback"
    assert "CK 助理" in schema.identity_block  # fallback 最小人格


@pytest.mark.asyncio
async def test_propose_section_update_writable(temp_soul, tmp_path):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    proposal_id = await loader.propose_section_update(
        section_title="我的成長",
        new_text="本週我學會了跨年度標案比對。",
        reason="autobiography weekly update",
    )

    assert proposal_id is not None
    assert proposal_id.startswith("soul-")
    # 檔案確實建立
    proposals_dir = tmp_path / "memory" / "proposals"
    assert any(f.stem == proposal_id for f in proposals_dir.iterdir())


@pytest.mark.asyncio
async def test_propose_section_update_non_writable_rejected(temp_soul):
    from app.services.memory.soul_loader import get_soul_loader
    loader = get_soul_loader()
    loader.soul_path = temp_soul

    # 「身份」不在 agent_writable_sections
    proposal_id = await loader.propose_section_update(
        section_title="身份",
        new_text="我改名叫阿榮",
        reason="unauthorized self-rename",
    )

    assert proposal_id is None  # 拒絕
