# -*- coding: utf-8 -*-
"""
向後相容 re-export stub — 已重命名為 agent_capability.py (ADR-0014/0015)

⚠️ DEPRECATED（2026-04-25 強化標示）：
    - 此檔預計於 ADR-0020 Phase 1 啟動 + Hermes GO（ADR-0030, 5/20）後刪除
    - 新環境 sunset 目標：2026-05-26（NemoClaw/OpenClaw repo archive deadline）
    - 刪除前的觀察期：import 時發出 DeprecationWarning 協助定位殘留依賴

所有新程式碼請使用:
    from app.api.endpoints.ai.agent_capability import router

關聯:
    - ADR-0014 Hermes 取代 OpenClaw
    - ADR-0015 NemoClaw 退場 + Cloudflare Tunnel
    - ADR-0030 Hermes GO/NO-GO（5/20 決策）
    - docs/archive/nemoclaw-archival-checklist.md Sprint 4 stub 刪除
"""
import warnings

warnings.warn(
    "app.api.endpoints.ai.agent_nemoclaw is deprecated. "
    "Use 'app.api.endpoints.ai.agent_capability' instead (ADR-0014/0015). "
    "This stub will be removed after Hermes GO (ADR-0030, target 2026-05-26).",
    DeprecationWarning,
    stacklevel=2,
)

from app.api.endpoints.ai.agent_capability import router  # noqa: F401, E402
