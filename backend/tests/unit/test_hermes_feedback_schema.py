# -*- coding: utf-8 -*-
"""Hermes feedback schema TDD — L4 學習閉環（ADR-0014）。

Hermes skill 執行完畢後回寫結果，供 Missive 端分析 skill 表現。
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_feedback_minimal():
    from app.schemas.hermes_acp import HermesFeedback

    fb = HermesFeedback(
        session_id="s1",
        skill_name="missive_document_search",
        outcome="success",
        latency_ms=420,
    )
    assert fb.session_id == "s1"
    assert fb.outcome == "success"


def test_feedback_outcome_enum():
    from app.schemas.hermes_acp import HermesFeedback

    with pytest.raises(ValidationError):
        HermesFeedback(
            session_id="s", skill_name="x", outcome="bogus", latency_ms=1,
        )


def test_feedback_negative_latency_rejected():
    from app.schemas.hermes_acp import HermesFeedback

    with pytest.raises(ValidationError):
        HermesFeedback(
            session_id="s", skill_name="x", outcome="success", latency_ms=-1,
        )


def test_feedback_satisfaction_range():
    from app.schemas.hermes_acp import HermesFeedback

    # 合法：0.0 ~ 1.0
    HermesFeedback(
        session_id="s", skill_name="x", outcome="success",
        latency_ms=1, user_satisfaction=0.8,
    )
    # 非法：> 1.0
    with pytest.raises(ValidationError):
        HermesFeedback(
            session_id="s", skill_name="x", outcome="success",
            latency_ms=1, user_satisfaction=1.5,
        )


def test_feedback_optional_fields_default():
    from app.schemas.hermes_acp import HermesFeedback

    fb = HermesFeedback(
        session_id="s", skill_name="x", outcome="failure", latency_ms=10,
    )
    assert fb.error_code is None
    assert fb.user_satisfaction is None
    assert fb.tools_used == []
