# -*- coding: utf-8 -*-
"""Crystal Applier — 批准 crystal proposal 後實際改 yaml（snapshot + validate + rollback）

2026-04-19 Memory Wiki Phase 3 新建。

安全閘：
1. snapshot 原 yaml（備份到 wiki/memory/evolutions/yaml-snapshots/）
2. apply diff via yaml_safe_editor
3. validate 新 yaml 語法
4. 失敗自動 rollback
5. 成功寫 crystal record
"""
from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from zoneinfo import ZoneInfo

from app.services.memory.yaml_safe_editor import (
    add_synonym_group,
    add_intent_rule,
    validate_yaml,
)

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

from app.core.paths import PROJECT_ROOT, BACKEND_DIR  # v6.10 P1-E SSOT
PROPOSALS_DIR = PROJECT_ROOT / "wiki" / "memory" / "proposals"
CRYSTALS_DIR = PROJECT_ROOT / "wiki" / "memory" / "crystals"
SNAPSHOTS_DIR = PROJECT_ROOT / "wiki" / "memory" / "evolutions" / "yaml-snapshots"

# v6.13 (2026-05-31) L52 family 第 11 案: 用 BACKEND_DIR (動態 fallback)
# 取代寫死 PROJECT_ROOT/backend (container 內不存在)
SYNONYMS_YAML = BACKEND_DIR / "app" / "services" / "ai" / "synonyms.yaml"
INTENT_RULES_YAML = BACKEND_DIR / "app" / "services" / "ai" / "intent_rules.yaml"


@dataclass
class ApplyResult:
    ok: bool
    crystal_id: Optional[str] = None
    snapshot_path: Optional[Path] = None
    error: Optional[str] = None


