"""
Agent Evolution Scheduler -- orchestration + triggering + status

This is the main orchestrator that decides WHEN to evolve and
delegates the actual work to:
  - agent_evolution_actions: pattern promote/demote/cleanup/analysis
  - agent_evolution_persistence: DB history, graduations, summary, push

進化閉環:
    SelfEvaluator.signals -> Redis Queue
                              |
    EvolutionScheduler.evolve() <- 每 50 次查詢 / 每日觸發
                              |
    修正動作: 升級種子 / 降級模式 / 調整閾值 / 清理
                              |
    下次查詢自動受益（零人工介入）

Version: 2.0.0  (split into 3 modules)
Created: 2026-03-16
Updated: 2026-04-08
"""

import json
import logging
import time
from typing import Any, Dict, List

from .agent_evolution_actions import (
    SEVERITY_PRIORITY,
    analyze_failure_patterns,
    cleanup_stale_learnings,
    compute_quality_trend,
    demote_failing_patterns,
    promote_top_patterns,
)
from .agent_evolution_persistence import (
    generate_evolution_summary,
    persist_evolution_history,
    process_graduations,
    push_evolution_report,
)

logger = logging.getLogger(__name__)

# Redis keys
SIGNAL_QUEUE_KEY = "agent:evolution:signals"
EVAL_HISTORY_KEY = "agent:evolution:eval_history"
EVOLUTION_STATE_KEY = "agent:evolution:state"
QUERY_COUNTER_KEY = "agent:evolution:query_count"
LAST_EVOLUTION_KEY = "agent:evolution:last_run"
BASELINE_KEY_PREFIX = "agent:evolution:baseline:"
BASELINE_TTL = 8 * 86400  # 8 days
BASELINE_CHECK_AGE = 7 * 86400  # 7 days


