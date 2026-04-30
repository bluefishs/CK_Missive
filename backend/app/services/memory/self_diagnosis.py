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

DIARY_DIR = Path(__file__).resolve().parents[4] / "wiki" / "memory" / "diary"


class SelfDiagnosis:
    """Agent 每日自我診斷。"""

    METRICS_URL = os.getenv("AGENT_METRICS_URL", "http://localhost:8001/metrics")

    async def diagnose(self) -> Dict[str, Any]:
        """跑 6 個健康指標檢查，回傳 result dict。"""
        result: Dict[str, Any] = {
            "evolution_counter_alive": False,
            "evolution_counter_value": 0,
            "memory_metrics_alive": False,
            "memory_diary_days": 0,
            "memory_proposals_pending": 0,
            "telegram_consecutive_failures": 0,
            "soul_alive": False,
            "anti_echo_recent_count": 0,
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
            if not result["memory_metrics_alive"]:
                result["alerts"].append("memory metrics 全 0 — hollow gauge 警報（L21）")
        except Exception as e:
            logger.warning("Memory metrics scrape failed: %s", e)

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
            soul_path = Path(__file__).resolve().parents[4] / "wiki" / "SOUL.md"
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

        return result

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

    async def run(self) -> Dict[str, Any]:
        """主入口：診斷 + 寫 diary + push alert。"""
        result = await self.diagnose()
        section = self.format_diary_section(result)
        path = await self.append_to_diary(section)
        result["diary_path"] = str(path) if path else None
        pushed = await self.push_alert_if_needed(result)
        result["alert_pushed"] = pushed
        return result
