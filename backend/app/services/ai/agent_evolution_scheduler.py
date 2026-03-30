"""
Agent Evolution Scheduler — 自動自省 + 自我改善

這是讓乾坤智能體「不需要人安排就能自行進化」的核心模組。

機制:
1. 每 N 次查詢自動觸發自省（不需等人啟動）
2. 分析最近的低分信號 → 找出共同失敗模式
3. 自動執行修正動作：
   - 升級高頻成功模式為永久種子
   - 降低經常失敗的模式信心
   - 調整路由閾值（自適應）
   - 清理過期/低效學習

進化閉環:
    SelfEvaluator.signals → Redis Queue
                              ↓
    EvolutionScheduler.evolve() ← 每 50 次查詢 / 每日觸發
                              ↓
    修正動作: 升級種子 / 降級模式 / 調整閾值 / 清理
                              ↓
    下次查詢自動受益（零人工介入）

Version: 1.0.0
Created: 2026-03-16
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Redis keys
SIGNAL_QUEUE_KEY = "agent:evolution:signals"
EVAL_HISTORY_KEY = "agent:evolution:eval_history"
EVOLUTION_STATE_KEY = "agent:evolution:state"
QUERY_COUNTER_KEY = "agent:evolution:query_count"
LAST_EVOLUTION_KEY = "agent:evolution:last_run"


class AgentEvolutionScheduler:
    """
    定期消費 SelfEvaluator 的改進信號，自動執行修正。

    觸發方式（任一條件滿足）:
    1. 查詢計數器達到 EVOLVE_EVERY_N_QUERIES (預設 50)
    2. 距離上次進化超過 EVOLVE_INTERVAL_SECONDS (預設 24h)

    不需要 cron/scheduler — 在每次查詢結束時檢查，非阻塞執行。
    """

    def __init__(self, redis: Any = None):
        self.redis = redis
        # EVO-4: 從 agent-policy.yaml 讀取閾值，fallback 硬編碼預設值
        try:
            from app.services.ai.ai_config import AIConfig
            cfg = AIConfig.get_instance()
            self.EVOLVE_EVERY_N_QUERIES = getattr(cfg, 'evolution_trigger_every_n_queries', 50)
            self.EVOLVE_INTERVAL_SECONDS = getattr(cfg, 'evolution_trigger_interval_hours', 24) * 3600
            self.SEED_PROMOTE_MIN_HITS = getattr(cfg, 'evolution_promote_min_hits', 15)
            self.SEED_PROMOTE_MIN_SUCCESS = getattr(cfg, 'evolution_promote_min_success', 0.90)
            self.PATTERN_DEMOTE_MAX_SUCCESS = getattr(cfg, 'evolution_demote_max_success', 0.30)
            self.SIGNAL_BATCH_SIZE = getattr(cfg, 'evolution_signal_batch_size', 100)
        except Exception:
            self.EVOLVE_EVERY_N_QUERIES = 50
            self.EVOLVE_INTERVAL_SECONDS = 86400
            self.SEED_PROMOTE_MIN_HITS = 15
            self.SEED_PROMOTE_MIN_SUCCESS = 0.90
            self.PATTERN_DEMOTE_MAX_SUCCESS = 0.30
            self.SIGNAL_BATCH_SIZE = 100

    async def should_evolve(self) -> bool:
        """檢查是否應該觸發進化（每次查詢結束時呼叫）"""
        if not self.redis:
            return False

        try:
            # 遞增查詢計數
            count = await self.redis.incr(QUERY_COUNTER_KEY)

            # 條件 1: 每 N 次查詢
            if count % self.EVOLVE_EVERY_N_QUERIES == 0:
                return True

            # 條件 2: 時間間隔
            last_run = await self.redis.get(LAST_EVOLUTION_KEY)
            if last_run:
                elapsed = time.time() - float(last_run)
                if elapsed >= self.EVOLVE_INTERVAL_SECONDS:
                    return True
            elif count > 10:
                # 從未執行過，且已有足夠資料
                return True

            return False
        except Exception:
            return False

    async def evolve(self) -> Dict[str, Any]:
        """
        執行自動進化。非阻塞，在背景執行。

        Returns:
            進化報告 dict
        """
        if not self.redis:
            return {"status": "skip", "reason": "no_redis"}

        report: Dict[str, Any] = {
            "timestamp": time.time(),
            "actions": [],
            "signals_consumed": 0,
        }
        actions_taken: list = []

        try:
            # 1. 消費改進信號
            signals = await self._consume_signals()
            report["signals_consumed"] = len(signals)

            # 2. 分析信號，找出共同失敗模式
            failure_patterns = self._analyze_failure_patterns(signals)
            report["failure_patterns"] = failure_patterns

            # 3. 自動升級高頻成功模式為種子
            promoted = await self._promote_top_patterns()
            if promoted:
                report["actions"].append({
                    "type": "seed_promotion",
                    "count": len(promoted),
                    "patterns": promoted,
                })
                actions_taken.append({"type": "promote", "count": len(promoted)})

            # 4. 降級持續失敗的模式
            demoted = await self._demote_failing_patterns()
            if demoted:
                report["actions"].append({
                    "type": "pattern_demotion",
                    "count": len(demoted),
                    "patterns": demoted,
                })
                actions_taken.append({"type": "demote", "count": len(demoted)})

            # 5. 計算品質趨勢
            trend = await self._compute_quality_trend()
            report["quality_trend"] = trend

            # 6. 清理過期學習
            cleaned = await self._cleanup_stale_learnings()
            if cleaned:
                report["actions"].append({
                    "type": "cleanup",
                    "removed": cleaned,
                })
                actions_taken.append({"type": "cleanup", "count": cleaned})

            # 記錄進化時間
            await self.redis.set(LAST_EVOLUTION_KEY, str(time.time()))

            # 儲存進化報告
            await self.redis.set(
                EVOLUTION_STATE_KEY,
                json.dumps(report, ensure_ascii=False, default=str),
            )
            await self.redis.expire(EVOLUTION_STATE_KEY, 7 * 86400)  # 7 天

            total_actions = sum(
                a.get("count", 0) for a in report["actions"]
            )
            logger.info(
                "Evolution completed: %d signals consumed, %d actions taken, "
                "trend=%.3f",
                report["signals_consumed"], total_actions,
                trend.get("slope", 0) if trend else 0,
            )

            # 進化日誌：記錄本次進化
            try:
                query_count_raw = await self.redis.get(QUERY_COUNTER_KEY)
                query_count = int(query_count_raw) if query_count_raw else 0
                journal_entry = json.dumps({
                    "timestamp": time.time(),
                    "triggered_by": "query_count" if query_count >= self.EVOLVE_EVERY_N_QUERIES else "time_interval",
                    "actions": actions_taken,
                    "signals_processed": len(signals),
                }, ensure_ascii=False)
                await self.redis.lpush("agent:evolution:journal", journal_entry)
                await self.redis.ltrim("agent:evolution:journal", 0, 99)  # Keep last 100
            except Exception:
                pass

            # Phase 2D: LLM 生成進化摘要（非阻塞）
            if actions_taken or report.get("signals_consumed", 0) > 0:
                try:
                    summary = await self._generate_evolution_summary(report)
                    if summary:
                        await self.redis.set(
                            "agent:evolution:latest_summary",
                            json.dumps({"summary": summary, "timestamp": time.time()}, ensure_ascii=False),
                        )
                        await self.redis.expire("agent:evolution:latest_summary", 7 * 86400)
                        # Phase 2F: 推送進化報告到 LINE/Discord（非阻塞）
                        await self._push_evolution_report(summary, report)
                except Exception as sum_err:
                    logger.debug("Evolution summary generation skipped: %s", sum_err)

        except Exception as e:
            logger.warning("Evolution failed (non-critical): %s", e)
            report["error"] = str(e)

        return report

    # ─── 進化動作 ──────────────────────────────────────

    async def _consume_signals(self) -> List[Dict[str, Any]]:
        """從 Redis 消費改進信號"""
        signals = []
        for _ in range(self.SIGNAL_BATCH_SIZE):
            raw = await self.redis.rpop(SIGNAL_QUEUE_KEY)
            if not raw:
                break
            try:
                signals.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return signals

    # Severity priority for sorting (lower number = higher priority)
    SEVERITY_PRIORITY = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    def _analyze_failure_patterns(
        self, signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """分析信號中的共同失敗模式（按嚴重度優先排序）"""
        type_counts: Dict[str, int] = {}
        type_examples: Dict[str, List[str]] = {}
        type_max_severity: Dict[str, str] = {}

        for sig in signals:
            sig_type = sig.get("type", "unknown")
            type_counts[sig_type] = type_counts.get(sig_type, 0) + 1
            if sig_type not in type_examples:
                type_examples[sig_type] = []
            if len(type_examples[sig_type]) < 3:
                type_examples[sig_type].append(
                    sig.get("question_preview", "")[:50]
                )
            # Track highest severity seen for this type
            sig_severity = sig.get("severity", "medium")
            existing = type_max_severity.get(sig_type, "low")
            if self.SEVERITY_PRIORITY.get(sig_severity, 3) < self.SEVERITY_PRIORITY.get(existing, 3):
                type_max_severity[sig_type] = sig_severity

        patterns = []
        for sig_type, count in type_counts.items():
            if count >= 3:  # 至少出現 3 次才視為模式
                patterns.append({
                    "type": sig_type,
                    "count": count,
                    "severity": type_max_severity.get(sig_type, "medium"),
                    "examples": type_examples.get(sig_type, []),
                })

        # Sort by severity priority (critical first), then by count descending
        patterns.sort(key=lambda p: (
            self.SEVERITY_PRIORITY.get(p.get("severity", "medium"), 3),
            -p["count"],
        ))

        return patterns

    async def _promote_top_patterns(self) -> List[str]:
        """將高頻成功模式升級為永久種子"""
        promoted = []
        try:
            index_key = "agent:patterns:index"
            # 取得分數最高的 10 個模式
            top = await self.redis.zrevrange(index_key, 0, 9, withscores=True)
            if not top:
                return promoted

            for pattern_key, _score in top:
                if isinstance(pattern_key, bytes):
                    pattern_key = pattern_key.decode()
                detail_key = f"agent:patterns:detail:{pattern_key}"
                detail = await self.redis.hgetall(detail_key)
                if not detail:
                    continue

                hit_count = int(detail.get(b"hit_count", detail.get("hit_count", 0)))
                success_str = detail.get(b"success_rate", detail.get("success_rate", "0"))
                success_rate = float(success_str)

                if (hit_count >= self.SEED_PROMOTE_MIN_HITS
                        and success_rate >= self.SEED_PROMOTE_MIN_SUCCESS):
                    # 標記為永久種子（移除 TTL）
                    await self.redis.persist(detail_key)
                    template = detail.get(b"template", detail.get("template", b""))
                    if isinstance(template, bytes):
                        template = template.decode()
                    promoted.append(template[:50])
                    logger.info(
                        "Pattern PROMOTED to seed: hits=%d rate=%.2f template=%s",
                        hit_count, success_rate, template[:50],
                    )

        except Exception as e:
            logger.debug("Promote failed: %s", e)

        return promoted

    async def _demote_failing_patterns(self) -> List[str]:
        """降級持續失敗的模式"""
        demoted = []
        try:
            index_key = "agent:patterns:index"
            # 取得分數最低的 10 個模式
            bottom = await self.redis.zrange(index_key, 0, 9, withscores=True)
            if not bottom:
                return demoted

            for pattern_key, _score in bottom:
                if isinstance(pattern_key, bytes):
                    pattern_key = pattern_key.decode()
                detail_key = f"agent:patterns:detail:{pattern_key}"
                detail = await self.redis.hgetall(detail_key)
                if not detail:
                    continue

                hit_count = int(detail.get(b"hit_count", detail.get("hit_count", 0)))
                success_str = detail.get(b"success_rate", detail.get("success_rate", "1"))
                success_rate = float(success_str)

                if (hit_count >= 5
                        and success_rate <= self.PATTERN_DEMOTE_MAX_SUCCESS):
                    # 移除失敗模式
                    await self.redis.zrem(index_key, pattern_key)
                    await self.redis.delete(detail_key)
                    demoted.append(pattern_key)
                    logger.info(
                        "Pattern DEMOTED: hits=%d rate=%.2f key=%s",
                        hit_count, success_rate, pattern_key,
                    )

        except Exception as e:
            logger.debug("Demote failed: %s", e)

        return demoted

    async def _compute_quality_trend(self) -> Dict[str, Any]:
        """計算品質趨勢（最近 100 次評分的移動平均）"""
        try:
            raw_list = await self.redis.lrange(EVAL_HISTORY_KEY, 0, 99)
            if not raw_list or len(raw_list) < 5:
                return {"status": "insufficient_data", "count": len(raw_list or [])}

            scores = []
            for raw in raw_list:
                try:
                    record = json.loads(raw)
                    scores.append(record.get("overall", 0))
                except (json.JSONDecodeError, TypeError):
                    continue

            if len(scores) < 5:
                return {"status": "insufficient_data", "count": len(scores)}

            # 簡易線性趨勢: 比較前半和後半的平均值
            mid = len(scores) // 2
            recent_avg = sum(scores[:mid]) / mid  # 最近（list head = newest）
            older_avg = sum(scores[mid:]) / (len(scores) - mid)
            slope = recent_avg - older_avg  # 正數 = 改善中

            return {
                "status": "ok",
                "count": len(scores),
                "recent_avg": round(recent_avg, 3),
                "older_avg": round(older_avg, 3),
                "slope": round(slope, 3),
                "direction": "improving" if slope > 0.02 else (
                    "declining" if slope < -0.02 else "stable"
                ),
            }
        except Exception:
            return {"status": "error"}

    async def _cleanup_stale_learnings(self) -> int:
        """清理過期學習（超過 30 天未命中的模式）"""
        cleaned = 0
        try:
            index_key = "agent:patterns:index"
            all_keys = await self.redis.zrangebyscore(
                index_key, "-inf", "+inf", withscores=True
            )
            if not all_keys:
                return 0

            now = time.time()
            for pattern_key, score in all_keys:
                if isinstance(pattern_key, bytes):
                    pattern_key = pattern_key.decode()
                # 分數太低（衰減後接近 0）= 長期未使用
                if score < 0.01:
                    detail_key = f"agent:patterns:detail:{pattern_key}"
                    await self.redis.zrem(index_key, pattern_key)
                    await self.redis.delete(detail_key)
                    cleaned += 1

            if cleaned:
                logger.info("Cleaned %d stale patterns", cleaned)

        except Exception as e:
            logger.debug("Cleanup failed: %s", e)

        return cleaned

    async def _push_evolution_report(self, summary: str, report: Dict[str, Any]) -> None:
        """推送進化報告到已配置的通道 (LINE/Discord)"""
        import os
        try:
            push_targets = os.getenv("EVOLUTION_PUSH_LINE_USERS", "").strip()
            discord_channels = os.getenv("EVOLUTION_PUSH_DISCORD_CHANNELS", "").strip()

            if not push_targets and not discord_channels:
                return  # 未配置推送目標

            actions_count = sum(a.get("count", 0) for a in report.get("actions", []))
            signals = report.get("signals_consumed", 0)
            message = (
                f"🧠 乾坤智能體進化報告\n\n"
                f"{summary}\n\n"
                f"📊 信號: {signals} | 動作: {actions_count}"
            )

            from app.services.notification_dispatcher import NotificationDispatcher
            dispatcher = NotificationDispatcher()
            line_ids = [uid.strip() for uid in push_targets.split(",") if uid.strip()] if push_targets else None
            discord_ids = [cid.strip() for cid in discord_channels.split(",") if cid.strip()] if discord_channels else None

            result = await dispatcher.broadcast_to_all(
                message=message,
                line_user_ids=line_ids,
                discord_channel_ids=discord_ids,
            )
            if any(v > 0 for v in result.values()):
                logger.info("Evolution report pushed: %s", result)
        except Exception as e:
            logger.debug("Evolution push skipped: %s", e)

    async def _generate_evolution_summary(self, report: Dict[str, Any]) -> Optional[str]:
        """用 LLM 生成自然語言進化摘要"""
        try:
            from app.core.ai_connector import get_ai_connector

            connector = get_ai_connector()

            actions_desc = []
            for action in report.get("actions", []):
                atype = action.get("type", "")
                count = action.get("count", action.get("removed", 0))
                if atype == "seed_promotion":
                    actions_desc.append(f"升級了 {count} 個高頻成功模式為種子")
                elif atype == "pattern_demotion":
                    actions_desc.append(f"降級了 {count} 個持續失敗的模式")
                elif atype == "cleanup":
                    actions_desc.append(f"清理了 {count} 個過期學習記錄")

            trend = report.get("quality_trend", {})
            trend_desc = ""
            if trend:
                slope = trend.get("slope", 0)
                if slope > 0.005:
                    trend_desc = f"品質呈上升趨勢 (斜率 +{slope:.4f})"
                elif slope < -0.005:
                    trend_desc = f"品質呈下降趨勢 (斜率 {slope:.4f})"
                else:
                    trend_desc = "品質保持穩定"

            prompt = (
                f"你是乾坤智能體的自我觀察系統。請用一段簡潔的中文 (2-3 句話) 描述本次進化：\n"
                f"- 消費了 {report.get('signals_consumed', 0)} 個信號\n"
                f"- 動作：{'; '.join(actions_desc) if actions_desc else '無特殊動作'}\n"
                f"- 趨勢：{trend_desc}\n"
                f"請以第一人稱描述，語氣自然，不要列點。"
            )

            result = await connector.chat_completion(
                question=prompt,
                system_prompt="你是乾坤智能體。用簡潔中文描述你的自我進化過程。",
                max_tokens=150,
                temperature=0.7,
            )
            return result.get("content", "").strip() if result else None
        except Exception as e:
            logger.debug("LLM summary generation failed: %s", e)
            return None

    async def get_evolution_status(self) -> Dict[str, Any]:
        """取得最近一次進化狀態（供前端儀表板顯示）"""
        if not self.redis:
            return {"status": "no_redis"}

        try:
            raw = await self.redis.get(EVOLUTION_STATE_KEY)
            if raw:
                state = json.loads(raw)
                # 附加最新摘要
                summary_raw = await self.redis.get("agent:evolution:latest_summary")
                if summary_raw:
                    state["latest_summary"] = json.loads(summary_raw)
                return state
            return {"status": "never_run"}
        except Exception:
            return {"status": "error"}
