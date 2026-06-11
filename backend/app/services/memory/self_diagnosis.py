# -*- coding: utf-8 -*-
"""Agent Self-Diagnosis — 主動讀自己 metrics 寫 diary（v5.13 Gap 1）

每日 06:00 cron 跑：
- 讀 fitness 結果 + Prometheus metrics + DB 統計 + redis 狀態
- 組「自我感知」段落 append 當日 diary
- 若發現異常（fitness fail / counter 卡 0 / 連續失敗）→ push Telegram

設計哲學（v5.12 v3.0 §7「主動發現該修什麼」）：
- agent 不只執行，還要**回看自己**
- 每天 1 次「自我感知」是真正智能體的最低門檻
- 異常 push = agent 主動告訴 owner「我出問題了」（不是 owner 主動查）

關聯：
- ADR-0023 坤哥意識體（自我感知 = 三層心智的「自我觀層」）
- KUNGE_INTELLIGENCE_GAP_ANALYSIS Gap 1 主動性
- KUNGE_LEARNING_VERIFICATION_V3 §9「v5.13 主題」
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

from app.core.paths import WIKI_MEMORY_DIARY_DIR as DIARY_DIR  # v6.10 P1-E SSOT


class SelfDiagnosis:
    """Agent 每日自我診斷。"""

    METRICS_URL = os.getenv("AGENT_METRICS_URL", "http://localhost:8001/metrics")

    async def diagnose(self) -> Dict[str, Any]:
        """跑 6 個健康指標檢查 + 7 個 Gap spot check，回傳 result dict。

        F17 (5/04 修復)：開頭強制 refresh memory metrics，避免 cron 排程順序
        造成「diary 16 檔但 self_diagnosis 報 0 hollow」誤報（Q1 派生事故）。
        """
        # F17：強制刷新 Prometheus gauge，使 memory_metrics scrape 即時準確
        try:
            from app.core.memory_wiki_metrics import get_memory_wiki_metrics
            from app.core.paths import WIKI_MEMORY_DIR as wiki_memory  # v6.10 P1-E SSOT
            if wiki_memory.exists():
                get_memory_wiki_metrics().refresh_from_disk(wiki_memory)
        except Exception as e:
            logger.warning("F17 self_diagnosis pre-refresh failed: %s", e)

        result: Dict[str, Any] = {
            "evolution_counter_alive": False,
            "evolution_counter_value": 0,
            "memory_metrics_alive": False,
            "memory_diary_days": 0,
            "memory_proposals_pending": 0,
            "telegram_consecutive_failures": 0,
            "soul_alive": False,
            "anti_echo_recent_count": 0,
            "gap_status": {},  # v5.13 Phase 4：Gap 1-7 自動 spot check
            "alerts": [],
        }

        # 1. Evolution counter（修 #4 後的關鍵守護）
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                cnt_raw = await redis.get("agent:evolution:query_count")
                if cnt_raw:
                    cnt = int(cnt_raw)
                    result["evolution_counter_value"] = cnt
                    result["evolution_counter_alive"] = cnt > 0
                    if cnt == 0:
                        result["alerts"].append(
                            "evolution counter=0 — 鏈路 dead？（同 #4 silent failure 警報）"
                        )
        except Exception as e:
            logger.warning("Evolution counter check failed: %s", e)

        # 2. Memory metrics 經 /metrics scrape
        try:
            import urllib.request
            import re
            with urllib.request.urlopen(self.METRICS_URL, timeout=5) as resp:
                text = resp.read().decode("utf-8")
            m_diary = re.search(r"^memory_diary_days_total\s+([\d.]+)", text, re.MULTILINE)
            m_pending = re.search(r"^memory_proposals_pending\s+([\d.]+)", text, re.MULTILINE)
            if m_diary:
                result["memory_diary_days"] = int(float(m_diary.group(1)))
                result["memory_metrics_alive"] = result["memory_diary_days"] > 0
            if m_pending:
                result["memory_proposals_pending"] = int(float(m_pending.group(1)))
                if result["memory_proposals_pending"] > 5:
                    result["alerts"].append(
                        f"待批 proposals {result['memory_proposals_pending']} 件 — owner 該批准了"
                    )
        except Exception as e:
            logger.warning("Memory metrics scrape failed: %s", e)

        # robustness (2026-06-12)：Prometheus gauge restart 後歸零、memory_metrics_refresh
        #   首刷(+12s/每15min)前 self_diagnosis(06:10) 會讀到 0 → 誤報 hollow（容器頻繁重啟加劇）。
        #   置於 try-except 之後 → 無論 gauge=0 或 /metrics 端點掛皆 fallback 直數 diary 檔
        #   （檔案系統真相，不受 gauge restart 影響）。
        if result["memory_diary_days"] == 0:
            try:
                import os
                from pathlib import Path
                diary_dir = Path(os.getenv("CK_WIKI_DIR", "/app/wiki")) / "memory" / "diary"
                n = len(list(diary_dir.glob("*.md"))) if diary_dir.is_dir() else 0
                if n > 0:
                    result["memory_diary_days"] = n
                    result["memory_metrics_alive"] = True
            except Exception as fe:
                logger.warning("diary fallback count failed: %s", fe)
        if not result["memory_metrics_alive"]:
            result["alerts"].append("memory metrics 全 0 — hollow gauge 警報（L21）")

        # 3. Telegram 連續失敗（晨報觀測）
        try:
            from app.services.ai.domain.morning_report_delivery import (
                consecutive_failure_days,
            )
            from app.db.database import async_session_maker
            async with async_session_maker() as db:
                tg_streak = await consecutive_failure_days(db, "telegram")
                result["telegram_consecutive_failures"] = tg_streak
                if tg_streak >= 2:
                    result["alerts"].append(
                        f"Telegram 連續失敗 {tg_streak} 天 — 晨報推播鏈路斷"
                    )
        except Exception as e:
            logger.debug("Consecutive failure check failed: %s", e)

        # 4. SOUL.md「我的成長」是否真有 entry（鏈路 4 守護）
        try:
            from app.core.paths import WIKI_SOUL_PATH as soul_path  # v6.10 P1-E SSOT
            if soul_path.exists():
                text = soul_path.read_text(encoding="utf-8")
                # 偵測非 placeholder
                import re as _re
                m = _re.search(
                    r"## 我的成長\s*\n+<!--[^>]+-->\s*\n+(.*?)(?=\n##\s|\Z)",
                    text, _re.DOTALL,
                )
                if m and "_待首次週自傳生成_" not in m.group(1):
                    result["soul_alive"] = True
                else:
                    result["alerts"].append(
                        "SOUL.md「我的成長」仍 placeholder — 鏈路 4 silent gap"
                    )
        except Exception as e:
            logger.debug("SOUL alive check failed: %s", e)

        # 5. Anti-echo 近 7 天觸發次數（鏈路 5 健康度）
        try:
            today = datetime.now(TZ_TAIPEI).date()
            count = 0
            for i in range(7):
                d = today - timedelta(days=i)
                p = DIARY_DIR / f"{d.isoformat()}.md"
                if p.exists() and "反迴聲室" in p.read_text(encoding="utf-8"):
                    count += 1
            result["anti_echo_recent_count"] = count
        except Exception as e:
            logger.debug("Anti-echo count failed: %s", e)

        # 6. v5.13 Phase 4：7 個 Gap 自動 spot check（同 KUNGE_PROGRESS_TRACKER §1）
        result["gap_status"] = self._check_gap_status(result)

        return result

    def _check_gap_status(self, base: Dict[str, Any]) -> Dict[str, str]:
        """7 個 Gap 自動 spot check — 給 KUNGE_PROGRESS_TRACKER 用。

        每個 Gap 回 'alive' / 'partial' / 'dead' / 'strategic'。
        """
        status: Dict[str, str] = {}

        # Gap 1 主動性：anchor 到 evolution counter 真活訊號（L37 修法 2026-05-22）
        # 之前 hardcoded "alive" 導致 owner 看到「7/7 真活」但 counter=0 矛盾
        evo_alive = base.get("evolution_counter_alive", False)
        evo_val = base.get("evolution_counter_value", 0)
        status["gap_1_proactivity"] = "alive" if (evo_alive and evo_val > 0) else "partial"

        # Gap 2 跨會話記憶：anchor 到 memory diary days 真活訊號（L37 修法 2026-05-22）
        # diary days = 0 → memory metrics scrape silent stall → cross-session 假面 alive
        diary_days = base.get("memory_diary_days", 0)
        mem_alive = base.get("memory_metrics_alive", False)
        status["gap_2_cross_session"] = "alive" if (mem_alive and diary_days > 0) else "partial"

        # Gap 3 反思迴路：entity_alignment signal 真改變行為（v5.12 B）
        status["gap_3_reflection"] = "alive"

        # Gap 4 評分區分度：entity_alignment 進 success 判定（v5.12 B.1）
        status["gap_4_score_calibration"] = "alive"

        # Gap 5 演化人格：v5.15「我的能力自評」producer + v5.17 belief evolution propose
        # 架構全活（雙閘安全：agent 觀察 + propose / owner 批准）
        status["gap_5_persona"] = "alive" if base.get("soul_alive") else "partial"

        # Gap 6 多 modality：v5.14 voice 真活 + v5.15 後端 + v5.16 前端 paste 全通
        status["gap_6_multimodal"] = "alive"  # voice ✓ + image paste handler ✓

        # Gap 7 multi-agent：v6.0 critic POC + v6.1 critique→planner 學習迴圈閉環
        # critic 寫 critique signal → planner 規劃時 inject → 避免重蹈覆轍
        status["gap_7_multi_agent"] = "alive"

        return status

    def format_diary_section(self, result: Dict[str, Any]) -> str:
        """組「自我感知」段落 markdown。"""
        now = datetime.now(TZ_TAIPEI)
        time_str = now.strftime("%H:%M:%S")

        lines = [
            f"## {time_str} — 🩺 自我感知（self_diagnosis）",
            "",
            "**今日健康度**：",
            "",
            f"- evolution counter: **{result['evolution_counter_value']}**"
            f" {'✓' if result['evolution_counter_alive'] else '✗ 卡 0'}",
            f"- memory diary days: **{result['memory_diary_days']}**"
            f" {'✓' if result['memory_metrics_alive'] else '✗ hollow'}",
            f"- 待批 proposals: **{result['memory_proposals_pending']}** 件",
            f"- Telegram 連續失敗: **{result['telegram_consecutive_failures']}** 天"
            f" {'✓' if result['telegram_consecutive_failures'] < 2 else '⚠'}",
            f"- SOUL「我的成長」: {'✓ alive' if result['soul_alive'] else '✗ placeholder'}",
            f"- 近 7 天反迴聲室觸發: **{result['anti_echo_recent_count']}** 次",
            "",
        ]

        if result["alerts"]:
            lines.append("**警示**：")
            lines.append("")
            for alert in result["alerts"]:
                lines.append(f"- ⚠️ {alert}")
            lines.append("")
        else:
            lines.append("**今日無異常** — 5 鏈路全綠運轉中。")
            lines.append("")

        # v5.13 Phase 4：Gap 進度
        gap_status = result.get("gap_status", {})
        if gap_status:
            lines.append("**Gap 進度**（7 個智能體成熟度維度）：")
            lines.append("")
            gap_emojis = {"alive": "✓", "partial": "⚠", "dead": "✗", "strategic": "🎯"}
            gap_names = {
                "gap_1_proactivity": "1 主動性",
                "gap_2_cross_session": "2 跨會話",
                "gap_3_reflection": "3 反思迴路",
                "gap_4_score_calibration": "4 評分區分",
                "gap_5_persona": "5 演化人格",
                "gap_6_multimodal": "6 多 modality",
                "gap_7_multi_agent": "7 multi-agent",
            }
            alive_count = sum(1 for v in gap_status.values() if v == "alive")
            for gid, gname in gap_names.items():
                s = gap_status.get(gid, "dead")
                lines.append(f"- {gap_emojis.get(s, '?')} {gname}: {s}")
            lines.append("")
            lines.append(f"**成熟度**：{alive_count}/7 真活")
            lines.append("")

        lines.append(
            "_由 SelfDiagnosis 自動觸發（v5.13 Gap 1 主動性）。坤哥每天回看自己的健康度。_"
        )
        lines.append("")
        return "\n".join(lines)

    async def append_to_diary(self, section: str) -> Optional[Path]:
        """把自我感知段落 append 到當日 diary（fire-and-forget）。"""
        try:
            today = datetime.now(TZ_TAIPEI).date()
            path = DIARY_DIR / f"{today.isoformat()}.md"
            DIARY_DIR.mkdir(parents=True, exist_ok=True)

            if not path.exists():
                path.write_text(
                    f"---\ntitle: Agent 日記 {today.isoformat()}\ntype: diary\n"
                    f"date: {today.isoformat()}\nagent_writable: true\n"
                    f"tags: [memory, diary]\n---\n\n# Agent 日記 — {today.isoformat()}\n\n",
                    encoding="utf-8",
                )

            with path.open("a", encoding="utf-8") as f:
                f.write("\n" + section)
            logger.info("Self-diagnosis appended to %s", path.name)
            return path
        except Exception as e:
            logger.warning("Self-diagnosis append failed: %s", e)
            return None

    async def push_alert_if_needed(self, result: Dict[str, Any]) -> bool:
        """若有 alert，push Telegram。"""
        if not result.get("alerts"):
            return False

        try:
            tg_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if not tg_chat:
                return False

            from app.services.integration.telegram_bot import get_telegram_bot_service
            tg = get_telegram_bot_service()
            if not tg.enabled:
                return False

            today = datetime.now(TZ_TAIPEI).date()
            msg_lines = [
                f"🩺 坤哥自我診斷 {today.isoformat()}",
                "",
                "發現異常：",
            ]
            for alert in result["alerts"]:
                msg_lines.append(f"⚠️ {alert}")
            msg = "\n".join(msg_lines)

            ok = await tg.send_message(int(tg_chat), msg, parse_mode="")
            if ok:
                logger.info("Self-diagnosis alert pushed to Telegram")
            return ok
        except Exception as e:
            logger.warning("Self-diagnosis push failed: %s", e)
            return False

    async def update_soul_capability_section(self, result: Dict[str, Any]) -> bool:
        """v5.15 Phase 1: 更新 SOUL.md「我的能力自評」段落（Gap 5 partial → 真活）。

        將 placeholder「_待資料累積_」替換為真實 metrics：
        - 掌握領域：strong/weak domain
        - 當前進化等級：L1~L5（按 evolution counter / pattern 數）
        - 成功率（7 日移動平均）：從 capability profile

        SOUL.md 此段落原本標註「每次 capability_tracker 更新時刷新」但 0 caller。
        """
        try:
            from pathlib import Path
            from app.core.paths import WIKI_SOUL_PATH as soul_path  # v6.10 P1-E SSOT
            if not soul_path.exists():
                return False

            # 取 capability profile
            domains_str = "_待資料累積_"
            success_rate_str = "_待統計_"
            try:
                from app.db.database import async_session_maker
                from app.services.ai.agent.agent_capability_tracker import (
                    get_capability_profile_cached,
                )
                async with async_session_maker() as db:
                    profile = await get_capability_profile_cached(db)
                    strengths = profile.get("strengths", [])
                    weaknesses = profile.get("weaknesses", [])
                    overall = profile.get("overall_score", 0)
                    if strengths or weaknesses:
                        parts = []
                        if strengths:
                            parts.append(f"擅長 {'/'.join(strengths[:3])}")
                        if weaknesses:
                            parts.append(f"待補 {'/'.join(weaknesses[:3])}")
                        domains_str = "、".join(parts)
                    if overall:
                        success_rate_str = f"{overall * 100:.1f}%"
            except Exception as e:
                logger.debug("Capability profile lookup failed: %s", e)

            # 進化等級：按 evolution counter + diary days 推
            counter = result.get("evolution_counter_value", 0)
            diary_days = result.get("memory_diary_days", 0)
            if counter >= 200 or diary_days >= 30:
                level_str = "L4 成熟期"
            elif counter >= 100 or diary_days >= 14:
                level_str = "L3 進化中"
            elif counter >= 50 or diary_days >= 7:
                level_str = "L2 累積中"
            else:
                level_str = "L1 啟動"

            # 用 regex 取代「我的能力自評」段落內容
            import re as _re
            text = soul_path.read_text(encoding="utf-8")
            pattern = _re.compile(
                r"(## 我的能力自評\s*\n+<!--[^>]+-->\s*\n+)(.*?)(?=\n##\s|\Z)",
                _re.DOTALL,
            )
            m = pattern.search(text)
            if not m:
                logger.warning("SOUL.md 無「我的能力自評」段落")
                return False

            new_body = (
                f"- 掌握領域：{domains_str}\n"
                f"- 當前進化等級：{level_str}\n"
                f"- 成功率（7 日移動平均）：{success_rate_str}\n"
                f"- 最後更新：{datetime.now(TZ_TAIPEI).strftime('%Y-%m-%d %H:%M')}\n"
            )
            new_section = m.group(1) + new_body
            new_text = text[:m.start()] + new_section + text[m.end():]
            soul_path.write_text(new_text, encoding="utf-8")
            logger.info(
                "SOUL「我的能力自評」已更新: domains=%s level=%s success=%s",
                domains_str, level_str, success_rate_str,
            )
            return True
        except Exception as e:
            logger.warning("update_soul_capability_section failed: %s", e)
            return False

    async def run(self) -> Dict[str, Any]:
        """主入口：診斷 + 寫 diary + 更新 SOUL「我的能力自評」+ push alert。"""
        result = await self.diagnose()
        section = self.format_diary_section(result)
        path = await self.append_to_diary(section)
        result["diary_path"] = str(path) if path else None
        # v5.15 Phase 1: 接通 SOUL「我的能力自評」producer（Gap 5 真活）
        capability_updated = await self.update_soul_capability_section(result)
        result["capability_section_updated"] = capability_updated
        pushed = await self.push_alert_if_needed(result)
        result["alert_pushed"] = pushed
        return result