class AgentEvolutionScheduler:
    """
    定期消費 SelfEvaluator 的改進信號，自動執行修正。

    觸發方式（任一條件滿足）:
    1. 查詢計數器達到 EVOLVE_EVERY_N_QUERIES (預設 50)
    2. 距離上次進化超過 EVOLVE_INTERVAL_SECONDS (預設 24h)

    不需要 cron/scheduler -- 在每次查詢結束時檢查，非阻塞執行。
    """

    # Re-export for backward compatibility (used in _analyze_failure_patterns delegate)
    SEVERITY_PRIORITY = SEVERITY_PRIORITY

    def __init__(self, redis: Any = None):
        self.redis = redis
        # EVO-4: 從 agent-policy.yaml 讀取閾值，fallback 硬編碼預設值
        try:
            from app.services.ai.core.ai_config import AIConfig
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

            # Domain-aware trigger: if any domain has 5+ consecutive low scores (<0.5),
            # trigger targeted evolution even if global thresholds not met
            try:
                for domain in ("doc", "dispatch", "erp", "graph", "pm", "analysis"):
                    domain_key = f"agent:domain_scores:{domain}"
                    raw_scores = await self.redis.lrange(domain_key, 0, 4)
                    if len(raw_scores) >= 5:
                        scores = [float(s) for s in raw_scores]
                        if all(s < 0.5 for s in scores):
                            logger.warning(
                                "Domain-aware trigger: %s has 5 consecutive low scores (avg=%.2f)",
                                domain, sum(scores) / len(scores),
                            )
                            return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    async def _get_current_avg_score(self) -> float:
        """Compute average of last 10 eval scores from Redis."""
        try:
            raw_list = await self.redis.lrange(EVAL_HISTORY_KEY, 0, 9)
            if not raw_list:
                return 0.0
            scores = []
            for raw in raw_list:
                try:
                    record = json.loads(raw)
                    scores.append(record.get("overall", 0))
                except (json.JSONDecodeError, TypeError):
                    continue
            return sum(scores) / len(scores) if scores else 0.0
        except Exception:
            return 0.0

    async def check_evolution_effectiveness(self) -> Dict[str, Any]:
        """
        Check effectiveness of past evolutions by comparing baselines
        recorded 7+ days ago with the current average eval score.

        Returns dict with effectiveness results for the evolution report.
        """
        result: Dict[str, Any] = {"checked": 0, "improved": 0, "degraded": 0}
        if not self.redis:
            return result

        try:
            current_avg = await self._get_current_avg_score()
            if current_avg == 0.0:
                return result

            # SCAN for all baseline keys
            cursor = 0
            expired_keys: List[str] = []
            now = time.time()

            while True:
                cursor, keys = await self.redis.scan(
                    cursor, match=f"{BASELINE_KEY_PREFIX}*", count=50,
                )
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode()
                    # Extract timestamp from key
                    try:
                        ts_str = key.replace(BASELINE_KEY_PREFIX, "")
                        baseline_ts = float(ts_str)
                    except (ValueError, TypeError):
                        continue

                    age = now - baseline_ts
                    if age < BASELINE_CHECK_AGE:
                        continue  # Not old enough to evaluate yet

                    # Read baseline score
                    raw = await self.redis.get(key)
                    if not raw:
                        continue
                    try:
                        baseline_score = float(raw)
                    except (ValueError, TypeError):
                        expired_keys.append(key)
                        continue

                    result["checked"] += 1
                    diff = current_avg - baseline_score

                    if diff > 0:
                        result["improved"] += 1
                        logger.info(
                            "Evolution effective: +%.2f improvement "
                            "(baseline=%.3f, current=%.3f, age=%.1fd)",
                            diff, baseline_score, current_avg, age / 86400,
                        )
                    elif diff < 0:
                        result["degraded"] += 1
                        logger.warning(
                            "Evolution degradation: %.2f "
                            "(baseline=%.3f, current=%.3f, age=%.1fd)",
                            diff, baseline_score, current_avg, age / 86400,
                        )
                        # Auto-rollback: if significant degradation (>0.1),
                        # demote recently promoted patterns to reduce damage
                        if diff < -0.1:
                            rollback_count = await self._auto_rollback_recent_promotions()
                            result["rollback"] = rollback_count
                            logger.warning(
                                "Auto-rollback triggered: demoted %d recent promotions "
                                "(degradation=%.3f)",
                                rollback_count, diff,
                            )

                    # Baseline evaluated, clean it up
                    expired_keys.append(key)

                if cursor == 0:
                    break

            # Clean up evaluated baselines
            for key in expired_keys:
                await self.redis.delete(key)

            if result["checked"]:
                logger.info(
                    "Evolution effectiveness: %d checked, %d improved, %d degraded",
                    result["checked"], result["improved"], result["degraded"],
                )

        except Exception as e:
            logger.debug("Evolution effectiveness check failed: %s", e)

        return result

    async def evolve(self) -> Dict[str, Any]:
        """
        執行自動進化。非阻塞，在背景執行。

        Returns:
            進化報告 dict
        """
        if not self.redis:
            return {"status": "skip", "reason": "no_redis"}

        # R-1: Check effectiveness of previous evolutions before consuming signals
        effectiveness = await self.check_evolution_effectiveness()

        # Pre-evolution snapshot for safe rollback
        try:
            query_count_raw = await self.redis.get(QUERY_COUNTER_KEY)
            _query_count_snapshot = int(query_count_raw) if query_count_raw else 0
            signal_queue_len = await self.redis.llen(SIGNAL_QUEUE_KEY) or 0
            from app.services.ai.misc.skill_snapshot_service import SkillSnapshotService
            snapshot_tag = await SkillSnapshotService.create_snapshot(
                trigger="evolution",
                metadata={
                    "query_count": _query_count_snapshot,
                    "signal_queue_length": signal_queue_len,
                },
            )
            if snapshot_tag:
                logger.info("Pre-evolution snapshot: %s", snapshot_tag)
        except Exception as snap_err:
            logger.debug("Snapshot before evolution skipped: %s", snap_err)

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
            failure_patterns = analyze_failure_patterns(signals)
            report["failure_patterns"] = failure_patterns

            # 3. 自動升級高頻成功模式為種子 (含 DB 閉環寫入)
            db_session = None
            try:
                from app.db.database import async_session_maker
                db_session = async_session_maker()
                _db = await db_session.__aenter__()
            except Exception:
                _db = None

            promoted = await promote_top_patterns(
                self.redis,
                min_hits=self.SEED_PROMOTE_MIN_HITS,
                min_success=self.SEED_PROMOTE_MIN_SUCCESS,
                db=_db,
            )

            if _db:
                try:
                    await _db.commit()
                    await db_session.__aexit__(None, None, None)
                except Exception:
                    pass
            if promoted:
                report["actions"].append({
                    "type": "seed_promotion",
                    "count": len(promoted),
                    "patterns": promoted,
                })
                actions_taken.append({"type": "promote", "count": len(promoted)})

            # 4. 降級持續失敗的模式
            demoted = await demote_failing_patterns(
                self.redis,
                max_success=self.PATTERN_DEMOTE_MAX_SUCCESS,
            )
            if demoted:
                report["actions"].append({
                    "type": "pattern_demotion",
                    "count": len(demoted),
                    "patterns": demoted,
                })
                actions_taken.append({"type": "demote", "count": len(demoted)})

            # 5. 計算品質趨勢
            trend = await compute_quality_trend(self.redis, EVAL_HISTORY_KEY)
            report["quality_trend"] = trend

            # 6. Process DB learning graduations
            graduation_result = await process_graduations()
            if graduation_result.get("graduated") or graduation_result.get("chronic"):
                report["actions"].append({
                    "type": "graduation_processing",
                    "graduated": graduation_result.get("graduated", 0),
                    "chronic": graduation_result.get("chronic", 0),
                })
                if graduation_result.get("graduated"):
                    actions_taken.append({"type": "graduate", "count": graduation_result["graduated"]})
                if graduation_result.get("chronic"):
                    actions_taken.append({"type": "chronic", "count": graduation_result["chronic"]})

            # 7. 清理過期學習
            cleaned = await cleanup_stale_learnings(self.redis)
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

            # Persist evolution history to DB (non-blocking)
            try:
                await persist_evolution_history(
                    redis=self.redis,
                    report=report,
                    signals=signals,
                    actions_taken=actions_taken,
                    evolve_every_n_queries=self.EVOLVE_EVERY_N_QUERIES,
                    query_counter_key=QUERY_COUNTER_KEY,
                )
            except Exception as persist_err:
                logger.debug("Evolution history persistence skipped: %s", persist_err)

            # Phase 2D: LLM 生成進化摘要（非阻塞）
            if actions_taken or report.get("signals_consumed", 0) > 0:
                try:
                    summary = await generate_evolution_summary(report)
                    if summary:
                        await self.redis.set(
                            "agent:evolution:latest_summary",
                            json.dumps({"summary": summary, "timestamp": time.time()}, ensure_ascii=False),
                        )
                        await self.redis.expire("agent:evolution:latest_summary", 7 * 86400)
                        # Phase 2F: 推送進化報告到 LINE/Discord（非阻塞）
                        await push_evolution_report(summary, report)
                except Exception as sum_err:
                    logger.debug("Evolution summary generation skipped: %s", sum_err)

            # R-1: Record baseline score for future effectiveness measurement
            try:
                baseline_score = await self._get_current_avg_score()
                if baseline_score > 0:
                    baseline_key = f"{BASELINE_KEY_PREFIX}{time.time():.0f}"
                    await self.redis.set(baseline_key, str(round(baseline_score, 4)))
                    await self.redis.expire(baseline_key, BASELINE_TTL)
            except Exception:
                pass

            # Store effectiveness result in report
            report["evolution_effectiveness"] = effectiveness

        except Exception as e:
            logger.warning("Evolution failed (non-critical): %s", e)
            report["error"] = str(e)

        # 進化後失效 IntelligenceState 快取，讓下次查詢讀到最新狀態
        try:
            await self.redis.delete("agent:intelligence:snapshot")
        except Exception:
            pass

        return report

    # ─── Internal helpers ──────────────────────────────────────

    async def _auto_rollback_recent_promotions(self) -> int:
        """
        Auto-rollback: demote patterns promoted in the last 7 days
        when significant quality degradation is detected (>0.1 drop).

        Returns the number of patterns demoted.
        """
        demoted = 0
        try:
            # Scan Redis patterns index for recently promoted ones
            # (patterns with high scores but added recently)
            index_key = "agent:patterns:index"
            members = await self.redis.zrevrange(index_key, 0, 19, withscores=True)
            if not members:
                return 0

            for member_raw, score in members:
                member = member_raw.decode() if isinstance(member_raw, bytes) else member_raw
                detail_key = f"agent:patterns:detail:{member}"
                detail_raw = await self.redis.hgetall(detail_key)
                if not detail_raw:
                    continue

                # Check if pattern was recently promoted (< 7 days)
                promoted_at = detail_raw.get(b"promoted_at") or detail_raw.get("promoted_at")
                if promoted_at:
                    try:
                        promoted_ts = float(promoted_at)
                        if time.time() - promoted_ts < 7 * 86400:
                            # Recent promotion — demote it
                            await self.redis.zrem(index_key, member)
                            await self.redis.delete(detail_key)
                            demoted += 1
                    except (ValueError, TypeError):
                        pass

            if demoted:
                logger.warning(
                    "Auto-rollback: removed %d recently promoted patterns", demoted
                )
        except Exception as e:
            logger.debug("Auto-rollback failed: %s", e)
        return demoted

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

    # ─── Backward-compatible method delegates ──────────────────

    def _analyze_failure_patterns(
        self, signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Delegate to module-level function (backward compat)."""
        return analyze_failure_patterns(signals)

    async def _promote_top_patterns(self) -> List[str]:
        """Delegate to module-level function (backward compat)."""
        return await promote_top_patterns(
            self.redis,
            min_hits=self.SEED_PROMOTE_MIN_HITS,
            min_success=self.SEED_PROMOTE_MIN_SUCCESS,
        )

    async def _demote_failing_patterns(self) -> List[str]:
        """Delegate to module-level function (backward compat)."""
        return await demote_failing_patterns(
            self.redis,
            max_success=self.PATTERN_DEMOTE_MAX_SUCCESS,
        )

    async def _compute_quality_trend(self) -> Dict[str, Any]:
        """Delegate to module-level function (backward compat)."""
        return await compute_quality_trend(self.redis, EVAL_HISTORY_KEY)

    async def _cleanup_stale_learnings(self) -> int:
        """Delegate to module-level function (backward compat)."""
        return await cleanup_stale_learnings(self.redis)

    async def _process_graduations(self) -> Dict[str, int]:
        """Delegate to module-level function (backward compat)."""
        return await process_graduations()

    async def _persist_evolution_history(
        self,
        report: Dict[str, Any],
        signals: List[Dict[str, Any]],
        actions_taken: List[Dict[str, Any]],
    ) -> None:
        """Delegate to module-level function (backward compat)."""
        await persist_evolution_history(
            redis=self.redis,
            report=report,
            signals=signals,
            actions_taken=actions_taken,
            evolve_every_n_queries=self.EVOLVE_EVERY_N_QUERIES,
            query_counter_key=QUERY_COUNTER_KEY,
        )

    async def _generate_evolution_summary(self, report: Dict[str, Any]):
        """Delegate to module-level function (backward compat)."""
        return await generate_evolution_summary(report)

    async def _push_evolution_report(self, summary: str, report: Dict[str, Any]) -> None:
        """Delegate to module-level function (backward compat)."""
        await push_evolution_report(summary, report)

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
