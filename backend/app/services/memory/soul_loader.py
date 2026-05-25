# -*- coding: utf-8 -*-
"""SOUL.md 載入器 — 身份層（三層智能記憶 L0）

2026-04-19 Memory Wiki Phase 0 新建。

職責：
- 從 wiki/SOUL.md 載入 Agent 人格定義
- 提供 propose/apply/rollback 流程（Agent 自動編輯需人批准）
- class-level 快取 + mtime 失效

⚠️ 跨 repo 同步（v5.9.6 修正：原宣稱「同步鏡像」實為 docstring lie）：
- wiki/SOUL.md 是 Missive 的 SSOT
- CK_AaaP/runbooks/hermes-stack/SOUL.md 為 Hermes gateway 用
- **無自動同步**，避免跨 repo 寫覆蓋 AaaP 端手動 edit
- 手動同步：bash scripts/sync/sync_soul_to_hermes.sh --apply
- Drift 偵測：python scripts/checks/soul_mirror_drift_check.py

安全設計：
- Agent 無法直接改 SOUL.md
- 所有編輯經 propose_section_update() → 寫 wiki/memory/proposals/
- 人批准後 apply_proposal() 才實際改 + 備份舊版

Usage:
    from app.services.memory.soul_loader import get_soul_loader
    soul = await get_soul_loader().load_soul()
    prompt = soul.build_system_prompt(role_context="agent")
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# wiki/SOUL.md 位置（相對專案根）— v6.10 P1-E SSOT
from app.core.paths import WIKI_SOUL_PATH as SOUL_PATH, WIKI_MEMORY_PROPOSALS_DIR as PROPOSALS_DIR


@dataclass
class SoulSchema:
    """SOUL.md 解析結果。"""
    version: str = "0.0.0"
    last_modified_by: str = "unknown"
    last_modified_at: str = ""
    agent_writable_sections: List[str] = field(default_factory=list)

    # 主要內容（用於注入 system prompt）
    full_text: str = ""
    identity_block: str = ""  # 身份 + 語言 + 語氣三個核心區段
    behavior_block: str = ""  # 行為準則
    growth_block: str = ""    # 我的成長（agent-writable）
    preference_block: str = ""  # 我學到的偏好
    capability_block: str = ""  # 我的能力自評

    # 中繼資訊
    loaded_at: Optional[datetime] = None
    source_mtime: float = 0.0

    def build_system_prompt(
        self,
        role_context: str = "agent",
        role_specific_block: Optional[str] = None,
    ) -> str:
        """組合成 system prompt。

        Args:
            role_context: 角色上下文（agent/doc/dispatch...）
            role_specific_block: 角色特定指令（會附加在 SOUL 基底之後）
        """
        # 核心基底 = 身份 + 語氣 + 行為 + 能力邊界（不含 agent-writable 區段的詳細內容）
        # 避免 prompt 過長，agent-writable 區段只放摘要
        parts = [self.identity_block.strip()]

        if self.behavior_block:
            parts.append(self.behavior_block.strip())

        # agent-writable 區段摘要（取第一行 + 截斷）
        writable_summary = []
        if self.growth_block and "待首次" not in self.growth_block:
            growth_short = self.growth_block.strip()[:300]
            writable_summary.append(f"## 我最近的成長\n{growth_short}")
        if self.preference_block and "待首次" not in self.preference_block:
            pref_short = self.preference_block.strip()[:200]
            writable_summary.append(f"## 我學到的偏好\n{pref_short}")
        if writable_summary:
            parts.append("\n\n".join(writable_summary))

        if role_specific_block:
            parts.append(f"## 本次角色 ({role_context})\n{role_specific_block.strip()}")

        return "\n\n---\n\n".join(parts)


class SoulLoader:
    """SOUL.md 載入 + 解析 + 快取。"""

    _instance: Optional["SoulLoader"] = None
    _cache: Optional[SoulSchema] = None

    def __init__(self, soul_path: Optional[Path] = None):
        self.soul_path = soul_path or SOUL_PATH

    @classmethod
    def get_instance(cls) -> "SoulLoader":
        if cls._instance is None:
            cls._instance = SoulLoader()
        return cls._instance

    async def load_soul(self, force: bool = False) -> SoulSchema:
        """載入 SOUL.md，class-level 快取 + mtime 失效。"""
        try:
            if not self.soul_path.exists():
                logger.warning("SOUL.md not found at %s — using fallback", self.soul_path)
                return self._fallback_soul()

            current_mtime = self.soul_path.stat().st_mtime

            # 快取命中
            if (not force and self._cache and self._cache.source_mtime == current_mtime):
                return self._cache

            # 讀檔 + parse
            raw = self.soul_path.read_text(encoding="utf-8")
            schema = self._parse(raw)
            schema.source_mtime = current_mtime
            schema.loaded_at = datetime.now()

            self._cache = schema
            logger.info(
                "SOUL.md loaded (v=%s, mtime=%.0f, %d chars)",
                schema.version, current_mtime, len(raw),
            )
            return schema
        except Exception as e:
            logger.error("Failed to load SOUL.md: %s", e, exc_info=True)
            return self._fallback_soul()

    def _parse(self, raw: str) -> SoulSchema:
        """Parse YAML frontmatter + sections."""
        schema = SoulSchema(full_text=raw)

        # Frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", raw, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            body = fm_match.group(2)
            schema.version = self._fm_get(fm_text, "version", "0.0.0")
            schema.last_modified_by = self._fm_get(fm_text, "last_modified_by", "unknown")
            schema.last_modified_at = self._fm_get(fm_text, "last_modified_at", "")
            writable_lines = self._fm_get_list(fm_text, "agent_writable_sections")
            schema.agent_writable_sections = writable_lines
        else:
            body = raw

        # Sections — 用 ## 標題分段
        sections = self._split_sections(body)

        # 核心識別區段（合併）
        # v5.8.0 ADR-0022/0026：擴充擷取 SOUL v2.0 坤哥人格的三信念、反迴聲室、倫理紅線
        # 使用 fuzzy match — section title 含關鍵字即擷取（容錯版本差異）
        identity_parts = []
        identity_keywords = [
            "身份",           # 身份 / 身份宣言
            "三信念",         # 三信念（世界觀底層）
            "反迴聲室",       # 反迴聲室協議
            "倫理紅線",       # 倫理紅線（不可逾越）
            "語言",           # 語言
            "語氣與風格",     # 語氣與風格
            "三層智能記憶架構", # 三層智能記憶架構（你的心智）
        ]
        # 維持 keyword 出現順序 + 避免重複擷取同一 section
        matched_titles: set = set()
        for keyword in identity_keywords:
            for section_title, section_body in sections.items():
                if keyword in section_title and section_title not in matched_titles:
                    identity_parts.append(f"## {section_title}\n{section_body}")
                    matched_titles.add(section_title)
                    break
        # 加頂部 intro（第一個 ## 前的文字）
        intro_match = re.match(r"^(.*?)(?=\n##\s)", body, re.DOTALL)
        if intro_match:
            intro = intro_match.group(1).strip()
            if intro:
                identity_parts.insert(0, intro)
        schema.identity_block = "\n\n".join(identity_parts)

        # 行為準則
        if "行為準則" in sections:
            schema.behavior_block = f"## 行為準則\n{sections['行為準則']}"

        # Agent-writable
        schema.growth_block = sections.get("我的成長", "")
        schema.preference_block = sections.get("我學到的偏好", "")
        schema.capability_block = sections.get("我的能力自評", "")

        return schema

    @staticmethod
    def _fm_get(fm_text: str, key: str, default: str = "") -> str:
        m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", fm_text, re.MULTILINE)
        return m.group(1).strip() if m else default

    @staticmethod
    def _fm_get_list(fm_text: str, key: str) -> List[str]:
        """解析 yaml list 欄位（簡易版，只支援 - "item" 多行格式）"""
        lines = fm_text.split("\n")
        items: List[str] = []
        in_target = False
        indent = 0
        for line in lines:
            stripped = line.rstrip()
            if stripped == f"{key}:":
                in_target = True
                continue
            if in_target:
                m = re.match(r"^(\s*)-\s+[\"']?([^\"']+?)[\"']?\s*$", line)
                if m:
                    if indent == 0:
                        indent = len(m.group(1))
                    items.append(m.group(2).strip())
                elif stripped and not stripped.startswith(" "):
                    in_target = False
        return items

    @staticmethod
    def _split_sections(body: str) -> Dict[str, str]:
        """把 markdown body 依 ## heading 切段。"""
        sections: Dict[str, str] = {}
        # Match "## 標題\n內容..." 直到下個 "## " 或檔尾
        pattern = re.compile(r"^##\s+(.+?)\s*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL)
        for m in pattern.finditer(body):
            title = m.group(1).strip()
            content = m.group(2).strip()
            # 移除 agent_writable 註釋
            content = re.sub(r"<!--\s*agent_writable.*?-->\s*", "", content)
            sections[title] = content
        return sections

    def _fallback_soul(self) -> SoulSchema:
        """SOUL.md 不可用時的最小人格（避免 Agent 啞口）。"""
        return SoulSchema(
            version="fallback",
            identity_block=(
                "# CK 助理\n\n"
                "你是 CK 助理，乾坤測繪公司的 AI 助理。專業、簡潔、使用繁體中文。"
                "Missive 後端為唯一事實來源。"
            ),
            behavior_block="## 行為準則\n查不到就說查不到，不杜撰。",
        )

    # ────────── Propose / Apply / Rollback ──────────
    # （Phase 4 autobiography 會用到；Phase 0 先建 skeleton）

    async def propose_section_update(
        self,
        section_title: str,
        new_text: str,
        reason: str,
        proposed_by: str = "agent",
    ) -> Optional[str]:
        """提案更新 agent-writable 區段。寫 proposal 檔，不改 SOUL。

        Returns:
            proposal_id（檔名 slug）或 None（區段非 agent-writable 時）
        """
        schema = await self.load_soul()
        if section_title not in schema.agent_writable_sections:
            logger.warning(
                "Cannot propose update to non-writable section: %s", section_title,
            )
            return None

        PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        proposal_id = f"soul-{section_title.replace(' ', '-')}-{datetime.now():%Y%m%d-%H%M%S}"
        proposal_path = PROPOSALS_DIR / f"{proposal_id}.md"

        proposal_content = f"""---
type: memory_proposal
proposal_kind: soul_section
target_file: wiki/SOUL.md
target_section: {section_title}
proposed_by: {proposed_by}
proposed_at: {datetime.now().isoformat()}
reason: {reason}
status: pending
---

# Proposal: 更新 SOUL 區段「{section_title}」

**原因**: {reason}

## 建議新內容

{new_text}

---

## 批准流程

此提案改動 Agent 身份層，需人工批准後才會寫入 `wiki/SOUL.md`。
批准 API: `POST /api/ai/memory/proposals/approve` with `proposal_id={proposal_id}`
"""
        proposal_path.write_text(proposal_content, encoding="utf-8")
        logger.info("SOUL section proposal written: %s", proposal_id)
        return proposal_id


def get_soul_loader() -> SoulLoader:
    """Singleton 入口。"""
    return SoulLoader.get_instance()
