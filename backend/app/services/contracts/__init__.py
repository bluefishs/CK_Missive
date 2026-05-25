"""Bounded Context Contract Layer — v1.0 (2026-05-18)

統一 N bounded contexts 對外暴露的 facade interface，禁止跨 context 直 import
內部 module（強制走 facade）。

目的：
- 模組化：每個 context 可獨立打包成 wheel / docker image
- 移轉部署：consumer repo 可單獨採用某 context 不需拷貝整個 source repo
- 統一架構管理：跨 repo 用同一套 Port interface

4 cross-cutting Ports（取代散落直 import）：
  - MessagingPort   （channel adapters 統一：LINE / Telegram / Discord ...）
  - AuditPort       （取代散落 audit mixin 直接 inherit）
  - CachePort       （後端 cache cascade SSOT）
  - RLSPort         （封 row-level security 與 alias group expansion）

採用指南：見 CONTRACTS_LAYER_GUIDE.md
"""
from app.services.contracts.ports.messaging import MessagingPort  # noqa: F401
from app.services.contracts.ports.audit import AuditPort  # noqa: F401
from app.services.contracts.ports.cache import CachePort  # noqa: F401
from app.services.contracts.ports.rls import RLSPort  # noqa: F401

__all__ = ["MessagingPort", "AuditPort", "CachePort", "RLSPort"]
