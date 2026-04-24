# -*- coding: utf-8 -*-
"""Anti-Echo Chamber Protocol — 反迴聲室協議

2026-04-21 v5.8.0 坤哥意識體 D5-A。

核心信念（SOUL.md v2.0）：
- 「我最危險的傾向是永遠同意主事者」
- 每 N 次連續同意後，強制提出反方觀點或盲區警示
- 決策前必先列 1-2 個風險或替代方案

職責：
- 掃最近 7 天 diary + agent_query_traces
- 若偵測到「過度一致」（高成功率/低 failure/無反思條目）
  → 在當日 diary append「反迴聲室」段落，列 1-3 條質疑候選
- 不動用 LLM（v1 模板生成，deterministic 可測試）
- 失敗只 log 不 raise（append-only 精神）

Usage:
    from app.services.memory.anti_echo import AntiEchoProtocol
    protocol = AntiEchoProtocol()
    triggered = await protocol.scan_and_reflect()
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

DIARY_DIR = Path(__file__).resolve().parents[4] / "wiki" / "memory" / "diary"

# 觸發門檻（可透過環境變數覆寫）
DEFAULT_SCAN_DAYS = 7
DEFAULT_MIN_ENTRIES = 20        # 至少 20 筆才有統計意義
DEFAULT_SUCCESS_THRESHOLD = 0.90  # 成功率 > 90% 視為過度一致
DEFAULT_FAILURE_MAX = 2          # failure 筆數 ≤ 2
DEFAULT_COOLDOWN_DAYS = 3        # 3 天內已觸發過就不重複


class AntiEchoProtocol:
    """反迴聲室協議執行器。"""

    def __init__(
        self,
        scan_days: int = DEFAULT_SCAN_DAYS,
        min_entries: int = DEFAULT_MIN_ENTRIES,
        success_threshold: float = DEFAULT_SUCCESS_THRESHOLD,
        failure_max: int = DEFAULT_FAILURE_MAX,
        cooldown_days: int = DEFAULT_COOLDOWN_DAYS,
    ):
        self.scan_days = scan_days
        self.min_entries = min_entries
        self.success_threshold = success_threshold
        self.failure_max = failure_max
        self.cooldown_days = cooldown_days

    async def scan_and_reflect(self) -> Dict[str, Any]:
        """主入口 — 掃近 N 天 diary 決定是否觸發反迴聲室。

        Returns:
            {
              "triggered": bool,
              "reason": str,
              "stats": {...},
              "reflections": [str, ...],  # 若觸發，輸出候選
              "appended_path": str | None,
            }
        """
        result: Dict[str, Any] = {
            "triggered": False,
            "reason": "",
            "stats": {},
            "reflections": [],
            "appended_path": None,
        }

        try:
            # 1. 掃 diary
            today = datetime.now(TZ_TAIPEI).date()
            entries = self._collect_entries(today)
            stats = self._aggregate_stats(entries)
            result["stats"] = stats

            # 2. 檢 cooldown
            if self._in_cooldown(today):
                result["reason"] = f"cooldown 內（{self.cooldown_days} 天）"
                return result

            # 3. 檢觸發條件
            if stats["total"] < self.min_entries:
                result["reason"] = (
                    f"entries {stats['total']} < {self.min_entries} 不足統計意義"
                )
                return result

            success_rate = (
                stats["success"] / stats["total"] if stats["total"] else 0.0
            )
            if success_rate < self.success_threshold:
                result["reason"] = (
                    f"success_rate {success_rate:.2f} < {self.success_threshold}"
                )
                return result

            if stats["failure"] > self.failure_max:
                result["reason"] = (
                    f"failure {stats['failure']} > {self.failure_max}（有異議跡象）"
                )
                return result

            # 4. 觸發 — 生成反思候選並 append
            reflections = self._generate_reflections(stats)
            appended_path = self._append_to_today_diary(today, stats, reflections)

            result.update({
                "triggered": True,
                "reason": (
                    f"過度一致（success_rate={success_rate:.2%}, "
                    f"total={stats['total']}, failure={stats['failure']}）"
                ),
                "reflections": reflections,
                "appended_path": str(appended_path) if appended_path else None,
            })
            logger.info(
                "AntiEcho triggered: success_rate=%.2f total=%d reflections=%d",
                success_rate, stats["total"], len(reflections),
            )
        except Exception as e:
            logger.warning("AntiEcho scan failed: %s", e, exc_info=True)
            result["reason"] = f"exception: {e}"

        return result

    # ────────── Helpers ──────────

    def _collect_entries(self, today) -> List[Dict[str, Any]]:
        """讀近 scan_days 天 diary 所有 entry。"""
        entries: List[Dict[str, Any]] = []
        for i in range(self.scan_days):
            d = today - timedelta(days=i)
            path = DIARY_DIR / f"{d.isoformat()}.md"
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
                # Parse entries by "## HH:MM:SS" headers
                for m in re.finditer(
                    r"^## (\d{2}:\d{2}:\d{2}) — (✅|❌) \[([^\]]+)\]",
                    text,
                    re.MULTILINE,
                ):
                    entries.append({
                        "date": d.isoformat(),
                        "time": m.group(1),
                        "success": m.group(2) == "✅",
                        "route_type": m.group(3),
                    })
            except Exception:
                continue
        return entries

    def _aggregate_stats(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(entries)
        success = sum(1 for e in entries if e["success"])
        failure = total - success
        routes: Dict[str, int] = {}
        for e in entries:
            r = e.get("route_type", "unknown")
            routes[r] = routes.get(r, 0) + 1
        # Top route
        top_route = max(routes.items(), key=lambda x: x[1])[0] if routes else "unknown"
        return {
            "total": total,
            "success": success,
            "failure": failure,
            "routes": routes,
            "top_route": top_route,
            "scan_days": self.scan_days,
        }

    def _in_cooldown(self, today) -> bool:
        """掃近 cooldown_days 天 diary 是否已出現反迴聲室段落。"""
        for i in range(self.cooldown_days):
            d = today - timedelta(days=i)
            path = DIARY_DIR / f"{d.isoformat()}.md"
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8")
                if "反迴聲室" in text or "anti_echo" in text:
                    return True
            except Exception:
                continue
        return False

    def _generate_reflections(self, stats: Dict[str, Any]) -> List[str]:
        """模板生成 1-3 條反思候選（v1 無 LLM，deterministic）。"""
        top_route = stats.get("top_route", "query")
        total = stats.get("total", 0)
        success = stats.get("success", 0)
        rate = (success / total * 100) if total else 0

        return [
            (
                f"過去 {self.scan_days} 天你最常讓我跑 `{top_route}` 類查詢"
                f"（{stats.get('routes', {}).get(top_route, 0)} 筆）— "
                f"如果這個查詢方向本身有盲點呢？試問：最近有沒有你「沒問」但其實該問的事？"
            ),
            (
                f"我連續同意了 {success} 次（成功率 {rate:.0f}%）— "
                f"是我看太少，還是你這週真的判斷都對？至少挑一個決定回來覆盤，確認不是迴聲效應。"
            ),
            (
                "有沒有你最近覺得「自己處理就好，不用問坤哥」的事？"
                "那些往往才是真正值得一起討論的 — 因為你對我產生了選擇性信任。"
            ),
        ]

    def _append_to_today_diary(
        self, today, stats: Dict[str, Any], reflections: List[str]
    ) -> Optional[Path]:
        """把反迴聲室段落 append 到當日 diary。"""
        try:
            path = DIARY_DIR / f"{today.isoformat()}.md"
            # 若尚無當日檔，不建 header（由 DiaryService.ensure_today_header 負責）
            if not path.exists():
                # 手動建最小 header 不阻塞
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f"---\ntitle: Agent 日記 {today.isoformat()}\ntype: diary\n"
                    f"date: {today.isoformat()}\ntags: [memory, diary]\n---\n\n"
                    f"# Agent 日記 — {today.isoformat()}\n\n",
                    encoding="utf-8",
                )

            now = datetime.now(TZ_TAIPEI)
            block = (
                f"\n## {now.strftime('%H:%M:%S')} — 🔔 反迴聲室（anti_echo）\n\n"
                f"**觸發**：過去 {stats['scan_days']} 天 {stats['total']} 筆查詢，"
                f"{stats['success']} 成功 / {stats['failure']} 失敗 — 超過連續同意門檻\n\n"
                f"**我可能錯了的地方（候選）**：\n\n"
            )
            for i, r in enumerate(reflections, 1):
                block += f"{i}. {r}\n\n"
            block += (
                "_由 AntiEchoProtocol 自動觸發（SOUL.md v2.0 反迴聲室協議）。"
                "坤哥將在下次對話主動提出其中一個問題。_\n"
            )

            with path.open("a", encoding="utf-8") as f:
                f.write(block)
            logger.info("AntiEcho block appended to %s", path.name)
            return path
        except Exception as e:
            logger.warning("AntiEcho append failed: %s", e)
            return None
