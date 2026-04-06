"""
PM/ERP 領域工具執行器

包含工具：
- search_projects: 搜尋承攬案件
- get_project_detail: 取得案件詳情
- get_project_progress: 取得案件進度
- search_vendors: 搜尋協力廠商
- get_vendor_detail: 取得廠商詳情
- get_contract_summary: 取得合約金額統計
- get_overdue_milestones: 查詢逾期里程碑
- get_unpaid_billings: 查詢未收款/逾期請款
- get_financial_summary: 查詢專案/公司財務總覽
- get_expense_overview: 查詢費用報銷總覽
- check_budget_alert: 預算超支警報檢查
- get_dispatch_progress: 派工進度彙整報告
- list_assets: 資產清單查詢
- get_asset_detail: 資產詳情
- get_asset_stats: 資產統計
- list_pending_expenses: 待審核費用
- get_expense_detail: 費用報銷詳情
- suggest_expense_category: AI 費用分類建議 (Gemma 4)
- get_dispatch_timeline: 派工單作業時間軸
- detect_dispatch_anomaly: 派工異常偵測 (Gemma 4)
- detect_project_risk: 專案風險偵測 (Gemma 4)
- analyze_document_intent: 公文意圖分析 (Gemma 4)

Extracted from agent_tools.py v1.83.0
Updated v5.1.1: 財務工具整合 (Phase 3-1/3-2)
Updated v5.2.5: 派工進度彙整 (OC-2 OpenClaw 模式轉化)
Updated v5.4.1: 新增 10 個業務模組工具 (asset/expense/dispatch/pm/document)
"""

