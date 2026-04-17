"""
Wiki Markdown 格式化器 — 從 wiki_compiler.py 拆分 (v5.6.0 技術債清理)

純函數模組：接收資料 dict，回傳 Markdown 字串。
不含任何 DB 查詢或 IO 操作。

Version: 1.0.0
Created: 2026-04-17
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WikiFormatter:
    """Wiki Markdown 格式化器 — 無狀態，純字串輸出"""

    @staticmethod
    def build_agency_description(row, projects, recent_docs) -> str:
        """建構機關 wiki 描述"""
        lines = [
            f"**機關代碼**: {row.agency_code or '(未登錄)'}",
            f"**機關類型**: {row.agency_type or '(未分類)'}",
            f"**往來期間**: {row.earliest} ~ {row.latest}",
            f"**公文統計**: 共 {row.doc_count} 件 (收文 {row.received} / 發文 {row.sent})",
            "",
        ]

        if projects:
            lines.append("## 關聯承攬案件")
            lines.append("")
            lines.append("| 案名 | 案號 | 年度 | 狀態 |")
            lines.append("|------|------|------|------|")
            for p in projects:
                lines.append(
                    f"| {p['name'][:40]} | {p['code']} | {p['year'] or ''} | {p['status']} |"
                )
            lines.append("")

        if recent_docs:
            lines.append("## 最近公文")
            lines.append("")
            for d in recent_docs:
                lines.append(
                    f"- [{d['category']}] {d['date']} {d['subject'][:60]}"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def build_project_description_v2(
        row, all_docs, financial, dispatches, agencies, engineering=None,
    ) -> str:
        """建構案件 wiki 描述 (v2 完整版 — 工程 + 公文 + 派工 + 機關 + 財務)"""
        amount_str = (
            f"${row.contract_amount:,.0f}" if row.contract_amount else "(未登錄)"
        )
        lines = [
            f"**案號**: {row.project_code or '(未指派)'}",
            f"**狀態**: {row.status or '(未設定)'}",
            f"**年度**: {row.year or '(未設定)'}",
            f"**合約金額**: {amount_str}",
            f"**地點**: {row.location or '(未登錄)'}",
            f"**關聯公文**: {len(all_docs)} 件",
            f"**派工單**: {len(dispatches)} 筆" if dispatches else "",
            "",
        ]

        # 工程名稱
        if engineering:
            lines.append(f"## 工程名稱 ({len(engineering)} 筆)")
            lines.append("")
            lines.append("| 工程 | 區域 | 起點 | 終點 |")
            lines.append("|------|------|------|------|")
            for eng in engineering:
                lines.append(
                    f"| {eng['name'][:40]} | {eng['district']} | {eng['start_point']} | {eng['end_point']} |"
                )
            lines.append("")

        # 往來機關
        if agencies:
            lines.append("## 往來機關")
            lines.append("")
            lines.append("| 機關 | 公文數 |")
            lines.append("|------|--------|")
            for a in agencies:
                lines.append(f"| [[entities/{a['name']}|{a['name']}]] | {a['doc_count']} |")
            lines.append("")

        # 財務
        if financial:
            lines.append("## 財務摘要")
            lines.append(
                f"- 報價紀錄 {financial['quote_count']} 筆, "
                f"合計 ${financial['total_quoted']:,.0f}"
            )
            lines.append("")

        # 派工單
        if dispatches:
            lines.append(f"## 派工單 ({len(dispatches)} 筆)")
            lines.append("")
            lines.append("| 派工單號 | 工程名稱 | 作業類別 | 承辦 | 履約期限 |")
            lines.append("|----------|----------|----------|------|----------|")
            for d in dispatches:
                dno = d['dispatch_no']
                lines.append(
                    f"| [[entities/{dno}|{dno}]] | {d.get('project_name','')[:25]} | {d['work_type'][:15]} | {d.get('handler','')} | {d.get('deadline','')[:15]} |"
                )
            lines.append("")

        # 公文 — 按月份分組 (完整列表)
        if all_docs:
            lines.append(f"## 公文清單 ({len(all_docs)} 件)")
            lines.append("")

            # 按月份分組
            by_month: Dict[str, List] = {}
            for d in all_docs:
                month = d['date'][:7] if d['date'] else 'unknown'
                by_month.setdefault(month, []).append(d)

            for month in sorted(by_month.keys(), reverse=True):
                docs = by_month[month]
                lines.append(f"### {month} ({len(docs)} 件)")
                lines.append("")
                for d in docs:
                    lines.append(
                        f"- [{d['category']}] {d['date']} `{d['doc_number'][:20]}` {d['subject'][:50]}"
                    )
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def build_overview(doc_count, project_count, agency_count, year_rows, cat_rows) -> str:
        """建構總覽 wiki 描述"""
        lines = [
            f"**公文總數**: {doc_count} 件",
            f"**承攬案件**: {project_count} 件",
            f"**機關數**: {agency_count}",
            f"**編譯時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 年度公文分佈",
            "",
            "| 年度 | 件數 |",
            "|------|------|",
        ]
        for r in year_rows:
            lines.append(f"| {int(r.year)} | {r.count} |")

        lines.extend([
            "",
            "## 類別分佈",
            "",
        ])
        for r in cat_rows:
            lines.append(f"- **{r.category or '(未分類)'}**: {r.count} 件")

        return "\n".join(lines)
