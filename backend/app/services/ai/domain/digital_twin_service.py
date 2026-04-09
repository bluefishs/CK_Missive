"""
數位分身服務層 — 聚合多源自覺資料

從 digital_twin.py 端點提取的業務邏輯：
- Agent 拓撲圖構建
- QA 影響分析
- Dashboard 聚合快照

Version: 1.1.0 — asyncio.gather 並行化 + git 安全封裝
Created: 2026-03-25
"""
import asyncio
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DigitalTwinService:
    """數位分身業務邏輯"""

    # ── Agent Topology ──────────────────────────────────────

    @staticmethod
    async def build_topology() -> Dict[str, Any]:
        """
        構建 Agent 組織圖 — 聚合 NemoClaw Registry + Missive Agent Roles

        Returns:
            {"nodes": [...], "edges": [...], "meta": {...}}
        """
        nodes: List[Dict] = []
        edges: List[Dict] = []

        # 1. NemoClaw 節點
        nodes.append({
            "id": "nemoclaw", "type": "leader",
            "label": "NemoClaw 監控塔",
            "description": "Gateway + Registry + Scheduler + Health Probe",
            "status": "unknown",
            "capabilities": ["gateway", "registry", "scheduler", "health_probe"],
            "project": "CK_NemoClaw",
        })

        # 2. OpenClaw 節點
        nodes.append({
            "id": "openclaw", "type": "engine",
            "label": "OpenClaw 通用引擎",
            "description": "Multi-Agent + Memory + Leader Agent 編排",
            "status": "unknown",
            "capabilities": ["reason", "delegate", "event_relay", "memory"],
            "project": "CK_OpenClaw",
        })
        edges.append({
            "source": "nemoclaw", "target": "openclaw",
            "label": "gateway → engine", "type": "delegation",
        })

        # 3. Missive Agent Roles
        try:
            from app.services.ai.agent.agent_roles import get_all_role_profiles
            for ctx, profile in get_all_role_profiles().items():
                node_id = f"missive-{ctx}"
                nodes.append({
                    "id": node_id, "type": "role",
                    "label": profile.identity,
                    "description": ", ".join(profile.capabilities[:4]),
                    "status": "active",
                    "capabilities": list(profile.capabilities),
                    "project": "CK_Missive", "context": ctx,
                })
                edges.append({
                    "source": "openclaw", "target": node_id,
                    "label": f"delegate → {ctx}", "type": "delegation",
                })
        except Exception as e:
            logger.warning("Failed to load agent roles: %s", e)

        # 4. 外部專案 Agent
        for agent in _EXTERNAL_AGENTS:
            nodes.append({
                "id": agent["id"], "type": "plugin",
                "label": agent["label"],
                "description": agent["description"],
                "status": "unknown",
                "capabilities": agent["capabilities"],
                "project": agent["project"],
                "triggers": agent.get("triggers", []),
            })
            edges.append({
                "source": "openclaw", "target": agent["id"],
                "label": f"delegate → {agent['id']}", "type": "delegation",
            })

        # 5. KG Hub 連線
        edges.append({
            "source": "ck-lvrland", "target": "missive-knowledge-graph",
            "label": "federated-contribute", "type": "data_flow",
        })
        edges.append({
            "source": "ck-tunnel", "target": "missive-knowledge-graph",
            "label": "federated-contribute", "type": "data_flow",
        })

        # 6. Registry 即時狀態
        try:
            from app.services.ai.federation.federation_client import get_federation_client
            client = get_federation_client()
            systems = client.list_available_systems()
            status_map = {s["id"]: s.get("status", "unknown") for s in systems}
            for node in nodes:
                nid = str(node["id"])
                if nid in status_map:
                    node["status"] = status_map[nid]
                elif nid.startswith("missive-"):
                    node["status"] = "active"
        except Exception as e:
            logger.debug("Registry status probe failed: %s", e)

        return {
            "nodes": nodes, "edges": edges,
            "meta": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }

    # ── QA Impact Analysis ──────────────────────────────────

    # 允許的 git branch 名稱 (防 command injection)
    _SAFE_BRANCH_RE = re.compile(r"^[a-zA-Z0-9._/\-]+$")

    @staticmethod
    async def analyze_qa_impact(base_branch: str = "main") -> Dict[str, Any]:
        """
        Diff-aware QA 影響分析 — git diff + 模組分類 + 風險評估

        Returns:
            {"success": bool, "affected": [...], "recommendation": str, ...}
        """
        # 驗證 branch 名稱（防 command injection）
        if not DigitalTwinService._SAFE_BRANCH_RE.match(base_branch):
            return {"success": False, "error": "Invalid branch name", "affected": []}

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"origin/{base_branch}"],
                cwd=project_root, capture_output=True, text=True, timeout=10,
            )
            changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        except Exception as e:
            return {"success": False, "error": f"Git diff failed: {e}", "affected": []}

        if not changed_files:
            return {
                "success": True, "changed_files_count": 0, "affected": [],
                "recommendation": "no_changes",
                "message": "沒有偵測到變更，無需 QA",
            }

        backend_changes = [f for f in changed_files if f.startswith("backend/")]
        frontend_changes = [f for f in changed_files if f.startswith("frontend/")]
        other_changes = [f for f in changed_files if not f.startswith(("backend/", "frontend/"))]

        affected_modules = _categorize_changes(backend_changes, frontend_changes)

        high_risk = sum(1 for m in affected_modules if m["risk"] == "high")
        has_migrations = any(m["category"] == "migrations" for m in affected_modules)
        has_model_changes = any(m["category"] == "models" for m in affected_modules)

        if has_migrations or has_model_changes:
            recommendation, message = "full_qa", "偵測到 DB 模型/遷移變更，建議執行完整 QA"
        elif high_risk >= 3:
            recommendation, message = "full_qa", f"偵測到 {high_risk} 個高風險模組變更，建議完整 QA"
        elif high_risk >= 1:
            recommendation, message = "diff_aware_qa", f"偵測到 {high_risk} 個高風險模組，建議 diff-aware QA"
        else:
            recommendation, message = "quick_qa", "僅低風險變更，快速 QA 即可"

        return {
            "success": True,
            "changed_files_count": len(changed_files),
            "affected": affected_modules,
            "recommendation": recommendation,
            "message": message,
            "summary": {
                "backend_changes": len(backend_changes),
                "frontend_changes": len(frontend_changes),
                "other_changes": len(other_changes),
                "high_risk_modules": high_risk,
                "has_migrations": has_migrations,
            },
            "suggested_commands": {
                "full": "/qa-smart full",
                "diff_aware": "/qa-smart",
                "quick": "/qa-smart quick",
            },
        }

    # ── Dashboard Snapshot ──────────────────────────────────

    _DASHBOARD_SOURCE_TIMEOUT = 3.0  # 每個資料源上限 3 秒

    @staticmethod
    async def get_dashboard_snapshot(db) -> Dict[str, Any]:
        """
        聚合分身狀態快照 — asyncio.gather 並行取得，每源 3s timeout

        Returns:
            {"profile": {...}, "capability": {...}, "daily": {...}, "health": {...}}
        """

        async def _safe(coro, label: str):
            """單源安全包裝：timeout + exception → None"""
            try:
                return await asyncio.wait_for(coro, timeout=DigitalTwinService._DASHBOARD_SOURCE_TIMEOUT)
            except Exception as e:
                logger.debug("Dashboard: %s unavailable: %s", label, e)
                return None

        async def _get_profile():
            from app.services.ai.agent.agent_self_profile import get_self_profile
            return await get_self_profile(db)

        async def _get_capability():
            from app.services.ai.agent.agent_capability_tracker import get_capability_profile
            return await get_capability_profile(db)

        async def _get_daily():
            from app.services.ai.agent.agent_mirror_feedback import generate_mirror_report
            return await generate_mirror_report(db)

        async def _get_quality():
            from app.repositories.agent_trace_repository import AgentTraceRepository
            return await AgentTraceRepository(db).get_quality_summary()

        async def _get_traces():
            from app.repositories.agent_trace_repository import AgentTraceRepository
            return await AgentTraceRepository(db).get_recent_traces(limit=5)

        async def _get_health():
            from app.services.ai.federation.federation_client import get_federation_client
            client = get_federation_client()
            systems = client.list_available_systems()
            return {
                "available": any(s["id"] in ("openclaw", "nemoclaw") for s in systems),
                "systems_count": len(systems),
            }

        profile, capability, daily, quality, traces, health = await asyncio.gather(
            _safe(_get_profile(), "self_profile"),
            _safe(_get_capability(), "capability_tracker"),
            _safe(_get_daily(), "mirror_feedback"),
            _safe(_get_quality(), "quality_stats"),
            _safe(_get_traces(), "recent_traces"),
            _safe(_get_health(), "gateway_health"),
        )

        return {
            "profile": profile,
            "capability": capability,
            "daily": daily,
            "quality": quality,
            "recent_traces": traces,
            "health": health or {"available": False, "systems_count": 0},
        }

    # ── Predictive Insights ────────────────────────────────

    @staticmethod
    async def get_predictive_insights() -> Dict[str, Any]:
        """
        智能洞察 — 基於歷史資料預測品質趨勢與工具健康風險

        Returns:
            {
                "quality_prediction": {"trend": "improving/stable/declining", "slope": float, "next_week_estimate": float},
                "tool_risks": [{"tool": str, "success_rate": float, "risk": "high/medium/low"}],
                "insights": [str],
            }
        """
        import json
        insights: List[str] = []
        quality_prediction: Dict[str, Any] = {"trend": "unknown", "slope": 0.0}
        tool_risks: List[Dict[str, Any]] = []

        # 1. 品質趨勢預測 (基於 eval_history 線性迴歸)
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                raw = await redis.lrange("agent:evolution:eval_history", 0, 99)
                if raw and len(raw) >= 5:
                    records = [json.loads(r) for r in raw]
                    scores = [r.get("overall", 0.5) for r in records]

                    # 簡易線性迴歸斜率
                    n = len(scores)
                    x_mean = (n - 1) / 2
                    y_mean = sum(scores) / n
                    numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
                    denominator = sum((i - x_mean) ** 2 for i in range(n))
                    slope = numerator / denominator if denominator > 0 else 0.0

                    current_avg = sum(scores[:10]) / min(len(scores), 10)
                    next_week_est = min(max(current_avg + slope * 7, 0.0), 1.0)

                    if slope > 0.005:
                        trend = "improving"
                        insights.append(f"品質呈上升趨勢 (斜率 +{slope:.4f})，預測下週平均分 {next_week_est:.2f}")
                    elif slope < -0.005:
                        trend = "declining"
                        insights.append(f"品質呈下降趨勢 (斜率 {slope:.4f})，建議檢視最近的進化動作")
                    else:
                        trend = "stable"
                        insights.append(f"品質穩定 (平均 {current_avg:.2f})")

                    quality_prediction = {"trend": trend, "slope": round(slope, 5), "current_avg": round(current_avg, 3), "next_week_estimate": round(next_week_est, 3), "sample_count": n}
                else:
                    insights.append("品質歷史資料不足 (需 5+ 筆)，暫無法預測")
        except Exception as e:
            logger.debug("Predictive quality failed: %s", e)

        # 2. 工具降級預警 (基於 tool_monitor 成功率)
        try:
            from app.services.ai.agent.agent_tool_monitor import AgentToolMonitor
            monitor = AgentToolMonitor()
            all_stats = await monitor.get_all_stats()
            degraded = await monitor.get_degraded_tools()

            for tool_name, stats in all_stats.items():
                rate = stats.recent_success_rate
                if tool_name in degraded:
                    tool_risks.append({"tool": tool_name, "success_rate": round(rate, 3), "risk": "critical", "status": "degraded"})
                    insights.append(f"工具 {tool_name} 已降級 (成功率 {rate:.0%})，需要檢修")
                elif rate < 0.5:
                    tool_risks.append({"tool": tool_name, "success_rate": round(rate, 3), "risk": "high", "status": "warning"})
                    insights.append(f"工具 {tool_name} 成功率偏低 ({rate:.0%})，可能即將降級")
                elif rate < 0.7:
                    tool_risks.append({"tool": tool_name, "success_rate": round(rate, 3), "risk": "medium", "status": "watch"})

            tool_risks.sort(key=lambda t: t["success_rate"])
        except Exception as e:
            logger.debug("Predictive tool risks failed: %s", e)

        # 3. 進化信號摘要
        try:
            from app.core.redis_client import get_redis
            redis = await get_redis()
            if redis:
                signal_count = await redis.llen("agent:evolution:signals")
                if signal_count > 20:
                    insights.append(f"待處理進化信號 {signal_count} 個，下次進化排程將處理")
                elif signal_count > 0:
                    insights.append(f"{signal_count} 個進化信號排隊中")
        except Exception:
            pass

        if not insights:
            insights.append("系統運行正常，暫無特殊洞察")

        return {
            "quality_prediction": quality_prediction,
            "tool_risks": tool_risks,
            "insights": insights,
        }


