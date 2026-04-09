"""
Reranker A/B Benchmark -- compares v1 rule-based vs v2 Gemma4 reranker.

Evaluates search quality using a ground truth dataset of 30 queries
across 8 categories (agency, keyword, dispatch, date_range, entity,
tender, finance, mixed).

Metrics:
  - Keyword Hit Rate: % of results containing expected keywords
  - Precision@K: % of top-K results that are relevant
  - MRR (Mean Reciprocal Rank): 1/rank of first relevant result
  - Latency: end-to-end query time in ms

Usage:
  python -m tests.benchmarks.reranker_benchmark [--mode v1|v2|both] [--top-k 5]

Version: 1.0.0
Created: 2026-04-05
"""

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GROUND_TRUTH_PATH = Path(__file__).parent / "search_ground_truth.json"


class SearchBenchmark:
    """Evaluates search quality using ground truth dataset."""

    def __init__(self, ground_truth_path: Optional[str] = None):
        path = Path(ground_truth_path) if ground_truth_path else GROUND_TRUTH_PATH
        with open(path, encoding="utf-8") as f:
            self.queries: List[Dict[str, Any]] = json.load(f)
        logger.info("Loaded %d ground truth queries from %s", len(self.queries), path)

    # ── Metric computation (static, usable without DB) ──

    @staticmethod
    def compute_keyword_hit_rate(
        results: List[Dict[str, Any]],
        expected_keywords: List[str],
    ) -> float:
        """What % of results contain at least one expected keyword.

        Scans subject, sender, doc_number, and receiver fields.
        Returns 0.0 if results or expected_keywords is empty.
        """
        if not results or not expected_keywords:
            return 0.0
        hits = 0
        for doc in results:
            text = " ".join(
                str(doc.get(f, ""))
                for f in ("subject", "sender", "doc_number", "receiver", "category")
            )
            if any(kw in text for kw in expected_keywords):
                hits += 1
        return hits / len(results)

    @staticmethod
    def compute_precision_at_k(
        results: List[Dict[str, Any]],
        expected_keywords: List[str],
        k: int = 5,
    ) -> float:
        """Precision@K -- fraction of top-K results that are relevant.

        A result is considered relevant if it contains at least one
        expected keyword in subject or sender.
        """
        top_k = results[:k]
        if not top_k or not expected_keywords:
            return 0.0
        relevant = sum(
            1
            for doc in top_k
            if any(
                kw in f"{doc.get('subject', '')} {doc.get('sender', '')} {doc.get('receiver', '')}"
                for kw in expected_keywords
            )
        )
        return relevant / len(top_k)

    @staticmethod
    def compute_mrr(
        results: List[Dict[str, Any]],
        expected_keywords: List[str],
    ) -> float:
        """Mean Reciprocal Rank -- 1/rank of first relevant result.

        Returns 0.0 if no relevant result found.
        """
        if not expected_keywords:
            return 0.0
        for i, doc in enumerate(results):
            text = f"{doc.get('subject', '')} {doc.get('sender', '')} {doc.get('receiver', '')}"
            if any(kw in text for kw in expected_keywords):
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def compute_ndcg_at_k(
        results: List[Dict[str, Any]],
        expected_keywords: List[str],
        k: int = 5,
    ) -> float:
        """Normalized Discounted Cumulative Gain at K.

        Binary relevance: 1 if any expected keyword in subject/sender, else 0.
        """
        import math

        top_k = results[:k]
        if not top_k or not expected_keywords:
            return 0.0

        # Compute gains
        gains = []
        for doc in top_k:
            text = f"{doc.get('subject', '')} {doc.get('sender', '')} {doc.get('receiver', '')}"
            rel = 1.0 if any(kw in text for kw in expected_keywords) else 0.0
            gains.append(rel)

        # DCG
        dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))

        # Ideal DCG (all relevant results first)
        ideal_gains = sorted(gains, reverse=True)
        idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))

        return dcg / idcg if idcg > 0 else 0.0

    # ── Single query execution ──

    async def run_single_query(
        self,
        query_entry: Dict[str, Any],
        db_session: Any,
        reranker_mode: str = "v2",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Execute a single benchmark query and compute metrics.

        Args:
            query_entry: Ground truth entry with query, expected_keywords, etc.
            db_session: SQLAlchemy async session.
            reranker_mode: "v1" (rule-based only) or "v2" (rule + LLM rerank).
            top_k: Number of top results for P@K.

        Returns:
            Dict with query metadata and computed metrics.
        """
        from app.services.ai.tools.tool_executor_search import SearchToolExecutor
        from app.services.ai.core.ai_config import get_ai_config

        config = get_ai_config()
        query_text = query_entry["query"]
        expected_kw = query_entry.get("expected_keywords", [])

        # Build search params from ground truth
        params: Dict[str, Any] = {"keywords": [query_text]}
        if query_entry.get("expected_doc_type"):
            params["doc_type"] = query_entry["expected_doc_type"]

        start_ts = time.perf_counter()

        try:
            # Lazy-import to avoid import-time DB dependency
            from app.services.ai.core.embedding_manager import EmbeddingManager
            from app.services.ai.core.base_ai_service import BaseAIService

            ai_connector = BaseAIService.get_shared_connector()
            embedding_mgr = EmbeddingManager()
            executor = SearchToolExecutor(
                db=db_session,
                ai_connector=ai_connector,
                embedding_mgr=embedding_mgr,
                config=config,
            )

            result = await executor.search_documents(params)
            documents = result.get("documents", [])

            # If v2 mode, apply LLM reranking on top
            if reranker_mode == "v2" and len(documents) > 3:
                try:
                    from app.services.ai.search.reranker import rerank_with_llm

                    documents = await rerank_with_llm(
                        ai_connector=ai_connector,
                        documents=documents,
                        query=query_text,
                        query_terms=expected_kw or [query_text],
                        top_n=top_k * 2,
                    )
                except Exception as e:
                    logger.warning("LLM rerank failed for query '%s': %s", query_text, e)

        except Exception as e:
            logger.error("Search failed for query '%s': %s", query_text, e)
            documents = []

        elapsed_ms = (time.perf_counter() - start_ts) * 1000

        return {
            "id": query_entry.get("id", ""),
            "query": query_text,
            "category": query_entry["category"],
            "mode": reranker_mode,
            "latency_ms": round(elapsed_ms, 1),
            "result_count": len(documents),
            "precision_at_k": round(
                self.compute_precision_at_k(documents, expected_kw, k=top_k), 4
            ),
            "mrr": round(self.compute_mrr(documents, expected_kw), 4),
            "ndcg_at_k": round(
                self.compute_ndcg_at_k(documents, expected_kw, k=top_k), 4
            ),
            "keyword_hit_rate": round(
                self.compute_keyword_hit_rate(documents, expected_kw), 4
            ),
            "min_expected": query_entry.get("min_expected_results", 0),
            "meets_minimum": len(documents) >= query_entry.get("min_expected_results", 0),
        }

    # ── Full benchmark suite ──

    async def run_benchmark(
        self,
        db_session: Any,
        mode: str = "both",
        top_k: int = 5,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run full benchmark suite.

        Args:
            db_session: SQLAlchemy async session.
            mode: "v1", "v2", or "both" for A/B comparison.
            top_k: Top-K cutoff for precision/NDCG.
            categories: If set, only run queries in these categories.

        Returns:
            Dict with per-query results and aggregate summary.
        """
        results: Dict[str, Any] = {"v1": [], "v2": [], "summary": {}, "meta": {}}
        results["meta"] = {
            "total_queries": len(self.queries),
            "mode": mode,
            "top_k": top_k,
            "categories": categories,
        }

        queries = self.queries
        if categories:
            queries = [q for q in queries if q["category"] in categories]
            results["meta"]["filtered_queries"] = len(queries)

        for entry in queries:
            if mode in ("v1", "both"):
                r1 = await self.run_single_query(entry, db_session, "v1", top_k)
                results["v1"].append(r1)
            if mode in ("v2", "both"):
                r2 = await self.run_single_query(entry, db_session, "v2", top_k)
                results["v2"].append(r2)

        # Compute aggregate metrics per mode
        for m in ("v1", "v2"):
            entries = results[m]
            if not entries:
                continue
            n = len(entries)
            results["summary"][m] = {
                "avg_precision_at_k": round(
                    sum(e["precision_at_k"] for e in entries) / n, 4
                ),
                "avg_mrr": round(sum(e["mrr"] for e in entries) / n, 4),
                "avg_ndcg_at_k": round(
                    sum(e["ndcg_at_k"] for e in entries) / n, 4
                ),
                "avg_latency_ms": round(
                    sum(e["latency_ms"] for e in entries) / n, 1
                ),
                "avg_hit_rate": round(
                    sum(e["keyword_hit_rate"] for e in entries) / n, 4
                ),
                "meets_minimum_pct": round(
                    sum(1 for e in entries if e["meets_minimum"]) / n, 4
                ),
                "total_queries": n,
            }

            # Per-category breakdown
            cat_metrics: Dict[str, Dict[str, float]] = {}
            for entry in entries:
                cat = entry["category"]
                if cat not in cat_metrics:
                    cat_metrics[cat] = {
                        "precision_sum": 0.0,
                        "mrr_sum": 0.0,
                        "latency_sum": 0.0,
                        "count": 0,
                    }
                cat_metrics[cat]["precision_sum"] += entry["precision_at_k"]
                cat_metrics[cat]["mrr_sum"] += entry["mrr"]
                cat_metrics[cat]["latency_sum"] += entry["latency_ms"]
                cat_metrics[cat]["count"] += 1

            results["summary"][m]["by_category"] = {
                cat: {
                    "avg_precision_at_k": round(v["precision_sum"] / v["count"], 4),
                    "avg_mrr": round(v["mrr_sum"] / v["count"], 4),
                    "avg_latency_ms": round(v["latency_sum"] / v["count"], 1),
                    "count": int(v["count"]),
                }
                for cat, v in cat_metrics.items()
            }

        # A/B comparison (if both modes ran)
        if "v1" in results["summary"] and "v2" in results["summary"]:
            s1 = results["summary"]["v1"]
            s2 = results["summary"]["v2"]
            results["summary"]["comparison"] = {
                "precision_delta": round(
                    s2["avg_precision_at_k"] - s1["avg_precision_at_k"], 4
                ),
                "mrr_delta": round(s2["avg_mrr"] - s1["avg_mrr"], 4),
                "latency_delta_ms": round(
                    s2["avg_latency_ms"] - s1["avg_latency_ms"], 1
                ),
                "hit_rate_delta": round(
                    s2["avg_hit_rate"] - s1["avg_hit_rate"], 4
                ),
                "v2_better_precision": s2["avg_precision_at_k"] > s1["avg_precision_at_k"],
                "v2_faster": s2["avg_latency_ms"] < s1["avg_latency_ms"],
            }

        return results

    # ── Offline metric-only evaluation (no DB required) ──

    def evaluate_results_offline(
        self,
        search_results: Dict[str, List[Dict[str, Any]]],
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Evaluate pre-collected search results against ground truth.

        Use this for offline evaluation when you have already collected
        search results and want to compute metrics without DB access.

        Args:
            search_results: Mapping of query_id -> list of result documents.
            top_k: Top-K cutoff.

        Returns:
            Aggregate metrics dict.
        """
        metrics = []
        for entry in self.queries:
            qid = entry.get("id", entry["query"])
            docs = search_results.get(qid, [])
            expected_kw = entry.get("expected_keywords", [])

            metrics.append({
                "id": qid,
                "category": entry["category"],
                "precision_at_k": self.compute_precision_at_k(docs, expected_kw, top_k),
                "mrr": self.compute_mrr(docs, expected_kw),
                "ndcg_at_k": self.compute_ndcg_at_k(docs, expected_kw, top_k),
                "keyword_hit_rate": self.compute_keyword_hit_rate(docs, expected_kw),
                "result_count": len(docs),
            })

        n = len(metrics) if metrics else 1
        return {
            "avg_precision_at_k": round(sum(m["precision_at_k"] for m in metrics) / n, 4),
            "avg_mrr": round(sum(m["mrr"] for m in metrics) / n, 4),
            "avg_ndcg_at_k": round(sum(m["ndcg_at_k"] for m in metrics) / n, 4),
            "avg_hit_rate": round(sum(m["keyword_hit_rate"] for m in metrics) / n, 4),
            "total_queries": len(metrics),
            "details": metrics,
        }


def _format_summary(results: Dict[str, Any]) -> str:
    """Format benchmark results as a readable table."""
    lines = ["\n=== Search Quality Benchmark Results ===\n"]

    for mode in ("v1", "v2"):
        if mode not in results.get("summary", {}):
            continue
        s = results["summary"][mode]
        label = "Rule-based (v1)" if mode == "v1" else "Gemma4 Rerank (v2)"
        lines.append(f"--- {label} ---")
        lines.append(f"  Queries:       {s['total_queries']}")
        lines.append(f"  Avg P@K:       {s['avg_precision_at_k']:.4f}")
        lines.append(f"  Avg MRR:       {s['avg_mrr']:.4f}")
        lines.append(f"  Avg nDCG@K:    {s['avg_ndcg_at_k']:.4f}")
        lines.append(f"  Avg Hit Rate:  {s['avg_hit_rate']:.4f}")
        lines.append(f"  Avg Latency:   {s['avg_latency_ms']:.1f} ms")
        lines.append(f"  Meets Minimum: {s['meets_minimum_pct']:.1%}")
        lines.append("")

        if "by_category" in s:
            lines.append("  By Category:")
            for cat, cv in sorted(s["by_category"].items()):
                lines.append(
                    f"    {cat:20s}  P@K={cv['avg_precision_at_k']:.3f}  "
                    f"MRR={cv['avg_mrr']:.3f}  "
                    f"Lat={cv['avg_latency_ms']:.0f}ms  "
                    f"(n={cv['count']})"
                )
            lines.append("")

    if "comparison" in results.get("summary", {}):
        c = results["summary"]["comparison"]
        lines.append("--- A/B Comparison (v2 - v1) ---")
        lines.append(f"  Precision delta:  {c['precision_delta']:+.4f}")
        lines.append(f"  MRR delta:        {c['mrr_delta']:+.4f}")
        lines.append(f"  Hit rate delta:   {c['hit_rate_delta']:+.4f}")
        lines.append(f"  Latency delta:    {c['latency_delta_ms']:+.1f} ms")
        winner = "v2 (Gemma4)" if c["v2_better_precision"] else "v1 (Rule-based)"
        lines.append(f"  Precision winner: {winner}")
        lines.append("")

    return "\n".join(lines)


async def _main(mode: str = "both", top_k: int = 5) -> None:
    """CLI entry point."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from app.core.database import get_async_session_factory

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    benchmark = SearchBenchmark()
    logger.info(
        "Starting benchmark: mode=%s, top_k=%d, queries=%d",
        mode, top_k, len(benchmark.queries),
    )

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        results = await benchmark.run_benchmark(session, mode=mode, top_k=top_k)

    print(_format_summary(results))

    # Save raw results
    output_path = Path(__file__).parent / "benchmark_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Raw results saved to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search quality benchmark")
    parser.add_argument("--mode", choices=["v1", "v2", "both"], default="both")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(_main(mode=args.mode, top_k=args.top_k))
