# -*- coding: utf-8 -*-
"""
系統健康檢查服務單元測試

測試 SystemHealthService 的各項檢查邏輯。
使用 Mock 資料庫和外部服務，不需要實際連線。

執行方式:
    pytest tests/unit/test_services/test_system_health_service.py -v
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession


# =========================================================================
# Mock 工廠
# =========================================================================

def make_mock_db() -> MagicMock:
    """建立標準 Mock DB session"""
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


# =========================================================================
# 啟動時間與運行時間
# =========================================================================

class TestStartupTimeAndUptime:
    """測試啟動時間設定與運行時間計算"""

    def test_set_startup_time(self):
        """設定啟動時間"""
        from app.services.system_health_service import SystemHealthService

        SystemHealthService._startup_time = None
        SystemHealthService.set_startup_time()

        assert SystemHealthService._startup_time is not None
        assert isinstance(SystemHealthService._startup_time, datetime)

    def test_get_uptime_when_set(self):
        """啟動時間已設定時回傳格式化字串"""
        from app.services.system_health_service import SystemHealthService

        SystemHealthService._startup_time = datetime.now() - timedelta(hours=2, minutes=30, seconds=15)

        uptime = SystemHealthService.get_uptime()
        assert "2h 30m 15s" == uptime

    def test_get_uptime_when_not_set(self):
        """啟動時間未設定時回傳 unknown"""
        from app.services.system_health_service import SystemHealthService

        SystemHealthService._startup_time = None
        uptime = SystemHealthService.get_uptime()
        assert uptime == "unknown"


# =========================================================================
# 資料庫檢查
# =========================================================================

class TestDatabaseCheck:
    """測試資料庫連線檢查"""

    @pytest.mark.asyncio
    async def test_database_healthy(self):
        """資料庫正常連線"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        service = SystemHealthService(db)

        result = await service.check_database()

        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert result["response_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_database_unhealthy(self):
        """資料庫連線失敗"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        db.execute = AsyncMock(side_effect=Exception("Connection refused"))
        service = SystemHealthService(db)

        result = await service.check_database()

        assert result["status"] == "unhealthy"
        assert "error" in result


# =========================================================================
# 連線池檢查
# =========================================================================

class TestConnectionPoolCheck:
    """測試連線池狀態檢查"""

    @patch("app.services.system_health_service.engine")
    def test_pool_healthy(self, mock_engine):
        """連線池正常"""
        from app.services.system_health_service import SystemHealthService

        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 0
        mock_pool.checkedin.return_value = 7
        mock_engine.pool = mock_pool

        result = SystemHealthService.check_connection_pool()

        assert result["status"] == "healthy"
        assert result["utilization_percent"] == 30.0
        assert result["pool_info"]["size"] == 10
        assert result["pool_info"]["checked_out"] == 3

    @patch("app.services.system_health_service.engine")
    def test_pool_zero_size(self, mock_engine):
        """連線池大小為 0 時不除零"""
        from app.services.system_health_service import SystemHealthService

        mock_pool = MagicMock()
        mock_pool.size.return_value = 0
        mock_pool.checkedout.return_value = 0
        mock_pool.overflow.return_value = 0
        mock_pool.checkedin.return_value = 0
        mock_engine.pool = mock_pool

        result = SystemHealthService.check_connection_pool()

        assert result["status"] == "healthy"
        assert result["utilization_percent"] == 0

    @patch("app.services.system_health_service.engine")
    def test_pool_check_failure(self, mock_engine):
        """連線池檢查失敗"""
        from app.services.system_health_service import SystemHealthService

        mock_engine.pool = MagicMock(side_effect=Exception("Pool error"))
        mock_engine.pool.size.side_effect = Exception("Pool error")

        result = SystemHealthService.check_connection_pool()

        assert result["status"] == "unknown"


# =========================================================================
# 系統資源檢查
# =========================================================================

class TestSystemResourcesCheck:
    """測試系統資源檢查"""

    @patch("app.services.system_health_service.psutil")
    def test_resources_healthy(self, mock_psutil):
        """系統資源正常"""
        from app.services.system_health_service import SystemHealthService

        mock_memory = MagicMock()
        mock_memory.percent = 65.0
        mock_memory.available = 8 * 1024**3  # 8 GB
        mock_memory.total = 16 * 1024**3     # 16 GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk.free = 200 * 1024**3      # 200 GB
        mock_disk.total = 500 * 1024**3     # 500 GB
        mock_psutil.disk_usage.return_value = mock_disk

        result = SystemHealthService.check_system_resources()

        assert result["status"] == "healthy"
        assert result["memory"]["used_percent"] == 65.0
        assert result["disk"]["used_percent"] == 50.0

    @patch("app.services.system_health_service.psutil")
    def test_resources_high_memory_warning(self, mock_psutil):
        """記憶體使用過高時顯示警告"""
        from app.services.system_health_service import SystemHealthService

        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_memory.available = 1 * 1024**3
        mock_memory.total = 16 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk.free = 200 * 1024**3
        mock_disk.total = 500 * 1024**3
        mock_psutil.disk_usage.return_value = mock_disk

        result = SystemHealthService.check_system_resources()

        assert result["status"] == "warning"
        assert "High memory usage" in result["warnings"]

    @patch("app.services.system_health_service.psutil")
    def test_resources_high_disk_warning(self, mock_psutil):
        """磁碟使用過高時顯示警告"""
        from app.services.system_health_service import SystemHealthService

        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 8 * 1024**3
        mock_memory.total = 16 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.percent = 95.0
        mock_disk.free = 25 * 1024**3
        mock_disk.total = 500 * 1024**3
        mock_psutil.disk_usage.return_value = mock_disk

        result = SystemHealthService.check_system_resources()

        assert result["status"] == "warning"
        assert "High disk usage" in result["warnings"]

    @patch("app.services.system_health_service.psutil")
    def test_resources_both_warnings(self, mock_psutil):
        """記憶體和磁碟都過高"""
        from app.services.system_health_service import SystemHealthService

        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_memory.available = 1 * 1024**3
        mock_memory.total = 16 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.percent = 95.0
        mock_disk.free = 25 * 1024**3
        mock_disk.total = 500 * 1024**3
        mock_psutil.disk_usage.return_value = mock_disk

        result = SystemHealthService.check_system_resources()

        assert result["status"] == "warning"
        assert len(result["warnings"]) == 2


# =========================================================================
# 效能建議
# =========================================================================

class TestPerformanceRecommendations:
    """測試效能優化建議"""

    def test_all_queries_fast(self):
        """所有查詢正常時無優化建議"""
        from app.services.system_health_service import SystemHealthService

        metrics = {
            "simple_count": {"execution_time_ms": 5.0, "status": "success"},
            "complex_join": {"execution_time_ms": 50.0, "status": "success"},
            "aggregation": {"execution_time_ms": 100.0, "status": "success"},
        }

        recommendations = SystemHealthService.get_performance_recommendations(metrics)
        assert len(recommendations) == 1
        assert "良好" in recommendations[0]

    def test_slow_query_warning(self):
        """慢查詢 (500-1000ms) 顯示優化建議"""
        from app.services.system_health_service import SystemHealthService

        metrics = {
            "simple_count": {"execution_time_ms": 5.0, "status": "success"},
            "complex_join": {"execution_time_ms": 750.0, "status": "success"},
        }

        recommendations = SystemHealthService.get_performance_recommendations(metrics)
        assert any("進一步優化" in r for r in recommendations)

    def test_very_slow_query_critical(self):
        """非常慢的查詢 (>1000ms) 建議加索引"""
        from app.services.system_health_service import SystemHealthService

        metrics = {
            "complex_join": {"execution_time_ms": 2000.0, "status": "success"},
        }

        recommendations = SystemHealthService.get_performance_recommendations(metrics)
        assert any("索引" in r for r in recommendations)

    def test_error_query_no_recommendation(self):
        """錯誤查詢不產生建議"""
        from app.services.system_health_service import SystemHealthService

        metrics = {
            "simple_count": {"execution_time_ms": None, "status": "error"},
        }

        recommendations = SystemHealthService.get_performance_recommendations(metrics)
        assert len(recommendations) == 1
        assert "良好" in recommendations[0]


# =========================================================================
# 資料品質檢查
# =========================================================================

class TestDataQualityCheck:
    """測試資料品質檢查"""

    @pytest.mark.asyncio
    async def test_data_quality_healthy(self):
        """資料品質良好"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        service = SystemHealthService(db)

        # Mock main query
        main_row = MagicMock()
        main_row.total = 100
        main_row.norm_sender = 95
        main_row.norm_receiver = 92
        main_row.sender_fk = 95
        main_row.receiver_fk = 93

        # Mock NER query
        ner_row = MagicMock()
        ner_row.total_docs = 100
        ner_row.ner_docs = 80

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.one.return_value = main_row
            else:
                result.one.return_value = ner_row
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await service.check_data_quality()

        assert result["status"] == "healthy"
        assert result["total_documents"] == 100
        assert result["agency_fk"]["sender_pct"] == 95.0
        assert result["ner_coverage_pct"] == 80.0

    @pytest.mark.asyncio
    async def test_data_quality_warning(self):
        """FK 覆蓋率低於 90% 時為 warning"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        service = SystemHealthService(db)

        main_row = MagicMock()
        main_row.total = 100
        main_row.norm_sender = 80
        main_row.norm_receiver = 75
        main_row.sender_fk = 85
        main_row.receiver_fk = 80

        ner_row = MagicMock()
        ner_row.total_docs = 100
        ner_row.ner_docs = 50

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.one.return_value = main_row
            else:
                result.one.return_value = ner_row
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await service.check_data_quality()

        assert result["status"] == "warning"

    @pytest.mark.asyncio
    async def test_data_quality_unhealthy(self):
        """FK 覆蓋率低於 70% 時為 unhealthy"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        service = SystemHealthService(db)

        main_row = MagicMock()
        main_row.total = 100
        main_row.norm_sender = 50
        main_row.norm_receiver = 40
        main_row.sender_fk = 60
        main_row.receiver_fk = 55

        ner_row = MagicMock()
        ner_row.total_docs = 100
        ner_row.ner_docs = 20

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.one.return_value = main_row
            else:
                result.one.return_value = ner_row
            return result

        db.execute = AsyncMock(side_effect=mock_execute)

        result = await service.check_data_quality()

        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_data_quality_error(self):
        """查詢失敗時回傳 error"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        db.execute = AsyncMock(side_effect=Exception("DB error"))
        service = SystemHealthService(db)

        result = await service.check_data_quality()

        assert result["status"] == "error"


# =========================================================================
# 備份狀態檢查
# =========================================================================

class TestBackupStatusCheck:
    """測試備份狀態檢查"""

    @patch("app.services.system_health_service.SystemHealthService.check_backup_status")
    def test_backup_healthy(self, mock_check):
        """備份正常"""
        mock_check.return_value = {
            "status": "healthy",
            "scheduler_running": True,
            "consecutive_failures": 0,
            "last_backup": datetime.now().isoformat(),
        }

        result = mock_check()
        assert result["status"] == "healthy"
        assert result["scheduler_running"] is True

    @patch("app.services.system_health_service.SystemHealthService.check_backup_status")
    def test_backup_warning_failures(self, mock_check):
        """備份有失敗記錄"""
        mock_check.return_value = {
            "status": "warning",
            "scheduler_running": True,
            "consecutive_failures": 2,
            "warnings": ["最近備份失敗 2 次"],
        }

        result = mock_check()
        assert result["status"] == "warning"
        assert result["consecutive_failures"] == 2


# =========================================================================
# 就緒檢查
# =========================================================================

class TestReadinessCheck:
    """測試就緒檢查"""

    @pytest.mark.asyncio
    async def test_readiness_success(self):
        """就緒檢查成功"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        service = SystemHealthService(db)

        result = await service.check_readiness()
        assert result is True

    @pytest.mark.asyncio
    async def test_readiness_failure(self):
        """就緒檢查失敗"""
        from app.services.system_health_service import SystemHealthService

        db = make_mock_db()
        db.execute = AsyncMock(side_effect=Exception("Not ready"))
        service = SystemHealthService(db)

        with pytest.raises(Exception, match="Not ready"):
            await service.check_readiness()


# =========================================================================
# 向後相容函數
# =========================================================================

class TestBackwardCompatFunctions:
    """測試向後相容模組級函數"""

    def test_set_startup_time_function(self):
        """模組級 set_startup_time 委託至類別"""
        from app.services.system_health_service import set_startup_time, SystemHealthService

        SystemHealthService._startup_time = None
        set_startup_time()
        assert SystemHealthService._startup_time is not None

    def test_get_uptime_function(self):
        """模組級 get_uptime 委託至類別"""
        from app.services.system_health_service import get_uptime, SystemHealthService

        SystemHealthService._startup_time = datetime.now() - timedelta(minutes=5)
        uptime = get_uptime()
        assert "0h 5m" in uptime
