"""
業務工具執行器 (資產/費用/派工/風險/意圖)

拆分自 tool_executor_domain.py v5.5.0

包含工具：
- list_assets / get_asset_detail / get_asset_stats
- list_pending_expenses / get_expense_detail / suggest_expense_category
- get_dispatch_timeline / detect_dispatch_anomaly
- detect_project_risk
- analyze_document_intent
"""

import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BusinessToolExecutor:
    """資產/費用/派工/風險/意圖 工具執行器"""

    def __init__(self, db: AsyncSession, ai_connector, embedding_mgr, config):
        self.db = db
        self.ai = ai_connector
        self.embedding_mgr = embedding_mgr
        self.config = config

    # === Asset Tools ===

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

    # === Expense Tools ===

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
            from app.services.ai.core.agent_utils import parse_json_safe

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

    # === Dispatch Tools ===

    async def get_dispatch_timeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """查詢派工單完整作業時間軸"""
        from sqlalchemy import select
        from app.extended.models.taoyuan import TaoyuanDispatchOrder, TaoyuanWorkRecord

        dispatch_id = params.get("dispatch_id")
        if not dispatch_id:
            return {"error": "需要提供 dispatch_id 參數", "count": 0}

        dispatch_id = int(dispatch_id)

        stmt = select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_id)
        result = await self.db.execute(stmt)
        dispatch = result.scalar_one_or_none()

        if not dispatch:
            return {"error": f"找不到派工單 ID={dispatch_id}", "count": 0}

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
        from sqlalchemy import select
        from app.extended.models.taoyuan import TaoyuanDispatchOrder
        from datetime import date

        contract_project_id = params.get("contract_project_id")
        today = date.today()

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
            from app.services.ai.core.agent_utils import parse_json_safe

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

        return {
            "anomalies": [{"dispatch_no": line.split(":")[0].replace("- 派工 ", "").strip(), "risk": "high", "issue": line} for line in anomalies_text[:10]],
            "summary": f"共 {len(anomalies_text)} 個派工異常",
            "count": len(anomalies_text),
        }

    # === PM Risk Tool ===

    async def detect_project_risk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """偵測專案風險（Gemma 4）"""
        from sqlalchemy import select, func
        from app.extended.models.pm import PMCase, PMMilestone
        from datetime import date

        case_code = params.get("case_code")
        if not case_code:
            return {"error": "需要提供 case_code 參數", "count": 0}

        stmt = select(PMCase).where(PMCase.case_code == case_code)
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": f"找不到案件 {case_code}", "count": 0}

        stmt2 = select(PMMilestone).where(PMMilestone.case_code == case_code)
        result2 = await self.db.execute(stmt2)
        milestones = result2.scalars().all()

        today = date.today()
        overdue_count = sum(
            1 for m in milestones
            if m.due_date and m.due_date < today and getattr(m, "status", "") != "completed"
        )

        try:
            from app.extended.models.invoice import ExpenseInvoice
            stmt3 = select(func.sum(ExpenseInvoice.amount)).where(
                ExpenseInvoice.case_code == case_code
            )
            result3 = await self.db.execute(stmt3)
            expense_total = result3.scalar() or 0
        except Exception:
            expense_total = 0

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
            from app.services.ai.core.agent_utils import parse_json_safe

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

        risk_level = "high" if overdue_count > 2 else ("medium" if overdue_count > 0 else "low")
        return {
            "case_code": case_code,
            "risk_score": overdue_count * 25,
            "risk_level": risk_level,
            "risks": [{"type": "milestone_delay", "detail": f"{overdue_count} 個里程碑逾期"}] if overdue_count else [],
            "recommendation": "建議優先處理逾期里程碑" if overdue_count else "專案風險可控",
            "count": 1,
        }

    # === Document Intent Tool ===

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
            from app.services.ai.core.agent_utils import parse_json_safe

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
