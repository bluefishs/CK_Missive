# -*- coding: utf-8 -*-
"""Agent Critic entity tag tests (v6.4 I3)

驗證 critique 寫入時自動 tag 涉及 entity（從 question + answer 抽 NER）：
- 「哪些 entity 最常觸發 hallucination」可由 grep `entities:.*老蕭` 統計
- 為 KG ↔ Memory Wiki ❺ 弱連結補第一條 join key
"""
from __future__ import annotations

import json
import re
import pytest
from pathlib import Path


def test_extract_critique_entities_persons():
    """抽承辦人 / 老X / 小X 等人名暱稱。"""
    from app.services.ai.agent.agent_critic import _extract_critique_entities
    text = "承辦人老蕭今天要找小陳處理案件"
    entities = _extract_critique_entities(text)
    assert "老蕭" in entities
    assert "小陳" in entities


def test_extract_critique_entities_case_codes():
    """抽案件編號 / 派工單號。"""
    from app.services.ai.agent.agent_critic import _extract_critique_entities
    text = "案件 113-A567 與 115年_派工單號021 都是進行中"
    entities = _extract_critique_entities(text)
    assert any("113" in e for e in entities)
    assert any("派工單號021" in e for e in entities)


def test_extract_critique_entities_empty_when_no_match():
    """純 generic 句子 → 空 list。"""
    from app.services.ai.agent.agent_critic import _extract_critique_entities
    entities = _extract_critique_entities("今天天氣不錯適合散步")
    assert entities == []


def test_extract_critique_entities_dedup_and_cap():
    """重複 entity 去重，總數 ≤ 5。"""
    from app.services.ai.agent.agent_critic import _extract_critique_entities
    text = (
        "承辦人老蕭 老蕭再提一次 老蕭真的是承辦人 "
        "案件 111-001 案件 112-002 案件 113-003 案件 114-004 案件 115-005 案件 116-006"
    )
    entities = _extract_critique_entities(text)
    assert entities.count("老蕭") == 1
    assert len(entities) <= 5


@pytest.mark.asyncio
async def test_persist_critique_writes_entities_frontmatter(tmp_path, monkeypatch):
    """_persist_critique 寫入檔案時 frontmatter 含 entities 欄位 + body 含 Entities 行。"""
    from app.services.ai.agent import agent_critic as ac_mod
    from app.services.ai.agent.agent_critic import AgentCritic

    monkeypatch.setattr(ac_mod, "CRITIQUES_DIR", tmp_path)

    critic = AgentCritic()
    question = "承辦人老蕭負責的 113-A001 案件進度如何？"
    answer = "本案目前由團隊處理中，預計下週完成。"
    critique_result = {
        "verdict": "concern",
        "critiques": ["entity_alignment=0.20 < 0.5 — 疑似 hallucination"],
        "should_retry": False,
    }

    await critic._persist_critique(question, answer, ["search_documents"], critique_result)

    files = list(tmp_path.glob("critique-*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")

    # frontmatter entities 欄位（合法 JSON list）
    m = re.search(r"^entities:\s*(\[.*\])\s*$", content, re.MULTILINE)
    assert m, f"entities frontmatter missing in: {content[:200]}"
    parsed = json.loads(m.group(1))
    assert "老蕭" in parsed
    assert any("113" in e for e in parsed)

    # body 也應 surface entities
    assert "**Entities**:" in content
    assert "老蕭" in content


@pytest.mark.asyncio
async def test_persist_critique_no_entity_writes_empty_list(tmp_path, monkeypatch):
    """無 entity 抽中 → entities: [] 且 body 顯示 (none)。"""
    from app.services.ai.agent import agent_critic as ac_mod
    from app.services.ai.agent.agent_critic import AgentCritic

    monkeypatch.setattr(ac_mod, "CRITIQUES_DIR", tmp_path)

    critic = AgentCritic()
    question = "今天派工狀況如何"
    answer = "本日派工順暢"
    critique_result = {
        "verdict": "concern",
        "critiques": ["completeness=0.20 — 過於簡陋"],
        "should_retry": False,
    }

    await critic._persist_critique(question, answer, [], critique_result)

    files = list(tmp_path.glob("critique-*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")

    m = re.search(r"^entities:\s*(\[.*\])\s*$", content, re.MULTILINE)
    assert m
    assert json.loads(m.group(1)) == []
    assert "(none)" in content
