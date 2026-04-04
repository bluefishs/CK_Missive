# -*- coding: utf-8 -*-
"""
Digital Twin 端點單元測試
Digital Twin API Endpoints Unit Tests

測試 ai/digital_twin.py 的核心端點邏輯

執行方式:
    pytest tests/unit/test_services/test_digital_twin_endpoints.py -v
"""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.api.endpoints.ai.digital_twin import (
    _validate_job_id,
    _sse_event,
    agent_topology,
    qa_impact_analysis,
    digital_twin_health,
    _proxy_task_action,
)


# ============================================================================
# _validate_job_id 測試
# ============================================================================

class TestValidateJobId:
    """Job ID 格式驗證"""

    @pytest.mark.parametrize("job_id", [
        "abc123",
        "job-001",
        "task_v2",
        "A" * 64,
    ])
    def test_valid_job_ids(self, job_id):
        assert _validate_job_id(job_id) == job_id

    @pytest.mark.parametrize("job_id", [
        "../../../etc/passwd",
        "job/../../",
        "",
        "a" * 65,
        "job id with spaces",
        "job;rm -rf",
        "job\nid",
    ])
    def test_invalid_job_ids(self, job_id):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_job_id(job_id)
        assert exc_info.value.status_code == 400


# ============================================================================
# _sse_event 測試
# ============================================================================

class TestSSEEvent:
    """SSE 事件格式化"""

    def test_basic_event(self):
        result = _sse_event({"type": "status", "message": "test"})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        parsed = json.loads(result[6:].strip())
        assert parsed["type"] == "status"

    def test_chinese_characters(self):
        result = _sse_event({"type": "token", "token": "中文測試"})
        assert "中文測試" in result

    def test_ensure_ascii_false(self):
        result = _sse_event({"message": "桃園市政府"})
        assert "桃園市政府" in result
        assert "\\u" not in result


# ============================================================================
# agent_topology 測試
# ============================================================================

class TestAgentTopology:
    """Agent 組織圖"""

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.username = "admin"
        return user

    @pytest.mark.asyncio
    @patch("app.services.ai.federation_client.get_federation_client")
    @patch("app.services.ai.agent_roles.get_all_role_profiles")
    async def test_topology_structure(self, mock_roles, mock_fed, mock_user):
        # Mock agent roles
        role_profile = MagicMock()
        role_profile.identity = "乾坤公文助手"
        role_profile.capabilities = ["搜尋", "摘要", "分析", "建議"]
        mock_roles.return_value = {"ck-doc": role_profile}

        # Mock federation client
        client = MagicMock()
        client.list_available_systems.return_value = []
        mock_fed.return_value = client

        result = await agent_topology(_current_user=mock_user)

        assert "nodes" in result
        assert "edges" in result
        assert "meta" in result
        assert result["meta"]["total_nodes"] > 0

        # 基本節點存在
        node_ids = [n["id"] for n in result["nodes"]]
        assert "nemoclaw" in node_ids
        assert "openclaw" in node_ids
        assert "missive-ck-doc" in node_ids

    @pytest.mark.asyncio
    async def test_topology_without_roles(self):
        """即使 agent_roles 載入失敗也不應崩潰"""
        mock_user = MagicMock()
        mock_user.username = "admin"

        with patch(
            "app.services.ai.agent_roles.get_all_role_profiles",
            side_effect=ImportError("not found"),
        ):
            with patch(
                "app.services.ai.federation_client.get_federation_client",
                side_effect=Exception("offline"),
            ):
                result = await agent_topology(_current_user=mock_user)

        # 至少有固定節點
        assert len(result["nodes"]) >= 2  # nemoclaw + openclaw
        assert result["meta"]["total_nodes"] >= 2


# ============================================================================
# qa_impact_analysis 測試
# ============================================================================

class TestQAImpactAnalysis:
    """Diff-aware QA 影響分析"""

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.username = "admin"
        return user

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_no_changes(self, mock_run, mock_user):
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        result = await qa_impact_analysis(base_branch="main", _current_user=mock_user)

        assert result["success"] is True
        assert result["recommendation"] == "no_changes"

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_high_risk_migration(self, mock_run, mock_user):
        mock_run.return_value = MagicMock(
            stdout="backend/alembic/versions/new_migration.py\nbackend/app/extended/models/core.py\n",
            returncode=0,
        )

        result = await qa_impact_analysis(base_branch="main", _current_user=mock_user)

        assert result["success"] is True
        assert result["recommendation"] == "full_qa"
        assert result["summary"]["has_migrations"] is True

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_frontend_only_changes(self, mock_run, mock_user):
        mock_run.return_value = MagicMock(
            stdout="frontend/src/components/test.tsx\n",
            returncode=0,
        )

        result = await qa_impact_analysis(base_branch="main", _current_user=mock_user)

        assert result["success"] is True
        assert result["summary"]["frontend_changes"] == 1
        assert result["summary"]["backend_changes"] == 0

    @pytest.mark.asyncio
    @patch("subprocess.run", side_effect=Exception("git not found"))
    async def test_git_error(self, mock_run, mock_user):
        result = await qa_impact_analysis(base_branch="main", _current_user=mock_user)

        assert result["success"] is False
        assert "Git diff failed" in result["error"]


# ============================================================================
# digital_twin_health 測試
# ============================================================================

class TestDigitalTwinHealth:
    """健康檢查"""

    @pytest.mark.asyncio
    @patch("app.services.ai.federation_client.get_federation_client")
    @patch("app.services.ai.agent_roles.get_all_role_profiles", return_value={"ck-doc": MagicMock()})
    async def test_healthy(self, mock_roles, mock_fed):
        client = MagicMock()
        client.list_available_systems.return_value = [
            {"id": "openclaw", "status": "active"},
        ]
        mock_fed.return_value = client

        result = await digital_twin_health()

        assert result["local_agent"] is True
        assert result["gateway_available"] is True
        assert result["local_roles_count"] >= 1

    @pytest.mark.asyncio
    @patch("app.services.ai.federation_client.get_federation_client",
           side_effect=Exception("connection refused"))
    @patch("app.services.ai.agent_roles.get_all_role_profiles", return_value={})
    async def test_unhealthy_gateway(self, mock_roles, mock_fed):
        result = await digital_twin_health()

        assert result["local_agent"] is True  # 本地永遠可用
        assert result["gateway_available"] is False
        assert "gateway_error" in result


# ============================================================================
# _proxy_task_action 測試
# ============================================================================

class TestProxyTaskAction:
    """任務代理操作"""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NEMOCLAW_GATEWAY_URL": "http://localhost:9000", "MCP_SERVICE_TOKEN": "test"})
    @patch("httpx.AsyncClient")
    async def test_approve_success(self, MockClient):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value = mock_client_instance

        result = await _proxy_task_action("job-1", "approve", {"approved_by": "admin"})

        assert result["success"] is True

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NEMOCLAW_GATEWAY_URL": "http://localhost:9000"})
    @patch("httpx.AsyncClient")
    async def test_proxy_upstream_error(self, MockClient):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value = mock_client_instance

        result = await _proxy_task_action("job-1", "approve", {})

        # _proxy_task_action now returns JSONResponse
        import json
        body = json.loads(result.body.decode())
        assert body["success"] is False
        assert "HTTP 500" in body["error"]