class CrystalApplier:
    """批准 crystal proposal，安全改 yaml。"""

    def __init__(self):
        CRYSTALS_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async def apply_proposal(
        self,
        proposal_id: str,
        approved_by: str = "admin",
    ) -> ApplyResult:
        """批准並套用 proposal。安全閘全程守護。"""
        proposal_path = PROPOSALS_DIR / f"{proposal_id}.md"
        if not proposal_path.exists():
            return ApplyResult(ok=False, error=f"Proposal {proposal_id} 不存在")

        try:
            # Step 1: parse proposal
            meta, payload = self._parse_proposal(proposal_path)
            if not meta:
                return ApplyResult(ok=False, error="Proposal 解析失敗")

            if meta.get("status") != "pending":
                return ApplyResult(
                    ok=False,
                    error=f"Proposal 狀態為 {meta.get('status')}，無法 apply",
                )

            target_file = meta.get("target_file")
            target_path = self._resolve_target(target_file)
            if not target_path or not target_path.exists():
                return ApplyResult(ok=False, error=f"Target {target_file} 不存在")

            # Step 2: snapshot
            snapshot_path = self._snapshot(target_path)

            # Step 3: apply
            original = target_path.read_text(encoding="utf-8")
            new_yaml = self._build_new_yaml(original, meta, payload)
            if new_yaml == original:
                # No-op（已存在）
                return ApplyResult(
                    ok=False, error="Proposal 已套用或無變化", snapshot_path=snapshot_path,
                )

            # Step 4: validate (yaml 才驗，markdown 不必)
            # v6.13 (2026-05-31): SOUL.md soul_section apply 跳過 yaml validate
            if target_path.suffix.lower() in (".yaml", ".yml"):
                v = validate_yaml(new_yaml)
                if not v.ok:
                    logger.error("Yaml validation failed: %s", v.error)
                    return ApplyResult(
                        ok=False, error=f"YAML 驗證失敗: {v.error}", snapshot_path=snapshot_path,
                    )

            # Step 5: write new
            target_path.write_text(new_yaml, encoding="utf-8")

            # Step 6: record crystal
            crystal_id = self._write_crystal_record(
                proposal_id=proposal_id,
                target_file=target_file,
                snapshot_path=snapshot_path,
                approved_by=approved_by,
                meta=meta,
            )

            # Step 7: 標記 proposal 為 applied
            self._mark_proposal_status(proposal_path, "applied", extra={
                "applied_at": datetime.now(TZ_TAIPEI).isoformat(),
                "crystal_id": crystal_id,
                "approved_by": approved_by,
            })

            # Step 8: 清快取（讓 yaml reload）
            await self._invalidate_caches()

            logger.info(
                "Crystal applied: proposal=%s crystal=%s target=%s",
                proposal_id, crystal_id, target_file,
            )
            # Prometheus counter（best-effort）
            try:
                from app.core.memory_wiki_metrics import get_memory_wiki_metrics
                get_memory_wiki_metrics().crystal_applied.inc()
            except Exception:
                pass

            # Step 9: 通知 owner（v6.3 體感型輸出，ADR-0027 LINE 主通道）
            # best-effort，不阻擋主流程
            try:
                await self._notify_owner_growth(
                    crystal_id=crystal_id,
                    target_file=target_file,
                    meta=meta,
                )
            except Exception as e:
                logger.warning("Crystal growth notify failed (non-blocking): %s", e)

            return ApplyResult(
                ok=True, crystal_id=crystal_id, snapshot_path=snapshot_path,
            )

        except Exception as e:
            logger.error("Crystal apply failed: %s", e, exc_info=True)
            return ApplyResult(ok=False, error=str(e))

    # ────────── Helpers ──────────

    @staticmethod
    def _parse_proposal(path: Path) -> Tuple[Optional[Dict], Optional[Dict]]:
        """解析 proposal frontmatter 與 payload yaml 區塊。

        v6.13 (2026-05-31): 擴 meta keys (含 soul_section 所需 target_section)
        + 抓 markdown body 為 markdown_payload 給 soul_section apply 用
        """
        text = path.read_text(encoding="utf-8")
        fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not fm_match:
            return None, None
        fm = fm_match.group(1)

        meta: Dict = {}
        # v6.13: 加 target_section / proposed_at / reason / proposed_by 給 soul_section 用
        for key in ("proposal_kind", "target_file", "target_section",
                    "source_pattern", "status", "proposed_at", "proposed_by", "reason"):
            m = re.search(rf"^{key}:\s*(.+?)\s*$", fm, re.MULTILINE)
            if m:
                meta[key] = m.group(1).strip()

        # Payload 在 ```yaml ... ``` 區塊
        import yaml as pyyaml  # PyYAML 足夠解析結構
        payload_match = re.search(r"```yaml\s*\n(.*?)\n```", text, re.DOTALL)
        payload: Optional[Dict] = None
        if payload_match:
            try:
                payload = pyyaml.safe_load(payload_match.group(1))
            except Exception as e:
                logger.warning("Payload parse failed: %s", e)
                payload = None

        # v6.13: 對 soul_section 抓 "## 建議新內容" 區段 body 為 markdown payload
        # （proposal 用 markdown 區塊不是 yaml）
        if meta.get("proposal_kind") == "soul_section":
            body_match = re.search(
                r"##\s*建議新內容\s*\n+(.+?)(?:\n##\s|\n---\s*\n|\Z)",
                text, re.DOTALL,
            )
            if body_match:
                if payload is None:
                    payload = {}
                payload["markdown_body"] = body_match.group(1).strip()

        return meta, payload

    @staticmethod
    def _resolve_target(target_file: str) -> Optional[Path]:
        """target_file 對照實體路徑。

        v6.13 (2026-05-31): 加 wiki/SOUL.md mapping (soul_section apply)
        """
        mapping = {
            "synonyms.yaml": SYNONYMS_YAML,
            "intent_rules.yaml": INTENT_RULES_YAML,
            "wiki/SOUL.md": PROJECT_ROOT / "wiki" / "SOUL.md",
        }
        return mapping.get(target_file)

    @staticmethod
    def _snapshot(target_path: Path) -> Path:
        """複製一份備份。

        v6.13 (2026-05-31): markdown 用 .md.bak / yaml 用 .yaml.bak
        """
        timestamp = datetime.now(TZ_TAIPEI).strftime("%Y%m%d-%H%M%S")
        ext = target_path.suffix.lstrip(".")  # md or yaml
        backup = SNAPSHOTS_DIR / f"{target_path.stem}-{timestamp}.{ext}.bak"
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, backup)
        return backup

    @staticmethod
    def _build_new_yaml(
        original: str,
        meta: Dict,
        payload: Optional[Dict],
    ) -> str:
        """根據 proposal 類型套用差異。"""
        if not payload:
            return original

        kind = meta.get("proposal_kind")
        if kind == "synonym":
            category = payload.get("category", "agency_synonyms")
            new_group = payload.get("group", [])
            new_text, _changed = add_synonym_group(original, category, new_group)
            return new_text

        elif kind == "intent_rule":
            rule_block = payload.get("rule") or {}
            if not rule_block.get("name") or not rule_block.get("pattern"):
                # Phase 3 初版：若 pattern 為空（pattern_extractor 目前不生 pattern 欄位）
                # 跳過實際寫入，回 original（caller 會判斷 no-op）
                logger.info("Intent rule missing pattern, skipping apply (proposal awaits manual pattern)")
                return original
            new_text, _changed = add_intent_rule(original, rule_block)
            return new_text

        elif kind == "soul_section":
            # v6.13 (2026-05-31): SOUL.md section append handler
            # 對齊 owner 安全: append 不覆寫既有內容 + section anchor 精確 + ## 我學到的偏好 之前停
            target_section = meta.get("target_section", "").strip()
            markdown_body = (payload or {}).get("markdown_body", "").strip()
            if not target_section or not markdown_body:
                logger.info("soul_section missing target_section or body, skipping")
                return original

            # 找 section 開頭 "## <target_section>" 到下一個 "## " 或 EOF
            section_pattern = re.compile(
                rf"(^##\s*{re.escape(target_section)}\s*\n)(.*?)(\n##\s|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            m = section_pattern.search(original)
            if not m:
                logger.warning(f"soul section '{target_section}' not found in SOUL.md")
                return original

            # append markdown_body 到 section 末尾 (在下個 ## 之前)
            header = m.group(1)
            body = m.group(2)
            next_section = m.group(3)
            # 避免重複: 若 markdown_body 已在 body 中 (尤其是 proposed_at 字串對齊) 則 no-op
            body_marker = markdown_body[:80].strip()
            if body_marker and body_marker in body:
                logger.info("soul_section content already present, skipping")
                return original

            new_body = body.rstrip() + "\n\n" + markdown_body + "\n"
            new_section = header + new_body + next_section
            return original[:m.start()] + new_section + original[m.end():]

        else:
            logger.warning("Unknown proposal_kind: %s", kind)
            return original

    def _write_crystal_record(
        self,
        *,
        proposal_id: str,
        target_file: str,
        snapshot_path: Path,
        approved_by: str,
        meta: Dict,
    ) -> str:
        """寫 crystal 紀錄（audit trail）。"""
        crystal_id = f"crystal-{datetime.now(TZ_TAIPEI).strftime('%Y%m%d-%H%M%S')}"
        crystal_path = CRYSTALS_DIR / f"{crystal_id}.md"
        crystal_path.write_text(
            f"""---
type: agent_memory
memory_type: crystal
crystal_id: {crystal_id}
source_proposal: {proposal_id}
source_pattern: {meta.get('source_pattern', '-')}
target_file: {target_file}
snapshot: {snapshot_path.name}
approved_by: {approved_by}
approved_at: {datetime.now(TZ_TAIPEI).isoformat()}
tags: [memory, crystal, {target_file.replace('.yaml', '')}]
---

# Crystal {crystal_id}

成功套用 proposal `{proposal_id}` → 改動 `{target_file}`。

Snapshot 備份至：`{snapshot_path}`

若需回滾：`POST /api/ai/memory/crystals/rollback` with `crystal_id={crystal_id}`
""",
            encoding="utf-8",
        )
        return crystal_id

    @staticmethod
    def _mark_proposal_status(
        path: Path, new_status: str, extra: Optional[Dict] = None,
    ) -> None:
        """更新 proposal frontmatter 的 status 欄位。"""
        text = path.read_text(encoding="utf-8")
        # Replace status 行
        text = re.sub(
            r"^status:\s*\S+",
            f"status: {new_status}",
            text, count=1, flags=re.MULTILINE,
        )
        # 追加 extra 欄位（在 --- 之前）
        if extra:
            extra_lines = "\n".join(f"{k}: {v}" for k, v in extra.items())
            text = re.sub(
                r"(^---\s*\n.*?)(\n---\s*\n)",
                rf"\1\n{extra_lines}\2",
                text, count=1, flags=re.DOTALL,
            )
        path.write_text(text, encoding="utf-8")

    @staticmethod
    async def _invalidate_caches() -> None:
        """清除 AI config 快取讓 yaml 重讀。"""
        try:
            from app.services.ai.core.ai_config import get_ai_config
            # AIConfig 採 class-level state；清 synonyms/rules 欄位
            # 2026-07-17: 原 AIConfig.get_instance()（不存在→hasattr False→config=None→
            #   快取清除靜默失效）改 get_ai_config()（模組級 singleton，SSOT）。L79 silent 家族。
            config = get_ai_config()
            if config:
                for attr in ("_synonyms", "_intent_rules", "_synonyms_loaded"):
                    if hasattr(config, attr):
                        setattr(config, attr, None)
        except Exception as e:
            logger.debug("Cache invalidation partial: %s", e)

    @staticmethod
    async def _notify_owner_growth(
        *, crystal_id: str, target_file: str, meta: Dict,
    ) -> None:
        """v6.3 體感型輸出：crystal apply 成功時推一則 LINE 給 owner。

        設計（坤哥第一人稱）：
        - 標題：「🌱 我學到了一條新規則」
        - 來源 pattern + 影響檔 + 完整紀錄路徑
        - 不含 PII（crystal_id 是時間戳，無使用者資料）

        ADR-0027：LINE 為 owner 主推送通道（Telegram 個人號 4/21 封禁後）。
        ENV 控制：
        - LINE_ADMIN_USER_ID 未設定 → silent skip
        - LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉
        """
        import os
        if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
            return
        line_user_id = os.getenv("LINE_ADMIN_USER_ID")
        if not line_user_id:
            return

        kind = meta.get("proposal_kind", "rule")
        source_pattern = meta.get("source_pattern", "-")
        text = (
            f"🌱 我學到了一條新規則\n"
            f"\n"
            f"📚 {crystal_id}\n"
            f"🎯 影響：{target_file}（{kind}）\n"
            f"🔍 來源：{source_pattern}\n"
            f"\n"
            f"從現在起遇到類似情境，我會用這個新方式回應。\n"
            f"完整紀錄：wiki/memory/crystals/{crystal_id}.md"
        )

        try:
            from app.services.integration.line_bot import LineBotService
            line_bot = LineBotService()
            if not line_bot.enabled:
                return
            ok = await line_bot.push_message(line_user_id, text)
            if ok:
                logger.info("Crystal growth notify pushed: crystal=%s", crystal_id)
            else:
                logger.warning("Crystal growth notify push returned False: crystal=%s", crystal_id)
        except Exception as e:
            logger.error(
                "Crystal growth notify error (multi-channel 體感斷鏈): %s",
                e, exc_info=True,
            )

    async def rollback(self, crystal_id: str) -> ApplyResult:
        """回滾指定 crystal（從 snapshot 還原）。"""
        crystal_path = CRYSTALS_DIR / f"{crystal_id}.md"
        if not crystal_path.exists():
            return ApplyResult(ok=False, error=f"Crystal {crystal_id} 不存在")

        try:
            text = crystal_path.read_text(encoding="utf-8")
            target_m = re.search(r"^target_file:\s*(\S+)", text, re.MULTILINE)
            snap_m = re.search(r"^snapshot:\s*(\S+)", text, re.MULTILINE)
            if not target_m or not snap_m:
                return ApplyResult(ok=False, error="Crystal frontmatter 缺欄位")

            target_path = self._resolve_target(target_m.group(1))
            snap_path = SNAPSHOTS_DIR / snap_m.group(1)
            if not target_path or not snap_path.exists():
                return ApplyResult(ok=False, error="Target 或 snapshot 缺失")

            # 還原
            shutil.copy2(snap_path, target_path)

            # 記錄 rollback
            rollback_log = PROJECT_ROOT / "wiki" / "memory" / "evolutions" / "rollbacks.md"
            rollback_log.parent.mkdir(parents=True, exist_ok=True)
            with rollback_log.open("a", encoding="utf-8") as f:
                f.write(
                    f"- {datetime.now(TZ_TAIPEI).isoformat()}: "
                    f"rollback crystal={crystal_id} target={target_path.name}\n",
                )

            await self._invalidate_caches()
            logger.info("Crystal rollback OK: %s", crystal_id)

            # v6.6 Phase A3 5b：rollback 也推 LINE（體感「主動性 / self-correction」）
            try:
                await self._notify_owner_rollback(
                    crystal_id=crystal_id,
                    target_file=target_path.name,
                )
            except Exception as e:
                logger.warning("Rollback notify failed (non-blocking): %s", e)

            return ApplyResult(ok=True, crystal_id=crystal_id)

        except Exception as e:
            return ApplyResult(ok=False, error=str(e))

    @staticmethod
    async def _notify_owner_rollback(
        *, crystal_id: str, target_file: str,
    ) -> None:
        """v6.6 Phase A3 5b：crystal rollback 推 LINE owner。

        坤哥第一人稱訊息：「↩ 我撤回了一條規則」— 體感「self-correction / 主動性」。

        ENV 共用 v6.3 _notify_owner_growth 的 gate：
        - LINE_ADMIN_USER_ID 未設 → silent skip
        - LINE_GROWTH_NOTIFY_ENABLED=false → 顯式關閉
        """
        import os
        if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
            return
        line_user_id = os.getenv("LINE_ADMIN_USER_ID")
        if not line_user_id:
            return

        text = (
            f"↩ 我撤回了一條規則\n"
            f"\n"
            f"📚 {crystal_id}\n"
            f"🎯 還原：{target_file}（從 snapshot）\n"
            f"\n"
            f"這條規則之前學歪了或不再適合，我已從 snapshot 還原。\n"
            f"完整紀錄：wiki/memory/evolutions/rollbacks.md"
        )

        try:
            from app.services.integration.line_bot import LineBotService
            line_bot = LineBotService()
            if not line_bot.enabled:
                return
            ok = await line_bot.push_message(line_user_id, text)
            if ok:
                logger.info("Crystal rollback notify pushed: crystal=%s", crystal_id)
            else:
                logger.warning("Crystal rollback notify returned False: %s", crystal_id)
        except Exception as e:
            logger.error(
                "Crystal rollback notify error: %s",
                e, exc_info=True,
            )