# ── Constants ───────────────────────────────────────────────

_EXTERNAL_AGENTS = [
    {
        "id": "ck-lvrland", "label": "地政圖資引擎",
        "description": "地籍查詢, 公告現值, 都更, 空間分析",
        "capabilities": ["map_rendering", "spatial_analysis", "land_query"],
        "project": "CK_lvrland_Webmap",
        "triggers": ["地圖", "測繪", "圖資", "地籍", "土地"],
    },
    {
        "id": "ck-tunnel", "label": "隧道監測引擎",
        "description": "裂縫偵測, 感測器監控, 點雲分析",
        "capabilities": ["sensor_monitoring", "crack_detection", "alert_management"],
        "project": "CK_DigitalTunnel",
        "triggers": ["隧道", "感測", "監控", "裂縫"],
    },
]


def _categorize_changes(
    backend_changes: List[str], frontend_changes: List[str],
) -> List[Dict[str, Any]]:
    """將變更檔案分類為模組影響"""
    affected: List[Dict[str, Any]] = []

    be_cats = {"api": [], "services": [], "models": [], "schemas": [],
               "migrations": [], "tests": [], "config": []}
    for f in backend_changes:
        if "/api/endpoints/" in f: be_cats["api"].append(f)
        elif "/services/" in f: be_cats["services"].append(f)
        elif "/models/" in f: be_cats["models"].append(f)
        elif "/schemas/" in f: be_cats["schemas"].append(f)
        elif "/alembic/" in f: be_cats["migrations"].append(f)
        elif "/tests/" in f: be_cats["tests"].append(f)
        else: be_cats["config"].append(f)

    for cat, files in be_cats.items():
        if files:
            affected.append({
                "layer": "backend", "category": cat,
                "files": files[:10], "count": len(files),
                "risk": "high" if cat in ("models", "migrations", "api") else "medium",
            })

    fe_cats = {"pages": [], "components": [], "hooks": [], "api": [],
               "types": [], "tests": [], "config": []}
    for f in frontend_changes:
        if "/pages/" in f: fe_cats["pages"].append(f)
        elif "/components/" in f: fe_cats["components"].append(f)
        elif "/hooks/" in f: fe_cats["hooks"].append(f)
        elif "/api/" in f: fe_cats["api"].append(f)
        elif "/types/" in f: fe_cats["types"].append(f)
        elif "/__tests__/" in f or ".test." in f: fe_cats["tests"].append(f)
        else: fe_cats["config"].append(f)

    for cat, files in fe_cats.items():
        if files:
            affected.append({
                "layer": "frontend", "category": cat,
                "files": files[:10], "count": len(files),
                "risk": "high" if cat in ("pages", "api", "types") else "medium",
            })

    return affected
