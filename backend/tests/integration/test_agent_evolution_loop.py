# -*- coding: utf-8 -*-
"""
Agent 自主進化閉環整合測試（scaffold）

目標：驗證 orchestrator → self_evaluator → evolution_scheduler →
     agent_learning 持久化 → planner inject 的完整鏈路，
     而不是單元層的 mock。

覆蓋鏈路：
  1. 模擬低 readiness 的 domain query → orchestrator 走 agent 路徑
  2. self_evaluator 產生 CRITICAL → 寫入 Redis 5min TTL
  3. evolution_scheduler 讀取 CRITICAL → 觸發 promote
  4. AgentLearning 寫入 DB → 下次 planner 查詢時被 inject
  5. 驗證第二次查詢的行為因 pattern 注入而改變

標記 @pytest.mark.xfail 的 case 為「目前已知但尚未驗證」的陷阱點，
由本 scaffold 追蹤 — 實作完成後移除 xfail。

Version: 0.1.0 (scaffold)
Created: 2026-04-14
Owner: P1 — 依 MEMORY Pending Work Queue
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# --------------------------------------------------------------------------
# Fixtures（待補）
# --------------------------------------------------------------------------
@pytest.fixture
async def fresh_redis():
    """清空 agent:* / evolution:* key，確保 test isolation。

    TODO: 連線 REDIS_URL，DELETE agent:shared_pool / evolution:critical:*
    """
    pytest.skip("fixture not implemented — 請先接上 Redis fixture")


@pytest.fixture
async def seed_low_readiness_domain(fresh_redis):
    """灌一個 readiness<0.5 的 domain 進 capability tracker。"""
    pytest.skip("fixture not implemented — 需 AgentCapabilityTracker seed API")


@pytest.fixture
async def orchestrator_with_real_evaluator():
    """orchestrator + 真實 self_evaluator（不 mock），但工具層 stub。"""
    pytest.skip("fixture not implemented — 需拆 tool executor 的測試替身")


# --------------------------------------------------------------------------
# 鏈路 1: CRITICAL → Redis → Planner 讀取
# --------------------------------------------------------------------------
class TestCriticalFeedbackLoop:
    async def test_critical_evaluation_writes_to_redis(self, orchestrator_with_real_evaluator):
        """self_evaluator.severity=critical 應寫入 evolution:critical:{domain} 5min TTL。"""
        pytest.xfail("待接上 evaluator 測試介面")

    async def test_planner_reads_critical_within_ttl(self, seed_low_readiness_domain):
        """planner 在 TTL 內讀到 CRITICAL 應調整策略（例如強制 agent 路徑）。"""
        pytest.xfail("待 planner 提供 inspection hook")

    async def test_critical_expires_after_ttl(self):
        """超過 5min 後 key 應自動過期，planner 回歸 baseline。"""
        pytest.xfail("需可控時鐘（freezegun）")


# --------------------------------------------------------------------------
# 鏈路 2: Evolution → AgentLearning 持久化 → Inject
# --------------------------------------------------------------------------
class TestEvolutionPersistence:
    async def test_promote_pattern_writes_to_db(self, fresh_redis):
        """evolution_scheduler.promote() 應寫入 AgentLearning 表。"""
        pytest.xfail("待接 DB fixture")

    async def test_learning_injector_picks_up_new_pattern(self):
        """下一次 planner 查詢應看到新 pattern 被注入。"""
        pytest.xfail("需 planner prompt snapshot diff")

    async def test_chronic_pattern_isolation(self):
        """同一 domain 連續 3 次 CRITICAL → 應被標記 chronic 並隔離，不再自動 promote。"""
        pytest.xfail("chronic 判斷邏輯待驗證閾值")


# --------------------------------------------------------------------------
# 鏈路 3: 自動回滾
# --------------------------------------------------------------------------
class TestAutoRollback:
    async def test_degraded_pattern_triggers_rollback(self):
        """新 pattern 7 天內使 domain readiness 下降 → 應自動 rollback。"""
        pytest.xfail("baseline→7天比較需時間窗 fixture")

    async def test_rollback_restores_previous_pattern(self):
        """rollback 後 AgentLearning 該 pattern 狀態應為 rolled_back。"""
        pytest.xfail("待 AgentLearning 欄位 status 上線")


# --------------------------------------------------------------------------
# 鏈路 4: Shared Pool 跨 session 可用
# --------------------------------------------------------------------------
class TestSharedPool:
    async def test_learning_available_across_sessions(self):
        """session A 學到的 pattern，session B 應能即時讀到。"""
        pytest.xfail("需 mock 兩個 session context")


# --------------------------------------------------------------------------
# 鏈路 5: Domain-aware 權重
# --------------------------------------------------------------------------
class TestDomainAwareWeights:
    @pytest.mark.parametrize("domain", ["tender", "graph", "doc", "sales", "field"])
    async def test_domain_specific_evaluation_weights(self, domain):
        """不同 domain 的評估權重應來自 agent-policy.yaml，而非硬編碼。"""
        pytest.xfail(f"{domain} 權重對照表待補")


# --------------------------------------------------------------------------
# 煙霧測試（先通這一個再說）
# --------------------------------------------------------------------------
class TestSmoke:
    async def test_scaffold_importable(self):
        """至少確保本檔能被 pytest collect，不爆 import error。"""
        from backend.app.services.ai.agent import agent_orchestrator  # noqa
        from backend.app.services.ai.agent import agent_evolution_scheduler  # noqa
        assert True
