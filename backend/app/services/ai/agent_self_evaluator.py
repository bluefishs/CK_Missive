"""
Agent Self-Evaluator — 每次回答自動評分 + 改進信號

解決核心問題：乾坤智能體目前是「被動記錄」而非「主動進化」。
本模組在每次回答後自動評估品質，產生改進信號，
驅動 EvolutionScheduler 進行自動修正。

進化閉環：
    Query → Answer → SelfEvaluator → Score + Signals
                                         ↓
                        EvolutionScheduler → Auto-Improve

Phase 8: Hierarchical Evaluation Signals
    - 4 severity levels: CRITICAL / HIGH / MEDIUM / LOW
    - Signal severity drives EvolutionScheduler priority

Version: 1.1.0
Created: 2026-03-16
Updated: 2026-03-16 - v1.1.0 Phase 8: hierarchical severity levels
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Severity Levels ──────────────────────────────────────
SEVERITY_CRITICAL = "critical"  # score < 0.3
SEVERITY_HIGH = "high"          # score < 0.5
SEVERITY_MEDIUM = "medium"      # score < 0.7
SEVERITY_LOW = "low"            # score >= 0.7


def classify_severity(overall_score: float) -> str:
    """Classify overall score into 4 severity levels."""
    if overall_score < 0.3:
        return SEVERITY_CRITICAL
    elif overall_score < 0.5:
        return SEVERITY_HIGH
    elif overall_score < 0.7:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


@dataclass
class EvalScore:
    """單次回答的品質評分"""
    relevance: float = 0.0          # 問答相關性 (0-1)
    completeness: float = 0.0       # 回答完整性 (0-1)
    citation_accuracy: float = 0.0  # 引用準確率 (0-1)
    latency_ok: bool = True         # 延遲是否達標
    tool_efficiency: float = 0.0    # 工具使用效率 (0-1)
    overall: float = 0.0           # 綜合分數 (0-1)
    severity: str = SEVERITY_LOW   # hierarchical severity level
    signals: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def needs_improvement(self) -> bool:
        return self.overall < 0.7


class AgentSelfEvaluator:
    """
    每次回答後自動評估品質。

    不需要 LLM 呼叫 — 純規則式評估，零額外延遲。
    產生的信號儲存到 Redis，供 EvolutionScheduler 定期消費。
    """

    # 預設權重配置
    DEFAULT_WEIGHTS = {
        "relevance": 0.30,
        "completeness": 0.25,
        "citation_accuracy": 0.20,
        "latency": 0.10,
        "tool_efficiency": 0.15,
    }

    # 領域特定權重
    DOMAIN_WEIGHTS = {
        "erp": {
            "relevance": 0.25, "completeness": 0.25,
            "citation_accuracy": 0.25, "latency": 0.10, "tool_efficiency": 0.15,
        },
        "dispatch": {
            "relevance": 0.30, "completeness": 0.20,
            "citation_accuracy": 0.15, "latency": 0.20, "tool_efficiency": 0.15,
        },
        "pm": {
            "relevance": 0.25, "completeness": 0.30,
            "citation_accuracy": 0.20, "latency": 0.10, "tool_efficiency": 0.15,
        },
        "tender": {
            "relevance": 0.25, "completeness": 0.30,
            "citation_accuracy": 0.20, "latency": 0.10, "tool_efficiency": 0.15,
        },
        "graph": {
            "relevance": 0.25, "completeness": 0.20,
            "citation_accuracy": 0.30, "latency": 0.10, "tool_efficiency": 0.15,
        },
        "doc": {
            "relevance": 0.30, "completeness": 0.20,
            "citation_accuracy": 0.25, "latency": 0.10, "tool_efficiency": 0.15,
        },
        "sales": {
            "relevance": 0.25, "completeness": 0.30,
            "citation_accuracy": 0.15, "latency": 0.15, "tool_efficiency": 0.15,
        },
        "field": {
            "relevance": 0.25, "completeness": 0.20,
            "citation_accuracy": 0.15, "latency": 0.25, "tool_efficiency": 0.15,
        },
    }

    @staticmethod
    def get_weights(context: Optional[str] = None) -> dict:
        """Return domain-specific weights if context matches, else defaults."""
        return AgentSelfEvaluator.DOMAIN_WEIGHTS.get(
            context, AgentSelfEvaluator.DEFAULT_WEIGHTS
        )

    # 閾值
    LATENCY_THRESHOLD_MS = 5000    # 延遲超過 5 秒扣分
    MAX_REASONABLE_TOOLS = 6       # 工具呼叫超過 6 次扣分
    MIN_ANSWER_LENGTH = 20         # 回答少於 20 字扣分
    SIGNAL_QUEUE_KEY = "agent:evolution:signals"
    EVAL_HISTORY_KEY = "agent:evolution:eval_history"

    def evaluate(
        self,
        question: str,
        answer: str,
        tool_results: List[Dict[str, Any]],
        trace: Any,
        citation_result: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ) -> EvalScore:
        """
        評估單次回答品質。純規則式，零 LLM 呼叫。

        Args:
            context: Domain context for weight selection (e.g. "erp", "dispatch", "pm")

        Returns:
            EvalScore with overall score and improvement signals
        """
        score = EvalScore()
        score.relevance = self._eval_relevance(question, answer)
        score.completeness = self._eval_completeness(answer, tool_results)
        score.citation_accuracy = self._eval_citation(citation_result)
        score.latency_ok = self._eval_latency(trace)
        score.tool_efficiency = self._eval_tool_efficiency(tool_results, trace)

        # 加權綜合分 (領域感知)
        weights = self.get_weights(context)
        score.overall = (
            weights["relevance"] * score.relevance
            + weights["completeness"] * score.completeness
            + weights["citation_accuracy"] * score.citation_accuracy
            + weights["latency"] * (1.0 if score.latency_ok else 0.3)
            + weights["tool_efficiency"] * score.tool_efficiency
        )

        # 層級化嚴重度分類 (Phase 8)
        score.severity = classify_severity(score.overall)

        # 產生改進信號
        score.signals = self._generate_signals(question, answer, score, trace)

        if score.needs_improvement:
            logger.info(
                "Self-eval LOW: overall=%.2f relevance=%.2f completeness=%.2f "
                "citation=%.2f latency=%s efficiency=%.2f signals=%d",
                score.overall, score.relevance, score.completeness,
                score.citation_accuracy, score.latency_ok,
                score.tool_efficiency, len(score.signals),
            )

        return score

    async def evaluate_and_store(
        self,
        question: str,
        answer: str,
        tool_results: List[Dict[str, Any]],
        trace: Any,
        citation_result: Optional[Dict[str, Any]] = None,
        redis: Optional[Any] = None,
        context: Optional[str] = None,
    ) -> EvalScore:
        """評估並儲存信號到 Redis（供 EvolutionScheduler 消費）"""
        score = self.evaluate(question, answer, tool_results, trace, citation_result, context)

        if redis and score.signals:
            try:
                import json
                for signal in score.signals:
                    signal["timestamp"] = time.time()
                    signal["question_preview"] = question[:100]
                    await redis.lpush(
                        self.SIGNAL_QUEUE_KEY, json.dumps(signal, ensure_ascii=False)
                    )
                # 保留最近 500 個信號
                await redis.ltrim(self.SIGNAL_QUEUE_KEY, 0, 499)

                # 記錄評分歷史（供趨勢分析）
                eval_record = {
                    "ts": time.time(),
                    "overall": round(score.overall, 3),
                    "severity": score.severity,
                    "relevance": round(score.relevance, 3),
                    "tools_used": len(tool_results),
                    "latency_ms": getattr(trace, "total_ms", 0),
                }
                await redis.lpush(
                    self.EVAL_HISTORY_KEY, json.dumps(eval_record)
                )
                await redis.ltrim(self.EVAL_HISTORY_KEY, 0, 999)
            except Exception as e:
                logger.debug("Eval store failed (non-critical): %s", e)

        # CRITICAL 即時回饋：不等 EvolutionScheduler，直接寫入短效快取
        if score.severity == "critical" and redis:
            try:
                import json
                for sig in score.signals:
                    sig_type = sig.get("type", "unknown")
                    await redis.setex(
                        f"agent:critical_feedback:{sig_type}",
                        300,  # 5 minutes TTL
                        json.dumps({
                            "type": sig_type,
                            "severity": "critical",
                            "score": round(score.overall, 3),
                            "question": question[:100],
                            "timestamp": time.time(),
                        }, ensure_ascii=False),
                    )
                logger.warning(
                    "CRITICAL signal immediate write: %d signals, score=%.2f",
                    len(score.signals), score.overall,
                )
            except Exception as e:
                logger.debug("CRITICAL feedback write failed: %s", e)

        return score

    # ─── 評估維度 ──────────────────────────────────────────

    def _eval_relevance(self, question: str, answer: str) -> float:
        """問答相關性：關鍵詞重疊率"""
        if not answer or len(answer) < self.MIN_ANSWER_LENGTH:
            return 0.2

        # 提取問題中的中文關鍵詞（2-4 字）
        q_chars = set()
        for i in range(len(question)):
            for length in (2, 3, 4):
                if i + length <= len(question):
                    ngram = question[i:i + length]
                    if all('\u4e00' <= c <= '\u9fff' for c in ngram):
                        q_chars.add(ngram)

        if not q_chars:
            return 0.8  # 非中文查詢，給予中性分數

        # 計算答案中包含多少問題關鍵詞
        hits = sum(1 for kw in q_chars if kw in answer)
        coverage = hits / len(q_chars) if q_chars else 0
        return min(1.0, 0.3 + coverage * 0.7)

    def _eval_completeness(
        self, answer: str, tool_results: List[Dict[str, Any]]
    ) -> float:
        """回答完整性：長度 + 工具結果覆蓋"""
        if not answer:
            return 0.0

        # 長度分數
        length_score = min(1.0, len(answer) / 200)

        # 工具結果利用率
        if not tool_results:
            return length_score * 0.7  # 無工具呼叫時降分

        tools_with_data = sum(
            1 for tr in tool_results
            if tr.get("result") and str(tr.get("result")) != "[]"
        )
        utilization = tools_with_data / len(tool_results) if tool_results else 0

        return 0.4 * length_score + 0.6 * utilization

    def _eval_citation(self, citation_result: Optional[Dict[str, Any]]) -> float:
        """引用準確率"""
        if not citation_result:
            return 0.7  # 無引用結果時給予中性分數
        if citation_result.get("valid"):
            return 1.0
        total = citation_result.get("total", 0)
        verified = citation_result.get("verified", 0)
        if total == 0:
            return 0.7
        return verified / total

    def _eval_latency(self, trace: Any) -> bool:
        """延遲是否達標"""
        total_ms = getattr(trace, "total_ms", 0)
        return total_ms <= self.LATENCY_THRESHOLD_MS

    def _eval_tool_efficiency(
        self, tool_results: List[Dict[str, Any]], trace: Any
    ) -> float:
        """工具使用效率：成功率 × 數量合理性"""
        if not tool_results:
            return 0.8  # 不需要工具的查詢

        total = len(tool_results)
        failed = len(getattr(trace, "tools_failed", []))
        success_rate = (total - failed) / total if total > 0 else 0

        # 工具數量合理性
        count_penalty = 1.0
        if total > self.MAX_REASONABLE_TOOLS:
            count_penalty = self.MAX_REASONABLE_TOOLS / total

        return success_rate * count_penalty

    # ─── 改進信號生成 ──────────────────────────────────────

    # 高延遲門檻 (>30s 視為 HIGH severity)
    HIGH_LATENCY_THRESHOLD_MS = 30000

    def _generate_signals(
        self,
        question: str,
        answer: str,
        score: EvalScore,
        trace: Any,
    ) -> List[Dict[str, Any]]:
        """根據評分產生具體的改進信號（含層級化嚴重度）"""
        signals: List[Dict[str, Any]] = []
        total_ms = getattr(trace, "total_ms", 0)
        all_tools_failed = (
            score.tool_efficiency == 0.0
            and len(getattr(trace, "tools_failed", [])) > 0
        )

        # CRITICAL: 全部工具失敗
        if all_tools_failed:
            signals.append({
                "type": "all_tools_failed",
                "severity": SEVERITY_CRITICAL,
                "detail": f"efficiency=0, failed={getattr(trace, 'tools_failed', [])}",
                "suggestion": "所有工具都失敗，檢查後端服務與資料庫連線",
            })

        # CRITICAL: 事實型查詢零引用
        if (
            score.citation_accuracy == 0.0
            and score.relevance < 0.5
            and score.completeness < 0.3
        ):
            signals.append({
                "type": "zero_citation_factual",
                "severity": SEVERITY_CRITICAL,
                "detail": f"citation=0, relevance={score.relevance:.2f}",
                "suggestion": "事實型查詢完全無引用，可能需要重新檢查檢索管線",
            })

        if score.relevance < 0.5:
            signals.append({
                "type": "low_relevance",
                "severity": SEVERITY_HIGH,
                "detail": f"relevance={score.relevance:.2f}",
                "suggestion": "prompt 可能需要更明確的指引來回答此類問題",
            })

        if score.completeness < 0.4:
            signals.append({
                "type": "incomplete_answer",
                "severity": SEVERITY_HIGH,
                "detail": f"completeness={score.completeness:.2f}, answer_len={len(answer)}",
                "suggestion": "工具結果未被充分利用，或回答過短",
            })

        if score.citation_accuracy < 0.5 and score.citation_accuracy > 0.0:
            signals.append({
                "type": "citation_inaccurate",
                "severity": SEVERITY_MEDIUM,
                "detail": f"citation_accuracy={score.citation_accuracy:.2f}",
                "suggestion": "synthesis prompt 需要強化引用驗證",
            })

        if not score.latency_ok:
            severity = (
                SEVERITY_HIGH
                if total_ms > self.HIGH_LATENCY_THRESHOLD_MS
                else SEVERITY_MEDIUM
            )
            signals.append({
                "type": "high_latency",
                "severity": severity,
                "detail": f"latency={total_ms}ms > {self.LATENCY_THRESHOLD_MS}ms",
                "suggestion": "考慮減少工具呼叫數或使用模式匹配跳過 LLM",
            })

        if score.tool_efficiency < 0.5 and not all_tools_failed:
            failed = getattr(trace, "tools_failed", [])
            signals.append({
                "type": "tool_inefficiency",
                "severity": SEVERITY_MEDIUM,
                "detail": f"efficiency={score.tool_efficiency:.2f}, failed={failed}",
                "suggestion": "工具失敗率過高，檢查工具健康狀態",
            })

        # Attach overall severity to every signal for filtering
        for sig in signals:
            sig["overall_severity"] = score.severity

        return signals


# ─── 全域單例 ──────────────────────────────────────────

_evaluator: Optional[AgentSelfEvaluator] = None


def get_self_evaluator() -> AgentSelfEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = AgentSelfEvaluator()
    return _evaluator