import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DomainToolExecutor:
    """PM/ERP 領域工具執行器"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    async def search_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋承攬案件"""
        from app.services.ai.pm_query_service import PMQueryService

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        svc = PMQueryService(self.db)
        return await svc.search_projects(
            keywords=keywords or None,
            status=params.get("status"),
            year=params.get("year"),
            client_agency=params.get("client_agency"),
            limit=min(int(params.get("limit", 10)), 20),
        )

    async def get_project_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得案件詳情"""
        from app.services.ai.pm_query_service import PMQueryService

        project_id = params.get("project_id")
        if not project_id:
            return {"error": "需要提供 project_id 參數", "count": 0}

        svc = PMQueryService(self.db)
        return await svc.get_project_detail(int(project_id))

    async def get_project_progress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得案件進度"""
        from app.services.ai.pm_query_service import PMQueryService

        project_id = params.get("project_id")
        if not project_id:
            return {"error": "需要提供 project_id 參數", "count": 0}

        svc = PMQueryService(self.db)
        return await svc.get_project_progress(int(project_id))

    async def search_vendors(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋協力廠商"""
        from app.services.ai.erp_query_service import ERPQueryService

        keywords = params.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        svc = ERPQueryService(self.db)
        return await svc.search_vendors(
            keywords=keywords or None,
            business_type=params.get("business_type"),
            limit=min(int(params.get("limit", 10)), 20),
        )

    async def get_vendor_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得廠商詳情"""
        from app.services.ai.erp_query_service import ERPQueryService

        vendor_id = params.get("vendor_id")
        if not vendor_id:
            return {"error": "需要提供 vendor_id 參數", "count": 0}

        svc = ERPQueryService(self.db)
        return await svc.get_vendor_detail(int(vendor_id))

    async def get_contract_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取得合約金額統計"""
        from app.services.ai.erp_query_service import ERPQueryService

        svc = ERPQueryService(self.db)
        return await svc.get_contract_summary(
            year=params.get("year"),
            status=params.get("status"),
        )

    async def get_overdue_milestones(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢逾期里程碑"""
        from app.services.ai.pm_query_service import PMQueryService

        svc = PMQueryService(self.db)
        return await svc.get_overdue_milestones(
            limit=min(int(params.get("limit", 20)), 50),
        )

    async def get_unpaid_billings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢未收款/逾期請款"""
        from app.services.ai.erp_query_service import ERPQueryService

        svc = ERPQueryService(self.db)
        return await svc.get_unpaid_billings(
            limit=min(int(params.get("limit", 20)), 50),
        )

    # === Finance Tools (Phase 3, v5.1.1) ===

    async def get_financial_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢專案或公司財務總覽"""
        from app.services.financial_summary_service import FinancialSummaryService

        case_code = params.get("case_code")
        year = params.get("year")
        top_n = min(int(params.get("top_n", 10)), 50)

        svc = FinancialSummaryService(self.db)

        if case_code:
            result = await svc.get_project_summary(case_code)
            return {"type": "project", "summary": result, "count": 1}
        else:
            result = await svc.get_company_overview(year=year, top_n=top_n)
            return {"type": "company", "summary": result, "count": 1}

    async def get_expense_overview(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢費用報銷總覽"""
        from app.schemas.erp.expense import ExpenseInvoiceQuery
        from app.services.expense_invoice_service import ExpenseInvoiceService

        limit = min(int(params.get("limit", 20)), 50)
        query = ExpenseInvoiceQuery(
            case_code=params.get("case_code"),
            status=params.get("status"),
            skip=0,
            limit=limit,
        )

        svc = ExpenseInvoiceService(self.db)
        items, total = await svc.query(query)

        return {
            "items": [
                {
                    "id": inv.id,
                    "inv_num": inv.inv_num,
                    "date": str(inv.date) if inv.date else None,
                    "amount": float(inv.amount) if inv.amount else 0,
                    "category": inv.category,
                    "status": inv.status,
                    "case_code": inv.case_code,
                    "description": inv.description,
                }
                for inv in items
            ],
            "total": total,
            "count": len(items),
        }

    async def check_budget_alert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """預算超支警報檢查"""
        from app.services.financial_summary_service import FinancialSummaryService

        threshold_pct = min(float(params.get("threshold_pct", 80)), 100)
        year = params.get("year")

        svc = FinancialSummaryService(self.db)
        overview = await svc.get_company_overview(year=year, top_n=50)

        alerts = []
        for proj in overview.get("top_projects", []):
            revenue = float(proj.get("revenue", 0) or 0)
            expenses = float(proj.get("expenses", 0) or 0)
            if revenue > 0:
                usage_pct = (expenses / revenue) * 100
                if usage_pct >= threshold_pct:
                    alerts.append({
                        "case_code": proj.get("case_code"),
                        "revenue": revenue,
                        "expenses": expenses,
                        "usage_pct": round(usage_pct, 1),
                        "level": "critical" if usage_pct >= 100 else "warning",
                    })

        return {
            "threshold_pct": threshold_pct,
            "alerts": alerts,
            "count": len(alerts),
        }

    # === Dispatch Progress (OC-2, v5.2.5) ===

    async def get_dispatch_progress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """派工進度彙整報告"""
        from app.services.ai.dispatch_progress_synthesizer import DispatchProgressSynthesizer

        synth = DispatchProgressSynthesizer(self.db)
        report = await synth.generate_report(
            year=params.get("year"),
        )
        return synth.to_dict(report)

    async def search_tender(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜尋政府標案"""
        from app.services.tender_search_service import TenderSearchService

        service = TenderSearchService()
        query = params.get("query", "測量")
        page = params.get("page", 1)
        result = await service.search_by_title(query=query, page=page)

        records = result.get("records", [])[:8]
        return {
            "total": result.get("total_records", 0),
            "count": len(records),
            "tenders": [
                {
                    "title": r.get("title", ""),
                    "unit_name": r.get("unit_name", ""),
                    "type": r.get("type", ""),
                    "date": r.get("date", ""),
                    "category": r.get("category", ""),
                    "companies": r.get("company_names", []),
                }
                for r in records
            ],
        }

    async def auto_tender_to_case(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-Agent: 標案搜尋→篩選→自動建案

        流程: 搜尋標案 → 篩選符合乾坤業務的 → 自動建立 PM Case + ERP Quotation
        """
        from app.services.tender_search_service import TenderSearchService
        from app.services.case_code_service import CaseCodeService
        from app.extended.models.pm import PMCase
        from app.extended.models.erp import ERPQuotation
        from datetime import date
        import re

        query = params.get("query", "測量")
        max_create = min(params.get("max_create", 3), 5)  # 最多 5 筆

        service = TenderSearchService()
        result = await service.search_by_title(query=query, page=1)
        records = result.get("records", [])

        # 只處理公開招標/取得報價 類型（排除決標/更正/廢標）
        actionable = [
            r for r in records
            if r.get("type", "").startswith(("公開", "限制性")) and r.get("title")
        ][:max_create]

        if not actionable:
            return {"created": 0, "message": f"搜尋「{query}」無可建案的招標公告"}

        code_service = CaseCodeService(self.db)
        created = []
        year = date.today().year

        for r in actionable:
            try:
                # 檢查是否已建案（避免重複）
                existing = await self.db.execute(
                    __import__('sqlalchemy').select(PMCase).where(
                        PMCase.case_name == r["title"][:200]
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                case_code = await code_service.generate_case_code("pm", year, "01")

                # 解析預算
                budget = 0
                # budget 在 detail 中，列表沒有，設為 0

                pm = PMCase(case_code=case_code, case_name=r["title"][:200], year=year, status="bidding",
                            notes=f"[Agent] 標案: {r.get('job_number', '')} ({r.get('unit_name', '')})")
                self.db.add(pm)
                await self.db.flush()

                q = ERPQuotation(case_code=case_code, case_name=r["title"][:200], year=year,
                                 total_price=budget, status="draft",
                                 notes=f"[Agent] {r.get('unit_name', '')} | {r.get('type', '')}")
                self.db.add(q)

                created.append({
                    "case_code": case_code,
                    "title": r["title"][:60],
                    "unit_name": r.get("unit_name", ""),
                })
            except Exception as e:
                continue

        if created:
            await self.db.commit()

        return {
            "query": query,
            "searched": len(records),
            "actionable": len(actionable),
            "created": len(created),
            "cases": created,
        }

    async def analyze_diagram(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析工程圖/測量圖/地籍圖 (Gemma 4 Vision)"""
        from app.services.ai.engineering_diagram_service import EngineeringDiagramService
        from app.extended.models.document import DocumentAttachment
        import os

        image_path = params.get("image_path", "")
        diagram_type = params.get("diagram_type", "survey")
        context = params.get("context", "")

        if not image_path:
            return {"error": "缺少 image_path 參數", "count": 0}

        # Resolve attachment path
        upload_dir = os.getenv("UPLOAD_DIR", "uploads")
        full_path = os.path.join(upload_dir, image_path) if not os.path.isabs(image_path) else image_path

        if not os.path.isfile(full_path):
            # Try looking up by attachment filename in DB
            from sqlalchemy import select
            stmt = select(DocumentAttachment).where(
                DocumentAttachment.file_name.ilike(f"%{os.path.basename(image_path)}%")
            )
            result = await self.db.execute(stmt)
            att = result.scalar_one_or_none()
            if att and att.file_path:
                full_path = os.path.join(upload_dir, att.file_path)

        if not os.path.isfile(full_path):
            return {"error": f"找不到圖檔: {image_path}", "count": 0}

        with open(full_path, "rb") as f:
            image_bytes = f.read()

        service = EngineeringDiagramService()
        result = await service.analyze_diagram(
            image_bytes=image_bytes,
            diagram_type=diagram_type,
            context=context,
        )
        result["count"] = 1
        return result

    # === Asset Tools (v5.4.1) ===

    async def list_assets(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢資產清單"""
        from app.services.erp.asset_service import AssetService
        from app.schemas.erp.asset import AssetListRequest

        req = AssetListRequest(
            category=params.get("category"),
            status=params.get("status"),
            case_code=params.get("case_code"),
            skip=0,
            limit=min(int(params.get("limit", 20)), 50),
        )

        svc = AssetService(self.db)
        assets, total = await svc.list_assets(req)

        return {
            "assets": [
                {
                    "id": a.id,
                    "asset_code": a.asset_code,
                    "name": a.name,
                    "category": a.category,
                    "status": a.status,
                    "purchase_price": float(a.purchase_price) if a.purchase_price else 0,
                    "location": getattr(a, "location", None),
                }
                for a in assets[:20]
            ],
            "total": total,
            "count": min(len(assets), 20),
        }

    async def get_asset_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢資產詳情含折舊和行為紀錄"""
        from app.services.erp.asset_service import AssetService

        asset_id = params.get("asset_id")
        if not asset_id:
            return {"error": "需要提供 asset_id 參數", "count": 0}

        svc = AssetService(self.db)
        detail = await svc.get_asset_with_relations(int(asset_id))

        if not detail:
            return {"error": f"找不到資產 ID={asset_id}", "count": 0}

        return {"asset": detail, "count": 1}

    async def get_asset_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """資產統計摘要"""
        from app.services.erp.asset_service import AssetService

        svc = AssetService(self.db)
        stats = await svc.get_stats()

        return {"stats": stats, "count": 1}

    # === Invoice/Expense Tools (v5.4.1) ===

    async def list_pending_expenses(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢待審核費用清單"""
        from app.schemas.erp.expense import ExpenseInvoiceQuery
        from app.services.expense_invoice_service import ExpenseInvoiceService

        status = params.get("status", "pending")
        limit = min(int(params.get("limit", 20)), 50)
        query = ExpenseInvoiceQuery(
            case_code=params.get("case_code"),
            status=status,
            skip=0,
            limit=limit,
        )

        svc = ExpenseInvoiceService(self.db)
        items, total = await svc.query(query)

        return {
            "items": [
                {
                    "id": inv.id,
                    "inv_num": inv.inv_num,
                    "date": str(inv.date) if inv.date else None,
                    "amount": float(inv.amount) if inv.amount else 0,
                    "category": inv.category,
                    "status": inv.status,
                    "case_code": inv.case_code,
                    "description": inv.description,
                }
                for inv in items
            ],
            "total": total,
            "count": len(items),
        }

    async def get_expense_detail(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢費用報銷詳情含明細和審核歷程"""
        from app.services.expense_invoice_service import ExpenseInvoiceService

        expense_id = params.get("expense_id")
        if not expense_id:
            return {"error": "需要提供 expense_id 參數", "count": 0}

        svc = ExpenseInvoiceService(self.db)
        inv = await svc.get_by_id(int(expense_id))

        if not inv:
            return {"error": f"找不到費用報銷 ID={expense_id}", "count": 0}

        # Get items if available
        items_list = []
        if hasattr(inv, "items") and inv.items:
            items_list = [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price) if item.unit_price else 0,
                    "amount": float(item.amount) if item.amount else 0,
                }
                for item in inv.items
            ]

        return {
            "expense": {
                "id": inv.id,
                "inv_num": inv.inv_num,
                "date": str(inv.date) if inv.date else None,
                "amount": float(inv.amount) if inv.amount else 0,
                "category": inv.category,
                "status": inv.status,
                "case_code": inv.case_code,
                "description": inv.description,
                "voucher_type": getattr(inv, "voucher_type", None),
                "items": items_list,
            },
            "count": 1,
        }

    async def suggest_expense_category(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """根據品名和廠商建議費用類別（Gemma 4）"""
        description = params.get("description", "")
        vendor = params.get("vendor", "")

        if not description:
            return {"error": "需要提供 description 參數", "count": 0}

        prompt = (
            "你是費用分類專家。根據以下費用描述，從這些類別中選擇最適合的：\n"
            "交通費、餐飲費、文具用品、設備器材、通訊費、維修費、印刷費、郵資、水電費、雜支\n\n"
            f"費用描述：{description}\n"
        )
        if vendor:
            prompt += f"廠商：{vendor}\n"
        prompt += '\n請以 JSON 回覆：{"category": "類別名稱", "confidence": 0.0~1.0, "reason": "原因"}'

        try:
            from app.services.ai.agent_utils import parse_json_safe

            result = await self.ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=128,
                task_type="classify",
            )
            parsed = parse_json_safe(result)
            if parsed and "category" in parsed:
                parsed["count"] = 1
                return parsed
            return {"category": "雜支", "confidence": 0.3, "reason": "無法判斷", "count": 1}
        except Exception as e:
            logger.warning("suggest_expense_category failed: %s", e)
            return {"category": "雜支", "confidence": 0.0, "reason": str(e), "count": 1}

    # === Dispatch Tools (v5.4.1) ===

    async def get_dispatch_timeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢派工單完整作業時間軸"""
        from sqlalchemy import select
        from app.extended.models.taoyuan import TaoyuanDispatchOrder, TaoyuanWorkRecord

        dispatch_id = params.get("dispatch_id")
        if not dispatch_id:
            return {"error": "需要提供 dispatch_id 參數", "count": 0}

        dispatch_id = int(dispatch_id)

        # Get dispatch order
        stmt = select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
        result = await self.db.execute(stmt)
        dispatch = result.scalar_one_or_none()

        if not dispatch:
            return {"error": f"找不到派工單 ID={dispatch_id}", "count": 0}

        # Get work records
        stmt2 = (
            select(TaoyuanWorkRecord)
            .where(TaoyuanWorkRecord.dispatch_order_id == dispatch_id)
            .order_by(TaoyuanWorkRecord.work_date)
        )
        result2 = await self.db.execute(stmt2)
        records = result2.scalars().all()

        timeline = []
        for rec in records:
            timeline.append({
                "date": str(rec.work_date) if rec.work_date else None,
                "type": "work_record",
                "category": getattr(rec, "work_category", None),
                "description": getattr(rec, "description", None),
            })

        return {
            "dispatch_no": dispatch.dispatch_no,
            "project_name": getattr(dispatch, "project_name", None),
            "status": getattr(dispatch, "status", None),
            "timeline": timeline,
            "count": len(timeline),
        }

    async def detect_dispatch_anomaly(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """偵測派工異常（Gemma 4）"""
        from sqlalchemy import select, func
        from app.extended.models.taoyuan import TaoyuanDispatchOrder, TaoyuanWorkRecord
        from datetime import date, timedelta

        contract_project_id = params.get("contract_project_id")
        today = date.today()

        # Find dispatches with potential issues
        stmt = select(TaoyuanDispatchOrder)
        if contract_project_id:
            stmt = stmt.where(TaoyuanDispatchOrder.contract_project_id == int(contract_project_id))
        stmt = stmt.limit(50)

        result = await self.db.execute(stmt)
        dispatches = result.scalars().all()

        anomalies_text = []
        for d in dispatches:
            deadline = getattr(d, "deadline", None)
            status = getattr(d, "status", "")
            if deadline and deadline < today and status not in ("已完成", "completed"):
                days = (today - deadline).days
                anomalies_text.append(
                    f"- 派工 {d.dispatch_no}: 逾期 {days} 天, 狀態={status}"
                )

        if not anomalies_text:
            return {"anomalies": [], "summary": "未偵測到異常", "count": 0}

        prompt = (
            "你是派工管理專家。分析以下派工異常，給出風險等級和建議：\n\n"
            + "\n".join(anomalies_text[:15])
            + '\n\n請以 JSON 回覆：{"anomalies": [{"dispatch_no": "xxx", "risk": "high/medium/low", "issue": "描述", "action": "建議"}], "summary": "總結"}'
        )

        try:
            from app.services.ai.agent_utils import parse_json_safe

            result = await self.ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
                task_type="classify",
            )
            parsed = parse_json_safe(result)
            if parsed and "anomalies" in parsed:
                parsed["count"] = len(parsed["anomalies"])
                return parsed
        except Exception as e:
            logger.warning("detect_dispatch_anomaly AI failed: %s", e)

        # Fallback: return raw anomalies
        return {
            "anomalies": [{"dispatch_no": line.split(":")[0].replace("- 派工 ", "").strip(), "risk": "high", "issue": line} for line in anomalies_text[:10]],
            "summary": f"共 {len(anomalies_text)} 個派工異常",
            "count": len(anomalies_text),
        }

    # === PM Risk Tool (v5.4.1) ===

    async def detect_project_risk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """偵測專案風險（Gemma 4）"""
        from sqlalchemy import select, func
        from app.extended.models.pm import PMCase, PMMilestone
        from datetime import date

        case_code = params.get("case_code")
        if not case_code:
            return {"error": "需要提供 case_code 參數", "count": 0}

        # Get project
        stmt = select(PMCase).where(PMCase.case_code == case_code)
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": f"找不到案件 {case_code}", "count": 0}

        # Get milestones
        stmt2 = select(PMMilestone).where(PMMilestone.case_code == case_code)
        result2 = await self.db.execute(stmt2)
        milestones = result2.scalars().all()

        today = date.today()
        overdue_count = sum(
            1 for m in milestones
            if m.due_date and m.due_date < today and getattr(m, "status", "") != "completed"
        )

        # Get expense total
        try:
            from app.extended.models.invoice import ExpenseInvoice
            stmt3 = select(func.sum(ExpenseInvoice.amount)).where(
                ExpenseInvoice.case_code == case_code
            )
            result3 = await self.db.execute(stmt3)
            expense_total = result3.scalar() or 0
        except Exception:
            expense_total = 0

        # Build context for AI
        milestone_info = "\n".join([
            f"  - {m.name}: 截止 {m.due_date}, 狀態 {getattr(m, 'status', '?')}"
            for m in milestones[:10]
        ]) or "無里程碑"

        prompt = (
            "你是專案風險分析專家。分析此專案的風險並給出評分 (0-100)。\n\n"
            f"案號: {case_code}\n"
            f"案名: {project.case_name}\n"
            f"狀態: {project.status}\n"
            f"里程碑 ({len(milestones)} 個, 逾期 {overdue_count} 個):\n{milestone_info}\n"
            f"費用總額: {float(expense_total):,.0f}\n\n"
            '請以 JSON 回覆：{"risk_score": 0-100, "risk_level": "high/medium/low", '
            '"risks": [{"type": "milestone_delay/budget_overrun/resource_conflict", "detail": "描述"}], '
            '"recommendation": "建議"}'
        )

        try:
            from app.services.ai.agent_utils import parse_json_safe

            result = await self.ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
                task_type="classify",
            )
            parsed = parse_json_safe(result)
            if parsed and "risk_score" in parsed:
                parsed["case_code"] = case_code
                parsed["count"] = 1
                return parsed
        except Exception as e:
            logger.warning("detect_project_risk AI failed: %s", e)

        # Fallback
        risk_level = "high" if overdue_count > 2 else ("medium" if overdue_count > 0 else "low")
        return {
            "case_code": case_code,
            "risk_score": overdue_count * 25,
            "risk_level": risk_level,
            "risks": [{"type": "milestone_delay", "detail": f"{overdue_count} 個里程碑逾期"}] if overdue_count else [],
            "recommendation": "建議優先處理逾期里程碑" if overdue_count else "專案風險可控",
            "count": 1,
        }

    # === Document Intent Tool (v5.4.1) ===

    async def analyze_document_intent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析公文意圖（Gemma 4）"""
        from sqlalchemy import select
        from app.extended.models.document import OfficialDocument

        document_id = params.get("document_id")
        if not document_id:
            return {"error": "需要提供 document_id 參數", "count": 0}

        stmt = select(OfficialDocument).where(OfficialDocument.id == int(document_id))
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            return {"error": f"找不到公文 ID={document_id}", "count": 0}

        subject = getattr(doc, "subject", "") or ""
        doc_type = getattr(doc, "doc_type", "") or ""
        sender = getattr(doc, "sender", "") or ""

        prompt = (
            "你是公文處理專家。分析以下公文的意圖，判斷需要的動作。\n\n"
            f"公文類型: {doc_type}\n"
            f"主旨: {subject}\n"
            f"發文單位: {sender}\n\n"
            "意圖分類：\n"
            "- reply_required: 需要回覆（如函詢、要求說明）\n"
            "- forward_required: 需要轉發（如轉知、副知）\n"
            "- action_required: 需要執行動作（如辦理、配合辦理）\n"
            "- info_only: 僅供備查（如通報、公告）\n\n"
            '請以 JSON 回覆：{"intent": "分類", "confidence": 0.0~1.0, "reason": "判斷依據", "suggested_action": "建議動作"}'
        )

        try:
            from app.services.ai.agent_utils import parse_json_safe

            result = await self.ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
                task_type="classify",
            )
            parsed = parse_json_safe(result)
            if parsed and "intent" in parsed:
                parsed["document_id"] = document_id
                parsed["subject"] = subject[:60]
                parsed["count"] = 1
                return parsed
        except Exception as e:
            logger.warning("analyze_document_intent AI failed: %s", e)

        # Fallback based on doc_type
        intent = "info_only"
        if doc_type in ("函", "書函"):
            intent = "reply_required"
        elif "轉" in subject or "副知" in subject:
            intent = "forward_required"

        return {
            "document_id": document_id,
            "subject": subject[:60],
            "intent": intent,
            "confidence": 0.3,
            "reason": f"基於公文類型 {doc_type} 的預設判斷",
            "suggested_action": "建議人工確認",
            "count": 1,
        }
