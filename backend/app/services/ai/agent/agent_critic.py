# -*- coding: utf-8 -*-
"""Agent Critic — multi-agent 雛形（v6.0 POC，Gap 7 partial）

設計哲學（從單 agent → multi-agent 生態的第一步）：
- agent_planner: 規劃 tool calls（已存在）
- agent_synthesizer: 合成最終答案（在 orchestrator 內，已存在）
- **agent_critic（v6.0 新增）**: 審回答品質，回 critique signal

v6.0 範圍（POC，archetypal safety）：
- critic 不直接觸發 retry（避免無限迴圈 + LLM 成本爆炸）
- 只**寫 critique signal** 到 wiki/memory/critiques/
- 未來 v6.1+ 才接 retry loop（多輪反思 → planner 修正路徑）

關聯：
- KUNGE_INTELLIGENCE_GAP_ANALYSIS Gap 7 multi-agent
- KUNGE_PROGRESS_TRACKER §7 v6.x 戰略
- 對比 self_evaluator（純規則式評分）：critic 用 LLM 真做 reflection
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

CRITIQUES_DIR = Path(__file__).resolve().parents[5] / "wiki" / "memory" / "critiques"


class AgentCritic:
    """Critic agent — 審 query / answer 品質（v6.0 POC）。

    與 self_evaluator 區別：
    - self_evaluator: 純規則式（n-gram、entity_alignment）— 快但 superficial
    - AgentCritic:    可選 LLM 反思（成本高但深）— 抓 self_evaluator 抓不到的

    v6.0 不啟用 LLM 反思（避免成本爆炸），只用規則式 critique signal。
    v6.1+ 可加 use_llm 參數啟用 LLM 反思。
    """

    def __init__(self):
        CRITIQUES_DIR.mkdir(parents=True, exist_ok=True)

    async def review(
        self,
        question: str,
        answer: str,
        tools_used: List[str],
        eval_score: Dict[str, Any],
    ) -> Dict[str, Any]:
        """審 query/answer，回 critique。

        Args:
            question: 原 query
            answer: agent 給的 answer
            tools_used: 使用的工具清單
            eval_score: self_evaluator 的 EvalScore（含 entity_alignment 等）

        Returns:
            {
                "verdict": "ok" | "concern" | "fail",
                "critiques": [str, ...],
                "should_retry": bool,
            }
        """
        critiques: List[str] = []
        verdict = "ok"

        # Rule 1: entity_alignment（hallucination 警示）
        entity_alignment = eval_score.get("entity_alignment", 1.0)
        if entity_alignment < 0.5:
            critiques.append(
                f"entity_alignment={entity_alignment:.2f} < 0.5 — query 含具名 entity "
                f"但 answer 沒提到，疑似 hallucination"
            )
            verdict = "concern"

        # Rule 2: completeness（answer 太短）
        completeness = eval_score.get("completeness", 1.0)
        if completeness < 0.3 and len(answer) < 100:
            critiques.append(
                f"completeness={completeness:.2f} 且 answer 僅 {len(answer)} 字 — 過於簡陋"
            )
            verdict = "concern"

        # Rule 3: tool 失敗但仍給 confident answer（潛在 hallucination）
        all_tools_failed = (
            eval_score.get("tool_efficiency", 1.0) == 0.0
            and len(tools_used) > 0
        )
        if all_tools_failed and len(answer) > 200:
            critiques.append(
                f"所有工具失敗但 answer 仍 {len(answer)} 字 — 可能 LLM 自己編造"
            )
            verdict = "fail"

        # Rule 4: 工具組合 ≥ 3 但 entity_alignment 低（過度搜尋仍 miss）
        if len(tools_used) >= 3 and entity_alignment < 0.5:
            critiques.append(
                f"用了 {len(tools_used)} 個工具但 entity 仍未對齊 — query 主詞或 prompt 設計需修"
            )

        # v6.0 POC：never retry（避免 LLM 成本爆炸）
        # v6.1+ 可改 should_retry = (verdict == "fail")
        should_retry = False

        result = {
            "verdict": verdict,
            "critiques": critiques,
            "should_retry": should_retry,
        }

        # 寫 critique signal（供未來 v6.1 retry loop 用）
        if critiques:
            await self._persist_critique(question, answer, tools_used, result)

        return result

    async def _persist_critique(
        self,
        question: str,
        answer: str,
        tools_used: List[str],
        critique: Dict[str, Any],
    ) -> None:
        """寫 critique 到 wiki/memory/critiques/（fire-and-forget）。"""
        try:
            now = datetime.now(TZ_TAIPEI)
            filename = f"critique-{now:%Y%m%d-%H%M%S}-{abs(hash(question)) % 10000:04d}.md"
            path = CRITIQUES_DIR / filename
            content = (
                f"---\n"
                f"type: agent_critique\n"
                f"verdict: {critique['verdict']}\n"
                f"created_at: {now.isoformat()}\n"
                f"tools_used: {json.dumps(tools_used, ensure_ascii=False)}\n"
                f"should_retry: {critique['should_retry']}\n"
                f"---\n\n"
                f"# Critique\n\n"
                f"**Question**: {question[:200]}\n\n"
                f"**Answer preview**: {answer[:300]}\n\n"
                f"**Critiques**:\n"
            )
            for c in critique["critiques"]:
                content += f"- {c}\n"
            path.write_text(content, encoding="utf-8")
            logger.debug("Critique persisted: %s", filename)
        except Exception as e:
            logger.debug("persist critique failed: %s", e)


_critic_instance: Optional[AgentCritic] = None


def get_agent_critic() -> AgentCritic:
    global _critic_instance
    if _critic_instance is None:
        _critic_instance = AgentCritic()
    return _critic_instance


# ────────── v6.1 Phase 1: Planner Consumer 接通 ──────────

async def get_recent_critiques_block(
    days: int = 7, max_items: int = 3,
) -> str:
    """v6.1 Phase 1：抽近 N 天 critique 組 system prompt block。

    領域：multi-agent 學習迴圈 — agent_planner 規劃時看「過去 N 天 critic 抓出的問題」，
    避免重蹈覆轍。比 retry loop 更務實（無無限遞迴風險）。

    Returns:
        非空字串 = N 條最新 critique 警示 / 空字串 = 沒有近期 critique
    """
    import re
    from datetime import datetime, timedelta

    if not CRITIQUES_DIR.exists():
        return ""

    try:
        # 取最新 N 個 critique（按 mtime DESC）
        cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()
        files = sorted(
            [p for p in CRITIQUES_DIR.glob("critique-*.md")
             if p.stat().st_mtime >= cutoff_ts],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:max_items]

        if not files:
            return ""

        warnings: List[str] = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
                # 抓 question + 第一條 critique
                q_m = re.search(r"\*\*Question\*\*:\s*(.+?)(?:\n|$)", text)
                c_m = re.search(
                    r"\*\*Critiques\*\*:\s*\n(?:- )(.+?)(?:\n|$)",
                    text,
                )
                v_m = re.search(r"^verdict:\s*(\S+)", text, re.MULTILINE)
                if q_m and c_m:
                    q = q_m.group(1)[:60]
                    c = c_m.group(1)[:120]
                    v = v_m.group(1) if v_m else "?"
                    warnings.append(f"- ({v}) Q「{q}」: {c}")
            except Exception:
                continue

        if not warnings:
            return ""

        return (
            "# 過去 7 天 critic 抓出的問題（避免重蹈覆轍）\n\n"
            + "\n".join(warnings)
            + "\n\n_規劃時請對這些 pattern 警覺，特別是 entity_alignment 類問題。_"
        )
    except Exception as e:
        logger.debug("get_recent_critiques_block failed: %s", e)
        return ""
