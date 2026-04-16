"""
派工進度彙整合成服務

將 proactive_triggers 的原始告警升級為 AI 合成的結構化進度報告。
結構化派工進度輸出格式（已完成/進行中/逾期+負責人+建議）。

三階段流程:
  1. DB 掃描: 查詢所有派工單狀態 + 作業紀錄進度
  2. 業務分類: 已完成/進行中/逾期，含逾期天數+負責人
  3. 摘要合成: 結構化文字 + 關鍵提醒

Version: 1.0.0
Created: 2026-03-27
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class DispatchProgressItem:
    """單筆派工單進度"""
    dispatch_id: int
    dispatch_no: str
    project_name: str
    case_handler: Optional[str]
    deadline_text: Optional[str]
    deadline_date: Optional[date]
    completed_records: int
    total_records: int
    status: str  # completed, in_progress, overdue, pending
    overdue_days: int = 0


@dataclass
class DispatchProgressReport:
    """派工進度彙整報告"""
    year: int
    scan_time: str
    completed: List[DispatchProgressItem]
    in_progress: List[DispatchProgressItem]
    overdue: List[DispatchProgressItem]
    pending: List[DispatchProgressItem]
    key_alerts: List[str]
    handler_summary: Dict[str, Dict[str, int]]  # {handler: {completed: n, overdue: n}}


def _parse_roc_date(deadline_text: Optional[str]) -> Optional[date]:
    """解析民國年日期字串 → date 物件"""
    if not deadline_text:
        return None
    m = re.search(r'(\d{2,3})年(\d{1,2})月(\d{1,2})日', deadline_text)
    if not m:
        return None
    try:
        roc_year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        return date(roc_year + 1911, month, day)
    except (ValueError, OverflowError):
        return None


class DispatchProgressSynthesizer:
    """派工進度彙整合成器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(
        self,
        year: Optional[int] = None,
        contract_project_id: Optional[int] = None,
    ) -> DispatchProgressReport:
        """
        生成派工進度彙整報告

        Args:
            year: 民國年度（如 115），預設為當前年度
            contract_project_id: 限定特定承攬案件
        """
        if year is None:
            year = date.today().year - 1911

        year_prefix = f"{year}年"
        today = date.today()

        # Stage 1: DB 掃描
        items = await self._scan_dispatches(year_prefix, contract_project_id)

        # Stage 2: 業務分類
        completed = []
        in_progress = []
        overdue = []
        pending = []

        for item in items:
            if item.total_records > 0 and item.completed_records == item.total_records:
                item.status = 'completed'
                completed.append(item)
            elif item.deadline_date and item.deadline_date < today:
                item.status = 'overdue'
                item.overdue_days = (today - item.deadline_date).days
                overdue.append(item)
            elif item.total_records > 0 and item.completed_records > 0:
                item.status = 'in_progress'
                in_progress.append(item)
            else:
                # 有 deadline 在未來 → in_progress，否則 pending
                if item.deadline_date and item.deadline_date >= today:
                    item.status = 'in_progress'
                    in_progress.append(item)
                else:
                    item.status = 'pending'
                    pending.append(item)

        # Stage 3: 負責人彙總 + 關鍵提醒
        handler_summary: Dict[str, Dict[str, int]] = {}
        for item in items:
            h = item.case_handler or '未指派'
            if h not in handler_summary:
                handler_summary[h] = {'completed': 0, 'in_progress': 0, 'overdue': 0, 'total': 0}
            handler_summary[h]['total'] += 1
            if item.status == 'completed':
                handler_summary[h]['completed'] += 1
            elif item.status == 'overdue':
                handler_summary[h]['overdue'] += 1
            else:
                handler_summary[h]['in_progress'] += 1

        key_alerts = self._generate_alerts(overdue, handler_summary, completed, in_progress)

        # 排序: 逾期天數多的排前面
        overdue.sort(key=lambda x: x.overdue_days, reverse=True)

        return DispatchProgressReport(
            year=year,
            scan_time=today.isoformat(),
            completed=completed,
            in_progress=in_progress,
            overdue=overdue,
            pending=pending,
            key_alerts=key_alerts,
            handler_summary=handler_summary,
        )

    async def _scan_dispatches(
        self, year_prefix: str, contract_project_id: Optional[int]
    ) -> List[DispatchProgressItem]:
        """查詢派工單 + 作業紀錄統計"""
        query = text("""
            SELECT d.id, d.dispatch_no, d.project_name, d.deadline,
                   d.case_handler,
                   COALESCE((SELECT COUNT(*) FROM taoyuan_work_records wr
                    WHERE wr.dispatch_order_id = d.id
                    AND wr.status = 'completed'), 0) as completed_count,
                   COALESCE((SELECT COUNT(*) FROM taoyuan_work_records wr
                    WHERE wr.dispatch_order_id = d.id), 0) as total_records
            FROM taoyuan_dispatch_orders d
            WHERE d.dispatch_no LIKE :prefix
            ORDER BY d.id
        """)
        params: Dict[str, Any] = {"prefix": f"{year_prefix}%"}

        result = await self.db.execute(query, params)
        items = []
        for r in result.fetchall():
            deadline_date = _parse_roc_date(r.deadline)
            items.append(DispatchProgressItem(
                dispatch_id=r.id,
                dispatch_no=r.dispatch_no,
                project_name=r.project_name or '',
                case_handler=r.case_handler,
                deadline_text=r.deadline,
                deadline_date=deadline_date,
                completed_records=r.completed_count,
                total_records=r.total_records,
                status='pending',
            ))
        return items

    def _generate_alerts(
        self,
        overdue: List[DispatchProgressItem],
        handler_summary: Dict[str, Dict[str, int]],
        completed: List[DispatchProgressItem],
        in_progress: List[DispatchProgressItem],
    ) -> List[str]:
        """生成關鍵提醒"""
        alerts = []

        # 負責人逾期集中提醒
        for handler, stats in handler_summary.items():
            if stats['overdue'] >= 2:
                alerts.append(
                    f"{handler}承辦的 {stats['overdue']} 筆派工單都逾期"
                    f"{'，建議立即跟進' if stats['overdue'] >= 3 else ''}"
                )

        # 最近完成的派工單
        recent_completed = [
            c for c in completed
            if c.deadline_date and (date.today() - c.deadline_date).days <= 7
        ]
        if recent_completed:
            nos = '、'.join(
                c.dispatch_no.replace(f'{c.dispatch_no[:4]}_派工單號', '')
                for c in recent_completed[:5]
            )
            alerts.append(f"最近 {len(recent_completed)} 筆派工單（{nos}）已全部如期完成")

        # 即將到期
        upcoming = [
            ip for ip in in_progress
            if ip.deadline_date and 0 < (ip.deadline_date - date.today()).days <= 7
        ]
        if upcoming:
            for u in upcoming:
                days_left = (u.deadline_date - date.today()).days
                alerts.append(
                    f"{u.dispatch_no} 剩餘 {days_left} 天到期"
                    f"（{u.case_handler or '未指派'}）"
                )

        return alerts

    def format_text_report(self, report: DispatchProgressReport) -> str:
        """格式化為結構化文字報告"""
        lines = [
            f"📊 派工進度彙整 — {date.today().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        # 已完成
        if report.completed:
            lines.append(f"✅ 已完成派工單 ({len(report.completed)}筆)")
            for i, c in enumerate(report.completed, 1):
                no_short = c.dispatch_no.replace(f'{report.year}年_', '')
                name = c.project_name[:25]
                handler = f"（{c.case_handler}）" if c.case_handler else ""
                lines.append(f"{i}. {no_short} - {name} {handler}")
            lines.append("")

        # 進行中
        active = report.in_progress + report.pending
        if active:
            lines.append(f"🔄 進行中派工單 ({len(active)}筆)")
            for item in active:
                no_short = item.dispatch_no.replace(f'{report.year}年_', '')
                name = item.project_name[:25]
                handler = f"（{item.case_handler}）" if item.case_handler else ""
                deadline_info = ""
                if item.deadline_date:
                    days_left = (item.deadline_date - date.today()).days
                    if days_left <= 7:
                        deadline_info = f" | 期限: {item.deadline_date.strftime('%Y-%m-%d')}"
                status_mark = ""
                if item.completed_records == item.total_records and item.total_records > 0:
                    status_mark = " — 已完成 ✅"
                lines.append(f"  - {no_short} {name} {handler}{deadline_info}{status_mark}")
            lines.append("")

        # 逾期
        if report.overdue:
            lines.append(f"🔴 逾期派工單 ({len(report.overdue)}筆)")
            for item in report.overdue:
                no_short = item.dispatch_no.replace(f'{report.year}年_', '')
                name = item.project_name[:25]
                handler = f"（{item.case_handler}）" if item.case_handler else ""
                lines.append(
                    f"  - {no_short} - {name} {handler}"
                    f" | 期限: {item.deadline_date} | 逾期{item.overdue_days}天 ⚠️"
                )
            lines.append("")

        # 關鍵提醒
        if report.key_alerts:
            lines.append("關鍵提醒：")
            for alert in report.key_alerts:
                lines.append(f"・{alert}")

        return "\n".join(lines)

    def to_dict(self, report: DispatchProgressReport) -> Dict[str, Any]:
        """轉換為 API 回傳用 dict"""
        def _item_dict(item: DispatchProgressItem) -> Dict[str, Any]:
            return {
                'dispatch_id': item.dispatch_id,
                'dispatch_no': item.dispatch_no,
                'project_name': item.project_name,
                'case_handler': item.case_handler,
                'deadline_text': item.deadline_text,
                'deadline_date': item.deadline_date.isoformat() if item.deadline_date else None,
                'completed_records': item.completed_records,
                'total_records': item.total_records,
                'status': item.status,
                'overdue_days': item.overdue_days,
            }

        return {
            'year': report.year,
            'scan_time': report.scan_time,
            'completed': [_item_dict(i) for i in report.completed],
            'in_progress': [_item_dict(i) for i in report.in_progress],
            'overdue': [_item_dict(i) for i in report.overdue],
            'pending': [_item_dict(i) for i in report.pending],
            'key_alerts': report.key_alerts,
            'handler_summary': report.handler_summary,
            'summary_text': self.format_text_report(report),
        }
