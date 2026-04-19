# -*- coding: utf-8 -*-
"""Auto Defense Loader — 讀 failures/ 主動 defensive rule 注入 planner

2026-04-19 Memory Wiki Phase 2。

職責：
- 讀 wiki/memory/failures/*.md 中 active:true 的 defensive_rule
- 提供給 agent_planner.plan_tools() 注入 system prompt
- Redis 快取 5 分鐘（避免每次 plan 都讀檔）

用途：Agent 從過去失敗中學習，避開重複犯錯。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

FAILURES_DIR = Path(__file__).resolve().parents[4] / "wiki" / "memory" / "failures"

_CACHE: Optional[dict] = None
_CACHE_TTL_SECONDS = 300  # 5 min


class AutoDefenseLoader:
    """載入 failures/ 中 active 的 defensive_rule 清單。"""

    @classmethod
    async def load_active_defenses(cls, max_items: int = 5) -> List[str]:
        """回傳最多 max_items 條 active defense rule 文字。"""
        global _CACHE
        now = datetime.now()

        # Check cache
        if _CACHE and (now - _CACHE["at"]).total_seconds() < _CACHE_TTL_SECONDS:
            return _CACHE["rules"][:max_items]

        rules = cls._scan_active_failures(max_items)

        _CACHE = {"at": now, "rules": rules}
        return rules

    @staticmethod
    def _scan_active_failures(max_items: int) -> List[str]:
        """掃檔案，依 last_seen 新到舊、取前 max_items 條 active 防禦規則。"""
        if not FAILURES_DIR.exists():
            return []

        candidates = []
        for path in FAILURES_DIR.glob("failure-*.md"):
            try:
                text = path.read_text(encoding="utf-8")
                fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
                if not fm_match:
                    continue
                fm = fm_match.group(1)

                # 只看 active: true
                active_match = re.search(r"^active:\s*(true|false)", fm, re.MULTILINE | re.IGNORECASE)
                if not active_match or active_match.group(1).lower() != "true":
                    continue

                # 取 last_seen 用於排序
                last_seen_match = re.search(r"^last_seen:\s*(\S+)", fm, re.MULTILINE)
                last_seen = last_seen_match.group(1) if last_seen_match else ""

                # 取 Defensive Rule 區段內容
                rule_match = re.search(
                    r"##\s+🛡️?\s*Defensive Rule.*?\n(.*?)(?=\n##\s|\n---\s*\n|$)",
                    text, re.DOTALL,
                )
                if not rule_match:
                    continue
                rule_body = rule_match.group(1).strip()

                # 取 tool_sequence 作為 header
                seq_match = re.search(r"^tool_sequence:\s*(\[.*?\])", fm, re.MULTILINE)
                tools_hint = seq_match.group(1) if seq_match else ""

                candidates.append({
                    "last_seen": last_seen,
                    "rule": f"### 失敗教訓 {tools_hint}\n{rule_body}",
                })
            except Exception as e:
                logger.debug("Failure parse skipped (%s): %s", path.name, e)
                continue

        # 依 last_seen desc
        candidates.sort(key=lambda c: c["last_seen"], reverse=True)
        return [c["rule"] for c in candidates[:max_items]]


async def get_defensive_rules_block(max_items: int = 5) -> str:
    """便捷函式：回傳組合好的「失敗教訓」區塊，供 planner 直接 concat。"""
    rules = await AutoDefenseLoader.load_active_defenses(max_items=max_items)
    if not rules:
        return ""
    return "# 失敗教訓（過去 7 天的反思）\n\n" + "\n\n".join(rules)
