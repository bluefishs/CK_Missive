# -*- coding: utf-8 -*-
"""Crystallizer — Pattern → Synonym / Intent Rule 提案（結晶）

2026-04-19 Memory Wiki Phase 3 新建。
2026-04-30 v5.11 Phase 1：加 auto-apply（高 confidence proposal 自動 apply，
  打破「owner 14 天不批准」斷鏈，落實 KUNGE_LEARNING_VERIFICATION 鏈路 1B）。

職責：
- 掃 wiki/memory/patterns/*.md 找 crystallization_candidate: true
- 生成結晶提案 → 寫 wiki/memory/proposals/crystal-*.md
- v5.11：高 confidence 自動 apply（dry-run 為預設安全模式）
- 邊緣 case 仍進 proposals/ 等 owner 批

設計：
- 兩種結晶類型：synonym / intent_rule
- 目前主力 synonym（最常見、低風險）
- intent_rule 需 pattern 提供正則，暫時依 tool_sequence 推斷

Auto-apply 安全閘（v5.11）：
- env CRYSTAL_AUTO_APPLY_MODE = "dry-run" | "live"（預設 dry-run）
- confidence ≥ 0.9 才嘗試 auto-apply
- 僅 intent_rules.yaml（synonyms.yaml 仍需人批，較敏感）
- 沿用 yaml_safe_editor snapshot/rollback 雙閘
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

from app.core.paths import WIKI_MEMORY_PATTERNS_DIR as PATTERNS_DIR  # v6.10 P1-E SSOT
from app.core.paths import WIKI_MEMORY_PROPOSALS_DIR as PROPOSALS_DIR  # v6.10 P1-E SSOT

# 結晶門檻（比 pattern extractor 更嚴）
MIN_HIT_FOR_CRYSTAL = 5
MIN_SUCCESS_RATE_FOR_CRYSTAL = 0.95

# Auto-apply 安全參數（v5.11 Phase 1）
AUTO_APPLY_MIN_CONFIDENCE = 0.9
AUTO_APPLY_ALLOWED_TARGETS = {"intent_rules.yaml"}  # synonyms.yaml 仍需人批
AUTO_APPLY_MODE_ENV = "CRYSTAL_AUTO_APPLY_MODE"  # dry-run | live


@dataclass
class CrystalProposal:
    """結晶提案（待批准）。"""
    proposal_id: str
    kind: str  # "synonym" | "intent_rule"
    target_file: str  # "synonyms.yaml" | "intent_rules.yaml"
    source_pattern: str  # pattern_hash
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    created_at: str = ""


class Crystallizer:
    """掃 patterns/ 產結晶提案。"""

    def __init__(self):
        PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    async def scan_and_propose(self) -> List[CrystalProposal]:
        """掃所有 pattern 檔，為符合門檻者產出 proposal。"""
        if not PATTERNS_DIR.exists():
            return []

        proposals: List[CrystalProposal] = []
        for path in PATTERNS_DIR.glob("pattern-*.md"):
            try:
                meta = self._parse_pattern_meta(path)
                if not meta:
                    continue
                if not self._meets_crystal_threshold(meta):
                    continue
                # 檢查是否 7 日內已被拒絕
                if self._was_recently_rejected(meta["template_hash"]):
                    logger.debug(
                        "Skip %s: recently rejected within 7 days",
                        meta["template_hash"],
                    )
                    continue
                # 檢查是否已有 proposal
                if self._has_pending_proposal(meta["template_hash"]):
                    continue

                # 產 proposal（v5.8.0 解鎖多工具 pattern）：
                # _propose_synonym_from_pattern 產出 intent_rule kind，
                # payload 內 tool_preference 本就支援任意工具數（line 209），
                # 原 `len == 1` gate 是保守設計；移除後多工具 pattern 亦可
                # 生成 intent_rule proposal（語意：偏好此 tool_sequence）。
                # 仍由人類批准後才套用（non-destructive）。
                if meta.get("tool_sequence"):
                    p = self._propose_synonym_from_pattern(meta)
                    if p:
                        self._write_proposal(p)
                        proposals.append(p)

            except Exception as e:
                logger.warning("Pattern scan failed (%s): %s", path.name, e)

        logger.info("Crystallizer: proposed %d crystal(s)", len(proposals))

        # v5.11 Phase 1: Auto-apply 高 confidence proposal（落實鏈路 1B 閉環）
        await self._auto_apply_eligible(proposals)

        return proposals

    # ────────── Auto-apply (v5.11 Phase 1) ──────────

    @staticmethod
    def _confidence_score(meta: Dict[str, Any]) -> float:
        """從 pattern meta 計算 auto-apply confidence。

        綜合 hit_count（流量）+ success_rate（品質）：
        - hit ≥ 15 飽和到 hit_factor=1.0
        - success_rate 直接乘上 hit_factor

        舉例：
        - hit=6,  succ=1.00 → 0.40 * 1.00 = 0.40（low — 留 owner 批）
        - hit=10, succ=1.00 → 0.67 * 1.00 = 0.67（middle）
        - hit=15, succ=1.00 → 1.00 * 1.00 = 1.00（high → auto-apply）
        - hit=20, succ=0.90 → 1.00 * 0.90 = 0.90（剛達標）
        """
        hit = meta.get("hit_count", 0)
        succ = meta.get("success_rate", 0.0)
        hit_factor = min(1.0, hit / 15.0)
        return round(succ * hit_factor, 3)

    async def _auto_apply_eligible(self, proposals: List[CrystalProposal]) -> None:
        """掃 proposals，符合 auto-apply 條件的直接 apply（雙閘安全）。

        條件：
        1. mode=live（dry-run 模式只 log 不真改）
        2. confidence >= 0.9
        3. target_file in {intent_rules.yaml}
        4. CrystalApplier 內部 yaml_safe_editor 仍提供 snapshot/rollback

        v5.11 預設 dry-run，first week owner 確認 log 全合理才切 live。
        """
        mode = os.getenv(AUTO_APPLY_MODE_ENV, "dry-run").strip().lower()
        if mode not in ("dry-run", "live"):
            logger.warning("CRYSTAL_AUTO_APPLY_MODE=%s 不認識，fallback dry-run", mode)
            mode = "dry-run"

        applied_count = 0
        skipped_count = 0
        for p in proposals:
            try:
                # 重新讀 pattern meta 算 confidence
                pattern_meta = self._lookup_pattern_meta(p.source_pattern)
                if not pattern_meta:
                    continue
                confidence = self._confidence_score(pattern_meta)

                # 安全閘 1: confidence
                if confidence < AUTO_APPLY_MIN_CONFIDENCE:
                    skipped_count += 1
                    continue
                # 安全閘 2: target file
                if p.target_file not in AUTO_APPLY_ALLOWED_TARGETS:
                    logger.info(
                        "Auto-apply skip: target=%s not in allowlist (proposal=%s)",
                        p.target_file, p.proposal_id,
                    )
                    skipped_count += 1
                    continue

                if mode == "dry-run":
                    logger.info(
                        "[DRY-RUN] Auto-apply would trigger: %s confidence=%.3f target=%s",
                        p.proposal_id, confidence, p.target_file,
                    )
                    skipped_count += 1
                    continue

                # mode=live → 真 apply
                from app.services.memory.crystal_applier import CrystalApplier
                applier = CrystalApplier()
                result = await applier.apply_proposal(
                    p.proposal_id, approved_by="crystallizer-auto",
                )
                if result.ok:
                    applied_count += 1
                    logger.info(
                        "Auto-apply ok: %s → crystal=%s confidence=%.3f",
                        p.proposal_id, result.crystal_id, confidence,
                    )
                    # 通知 owner（best-effort）
                    await self._notify_auto_apply(p, confidence, result.crystal_id)
                else:
                    logger.warning(
                        "Auto-apply failed: %s error=%s",
                        p.proposal_id, result.error,
                    )

            except Exception as e:
                logger.error(
                    "Auto-apply error on %s: %s", p.proposal_id, e, exc_info=True,
                )

        logger.info(
            "Crystallizer auto-apply summary: mode=%s applied=%d skipped=%d",
            mode, applied_count, skipped_count,
        )

    def _lookup_pattern_meta(self, template_hash: str) -> Optional[Dict[str, Any]]:
        """從 patterns/ 找對應 hash 的 meta。"""
        if not PATTERNS_DIR.exists():
            return None
        for path in PATTERNS_DIR.glob("pattern-*.md"):
            meta = self._parse_pattern_meta(path)
            if meta and meta.get("template_hash") == template_hash:
                return meta
        return None

    @staticmethod
    async def _notify_auto_apply(
        proposal: CrystalProposal, confidence: float, crystal_id: Optional[str],
    ) -> None:
        """Best-effort 推通知（Telegram/LINE 任一即可）。失敗只 log。"""
        try:
            msg = (
                f"🔮 自動結晶通知\n"
                f"proposal={proposal.proposal_id[:30]}\n"
                f"crystal={crystal_id}\n"
                f"confidence={confidence:.2f}\n"
                f"target={proposal.target_file}\n"
                f"如需 rollback 請於 7 天內：crystal_applier rollback {crystal_id}"
            )
            tg_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if tg_chat:
                from app.services.integration.telegram_bot import get_telegram_bot_service
                tg = get_telegram_bot_service()
                if tg.enabled:
                    await tg.send_message(int(tg_chat), msg)
        except Exception as e:
            logger.debug("Auto-apply notify failed (non-critical): %s", e)

    # ────────── Parsing ──────────

    @staticmethod
    def _parse_pattern_meta(path: Path) -> Optional[Dict[str, Any]]:
        try:
            text = path.read_text(encoding="utf-8")
            fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not fm_match:
                return None
            fm = fm_match.group(1)

            meta: Dict[str, Any] = {}
            for key in ("template_hash",):
                m = re.search(rf"^{key}:\s*(.+?)\s*$", fm, re.MULTILINE)
                if m:
                    # 2026-04-24 ADR-0028：剝除可能的雙/單引號
                    # （寫端會加引號防 YAML int coercion，讀端需一致剝除）
                    val = m.group(1).strip()
                    if (val.startswith('"') and val.endswith('"')) or \
                       (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    meta[key] = val

            for int_key in ("hit_count", "success_count", "failure_count"):
                m = re.search(rf"^{int_key}:\s*(\d+)", fm, re.MULTILINE)
                if m:
                    meta[int_key] = int(m.group(1))

            rate_m = re.search(r"^success_rate:\s*([\d.]+)", fm, re.MULTILINE)
            if rate_m:
                meta["success_rate"] = float(rate_m.group(1))

            cand_m = re.search(r"^crystallization_candidate:\s*(True|False)", fm, re.MULTILINE)
            if cand_m:
                meta["crystallization_candidate"] = cand_m.group(1) == "True"

            # 2026-06-02 柱一閉合：pattern 檔 tool_sequence 是非引號 YAML 陣列
            # [search_documents, search_entities]（非合法 JSON）→ 原 json.loads 失敗
            # silent → tool_sequence 空 → crystal-intent proposal 生不出來（潛伏斷點）。
            # 改 split 解析（容忍引號與否）。
            seq_m = re.search(r"^tool_sequence:\s*\[(.*?)\]", fm, re.MULTILINE)
            if seq_m:
                inner = seq_m.group(1).strip()
                if inner:
                    meta["tool_sequence"] = [
                        t.strip().strip('"').strip("'")
                        for t in inner.split(",") if t.strip()
                    ]

            # 2026-06-02 柱一閉合 Step A：抽 example_questions（「## 典型問法」區段）
            # 供 crystal_applier 批准後 seed 進 PatternLearner（閉合 intent 終點）。
            # 排除「- (尚無示例)」佔位行。
            body = text[fm_match.end():]
            eq_m = re.search(r"##\s*典型問法\s*\n(.*?)(?:\n##|\Z)", body, re.DOTALL)
            if eq_m:
                questions = []
                for ln in eq_m.group(1).splitlines():
                    ln = ln.strip()
                    if ln.startswith("- ") and "尚無示例" not in ln:
                        q = ln[2:].strip()
                        if q:
                            questions.append(q)
                if questions:
                    meta["example_questions"] = questions

            return meta
        except Exception:
            return None

    @staticmethod
    def _meets_crystal_threshold(meta: Dict[str, Any]) -> bool:
        return (
            meta.get("crystallization_candidate", False)
            and meta.get("hit_count", 0) >= MIN_HIT_FOR_CRYSTAL
            and meta.get("success_rate", 0.0) >= MIN_SUCCESS_RATE_FOR_CRYSTAL
        )

    @staticmethod
    def _has_pending_proposal(template_hash: str) -> bool:
        """查是否有 pending 的 proposal 針對此 pattern。"""
        for path in PROPOSALS_DIR.glob("crystal-*.md"):
            try:
                text = path.read_text(encoding="utf-8")
                if template_hash in text and "status: pending" in text:
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _was_recently_rejected(template_hash: str) -> bool:
        """查 7 天內此 pattern 是否被拒絕過。"""
        from datetime import timedelta
        seven_days_ago = (datetime.now(TZ_TAIPEI) - timedelta(days=7))
        for path in PROPOSALS_DIR.glob("crystal-*.md"):
            try:
                text = path.read_text(encoding="utf-8")
                if template_hash not in text:
                    continue
                if "status: rejected" not in text:
                    continue
                # 找拒絕時間
                m = re.search(r"^rejected_at:\s*(\S+)", text, re.MULTILINE)
                if m:
                    try:
                        rej_time = datetime.fromisoformat(m.group(1))
                        if rej_time > seven_days_ago:
                            return True
                    except Exception:
                        pass
            except Exception:
                pass
        return False

    # ────────── Proposal generation ──────────

    # 通用停用詞 + 問句碎片（避免 regex 過寬或抓到無意義 ngram）
    _PATTERN_STOPWORDS = frozenset({
        "幾件", "幾筆", "多少", "查詢", "什麼", "哪些", "請問", "幫我", "我想",
        "目前", "現在", "資料", "相關", "如何", "怎麼", "可以", "提供",
        "告訴", "知道", "看看", "一下", "這個", "那個",
    })

    @classmethod
    def _derive_pattern_from_questions(cls, questions: List[str]) -> str:
        """從 example_questions 推導保守 regex pattern（供 owner 審核，非直接生效）。

        L1 (2026-06-03)：原 payload `pattern` 寫死空字串 → proposal 無觸發條件，
        owner 只能 defer（superseded 理由之一）。改從「典型問法」抽共現關鍵詞生成
        候選 regex。依 `adr-anti-half-wired-sop.md` regex 守則：
        - 用 2–3 字限定詞（滑動 ngram，非單字 OR）
        - 過濾通用停用詞 / 問句碎片
        - 需在 ≥2 問句共現（單一問句則放寬為 1）才採用
        - 無共現詞 → 回空字串（不亂生 dead rule）

        proposal 有 owner approve gate，候選 regex 不直接污染生產路由。
        """
        if not questions:
            return ""
        counter: Counter = Counter()
        for q in questions:
            grams = set()
            for seg in re.findall(r"[一-鿿]+", q):
                for n in (2, 3):
                    for i in range(len(seg) - n + 1):
                        grams.add(seg[i:i + n])
            for g in grams:
                counter[g] += 1
        threshold = 2 if len(questions) >= 2 else 1
        # 排除「完整等於或包含」任一停用詞的 gram（避免「問多少」「度如何」等碎片入 regex）
        common = [
            w for w, c in counter.most_common(15)
            if c >= threshold
            and not any(sw in w for sw in cls._PATTERN_STOPWORDS)
        ][:5]
        if not common:
            return ""
        return "|".join(re.escape(w) for w in common)

    def _propose_synonym_from_pattern(
        self, meta: Dict[str, Any],
    ) -> Optional[CrystalProposal]:
        """基於單工具 pattern 產生 synonym 提案（保守策略：不直接改 yaml）。

        簡化：先用佔位提案（說明此 pattern 常用同義詞機會），
        實質 synonym 推斷留給 LLM 階段（Phase 4+ 升級）。
        """
        # 此 phase 先做 skeleton：記錄高頻成功 pattern，推薦加「快速通道」intent_rule
        # 而非真正的 synonym（synonym 推斷需 NLP）
        tools = meta.get("tool_sequence", [])
        if not tools:
            return None

        proposal_id = f"crystal-intent-{meta['template_hash']}-{uuid.uuid4().hex[:6]}"
        return CrystalProposal(
            proposal_id=proposal_id,
            kind="intent_rule",
            target_file="intent_rules.yaml",
            source_pattern=meta["template_hash"],
            payload={
                "rule": {
                    "name": f"crystal_auto_{meta['template_hash']}",
                    # L1 (2026-06-03)：從 example_questions 推導候選 regex（取代寫死空字串）。
                    # 仍經 owner approve gate；無共現關鍵詞時回空（維持舊行為，不亂生）。
                    "pattern": self._derive_pattern_from_questions(
                        meta.get("example_questions", [])
                    ),
                    "tool_preference": tools,
                    "priority": 50,
                    "note": (
                        f"由 pattern {meta['template_hash']} 自動提議。"
                        f"hit={meta.get('hit_count', 0)} success_rate="
                        f"{meta.get('success_rate', 0):.0%}"
                    ),
                },
                "stats": {
                    "hit_count": meta.get("hit_count", 0),
                    "success_rate": meta.get("success_rate", 0),
                    "tool_sequence": tools,
                    # 2026-06-02 柱一閉合 Step A：帶 example_questions 供 seed PatternLearner
                    "example_questions": meta.get("example_questions", []),
                },
            },
            reason=(
                f"Pattern {meta['template_hash']} 已累積 "
                f"{meta.get('hit_count', 0)} 次使用，成功率 "
                f"{meta.get('success_rate', 0):.0%}，"
                f"tool_sequence={tools}。建議結晶為 intent_rule 加速路由。"
            ),
            created_at=datetime.now(TZ_TAIPEI).isoformat(),
        )

    def _write_proposal(self, p: CrystalProposal) -> Path:
        path = PROPOSALS_DIR / f"{p.proposal_id}.md"
        payload_yaml = _indent(
            "\n".join(
                f"{k}: {json.dumps(v, ensure_ascii=False)}"
                for k, v in p.payload.items()
            ),
            "  ",
        )
        content = f"""---
type: memory_proposal
proposal_kind: {p.kind}
target_file: {p.target_file}
source_pattern: {p.source_pattern}
proposed_by: agent
proposed_at: {p.created_at}
status: pending
reason: {json.dumps(p.reason, ensure_ascii=False)}
---

# Crystal Proposal: {p.proposal_id}

**Kind**: {p.kind}  |  **Target**: `{p.target_file}`

## Reason

{p.reason}

## Payload

```yaml
{payload_yaml}
```

## 批准流程

這是一個**結晶提案** — 將高頻成功 pattern 固化為規則。需人批准才會實際改動
`{p.target_file}`。批准後 CrystalApplier 會：

1. Snapshot 原 yaml 到 `wiki/memory/evolutions/yaml-snapshots/`
2. 套用 diff（ruamel.yaml 保留註解）
3. Validate 新 yaml 語法
4. 失敗自動 rollback
5. 寫 crystal record 到 `wiki/memory/crystals/`

批准 API（待 Phase 5 UI 實作）:
`POST /api/ai/memory/proposals/approve` with `proposal_id={p.proposal_id}`
"""
        path.write_text(content, encoding="utf-8")
        return path


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())
