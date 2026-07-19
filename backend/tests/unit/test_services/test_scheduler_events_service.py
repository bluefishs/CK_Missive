"""SchedulerEventsService 聚合純函式 TDD（DDD 標準化抽取行為保真）。"""
from app.services.system.scheduler_events_service import SchedulerEventsService


class TestAggregateStats:
    def test_groups_by_job_and_computes_rates(self):
        events = [
            {"job_id": "a", "status": "success", "duration_ms": 100},
            {"job_id": "a", "status": "success", "duration_ms": 200},
            {"job_id": "a", "status": "failure", "duration_ms": 0},
            {"job_id": "b", "status": "success", "duration_ms": 50},
        ]
        out = SchedulerEventsService.aggregate_stats(events)
        assert out["total_events"] == 4
        assert out["total_jobs"] == 2
        # 依 total_count 降序 → a(3) 在 b(1) 前
        a = out["jobs"][0]
        assert a["job_id"] == "a"
        assert a["success_count"] == 2 and a["failure_count"] == 1
        assert a["total_count"] == 3
        assert a["success_rate_pct"] == round(2 / 3 * 100, 1)
        assert a["avg_duration_ms"] == 100.0  # (100+200+0)/3

    def test_empty_events(self):
        out = SchedulerEventsService.aggregate_stats([])
        assert out == {"jobs": [], "total_events": 0, "total_jobs": 0}

    def test_missing_job_id_bucketed_unknown(self):
        out = SchedulerEventsService.aggregate_stats([{"status": "success"}])
        assert out["jobs"][0]["job_id"] == "unknown"
