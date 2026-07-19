"""Scheduler Events Service（DDD 標準化，2026-07-20）

異質同工/標準化收斂：原 endpoints/scheduler_events.py 在端點內直讀 cron_events.jsonl
+ in-endpoint 聚合，繞過 service 層（治理端點標準化盲區）。抽出本 service 封裝
「讀 jsonl / 聚合統計 / 列覆盤報告」邏輯，端點改薄委派。行為保真。

資料源：CK_LOGS_DIR/cron_events.jsonl（cron @tracked_job 寫入）、
       wiki/memory/self-retrospective-reports/*.md（每日覆盤 cron 產出）。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SchedulerEventsService:
    """Cron 執行事件與覆盤報告的讀取/聚合（純檔案讀取，無 DB）。"""

    def __init__(self) -> None:
        self._logs_dir = Path(os.getenv("CK_LOGS_DIR", "/app/logs"))
        self._wiki_memory_dir = Path(os.getenv("CK_PROJECT_ROOT", "/app")) / "wiki" / "memory"

    # ── 內部 ──────────────────────────────────────────────────────
    @property
    def events_log(self) -> Path:
        return self._logs_dir / "cron_events.jsonl"

    @property
    def reports_dir(self) -> Path:
        return self._wiki_memory_dir / "self-retrospective-reports"

    def _read_event_lines(self) -> List[str]:
        log = self.events_log
        if not log.exists():
            return []
        return log.read_text(encoding="utf-8").splitlines()

    @staticmethod
    def aggregate_stats(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """依 job_id 分組聚合成功/失敗率與平均耗時（純函式，可測）。"""
        stats: Dict[str, Dict[str, Any]] = {}
        for ev in events:
            job = ev.get("job_id", "unknown")
            s = stats.setdefault(job, {
                "success": 0, "failure": 0, "total_duration_ms": 0, "last_event": None,
            })
            if ev.get("status") == "success":
                s["success"] += 1
            elif ev.get("status") == "failure":
                s["failure"] += 1
            s["total_duration_ms"] += ev.get("duration_ms", 0) or 0
            s["last_event"] = ev

        result = []
        for job, s in stats.items():
            total = s["success"] + s["failure"]
            avg_ms = (s["total_duration_ms"] / total) if total else 0
            success_rate = (s["success"] / total * 100) if total else 0
            result.append({
                "job_id": job,
                "success_count": s["success"],
                "failure_count": s["failure"],
                "total_count": total,
                "success_rate_pct": round(success_rate, 1),
                "avg_duration_ms": round(avg_ms, 1),
                "last_event": s["last_event"],
            })
        result.sort(key=lambda x: x["total_count"], reverse=True)
        return {
            "jobs": result,
            "total_events": sum(j["total_count"] for j in result),
            "total_jobs": len(result),
        }

    # ── 公開 API ──────────────────────────────────────────────────
    def get_events(
        self, limit: int = 100, job_id: Optional[str] = None, status: Optional[str] = None,
    ) -> Dict[str, Any]:
        log = self.events_log
        if not log.exists():
            return {"events": [], "total": 0, "file": str(log)}
        events = []
        for line in self._read_event_lines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if job_id and ev.get("job_id") != job_id:
                continue
            if status and ev.get("status") != status:
                continue
            events.append(ev)
        return {
            "events": events[-limit:][::-1],  # 反序最新在前
            "total": len(events),
            "file": str(log),
            "filter": {"job_id": job_id, "status": status, "limit": limit},
        }

    def get_events_stats(self) -> Dict[str, Any]:
        if not self.events_log.exists():
            return {"jobs": [], "total_events": 0}
        events = []
        for line in self._read_event_lines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return self.aggregate_stats(events)

    def list_reports(self, limit: int = 30) -> Dict[str, Any]:
        rdir = self.reports_dir
        if not rdir.is_dir():
            return {"reports": [], "total": 0, "dir": str(rdir)}
        reports = []
        for f in sorted(rdir.glob("*.md"), reverse=True)[:limit]:
            try:
                stat = f.stat()
                text = f.read_text(encoding="utf-8", errors="ignore")[:3000]
                overall = "UNKNOWN"
                for line in text.splitlines()[:20]:
                    if "**Overall**" in line:
                        overall = line.split(":")[-1].strip().rstrip("*").strip()
                        break
                reports.append({
                    "date": f.stem,
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "overall": overall,
                    "summary": text[:500],
                })
            except Exception:
                continue
        return {"reports": reports, "total": len(reports), "dir": str(rdir)}

    def get_report(self, date: str) -> Optional[Dict[str, Any]]:
        """回傳 {date, markdown, json?}；md 不存在回 None（端點轉 404）。"""
        rdir = self.reports_dir
        md_file = rdir / f"{date}.md"
        json_file = rdir / f"{date}.json"
        if not md_file.exists():
            return None
        result: Dict[str, Any] = {
            "date": date,
            "markdown": md_file.read_text(encoding="utf-8", errors="ignore"),
        }
        if json_file.exists():
            try:
                result["json"] = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return result
