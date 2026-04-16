# -*- coding: utf-8 -*-
"""
向後相容 re-export stub — NemoClawAgent 已重命名為 MissiveAgent (ADR-0014/0015)

所有新程式碼請使用:
    from app.services.ai.misc.missive_agent import MissiveAgent
"""
from app.services.ai.misc.missive_agent import MissiveAgent as NemoClawAgent  # noqa: F401

__all__ = ["NemoClawAgent"]
