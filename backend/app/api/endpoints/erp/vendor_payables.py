"""ERP 廠商應付 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service, get_async_db
from app.services.erp import ERPVendorPayableService
from app.schemas.erp import (
    ERPVendorPayableCreate, ERPVendorPayableUpdate,
    ERPIdRequest, ERPQuotationIdRequest, ERPPayableUpdateRequest,
)
from app.schemas.common import SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_vendor_payables(
    req: ERPQuotationIdRequest,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """取得報價單廠商應付"""
    items = await service.get_by_quotation(req.erp_quotation_id)
    return SuccessResponse(data=items)


@router.post("/create")
async def create_vendor_payable(
    data: ERPVendorPayableCreate,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """建立廠商應付"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="廠商應付建立成功")


@router.post("/update")
async def update_vendor_payable(
    req: ERPPayableUpdateRequest,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """更新廠商應付"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="廠商應付不存在")
    return SuccessResponse(data=result, message="廠商應付更新成功")


@router.post("/delete")
async def delete_vendor_payable(
    req: ERPIdRequest,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """刪除廠商應付"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="廠商應付不存在")
    return DeleteResponse(deleted_id=req.id)


@router.post("/assignment-gaps")
async def list_assignment_gaps(
    req: ERPQuotationIdRequest,
    db=Depends(get_async_db),
):
    """本案已指派、但**還沒有對應應付**的協力廠商。

    ⭐ 2026-09-08 owner：「/erp/quotations/789?tab=payable 無對應應付帳款」。

    實查：那一案（CK2026_PM_02_109）**有**協力廠商指派（廠商 401、角色「測量業務」），
    但 `project_vendor_association.contract_amount = 0` ⇒
    「指派即應付」（weekly 106）依設計不建應付（金額 0 建不出有意義的應付）。

    也就是說系統是對的，**但畫面說不出為什麼是空的** ——
    使用者看到的只是一張空表格，而「沒有協力廠商」與「有協力廠商但沒填委外金額」
    在畫面上長得一模一樣。本 repo 記過這件事：**空清單長什麼樣，要分得出來。**

    ⇒ 這一支把「差在哪」講出來，讓應付分頁能顯示
    「已指派 N 家但未填委外金額，填了就會自動建立應付」。
    """
    from sqlalchemy import text as _t
    rows = (await db.execute(_t("""
        SELECT pv.vendor_id,
               COALESCE(v.vendor_name, '(廠商 ' || pv.vendor_id || ')') AS vendor_name,
               pv.role,
               COALESCE(pv.contract_amount, 0) AS contract_amount,
               cp.id AS project_id,
               EXISTS (SELECT 1 FROM erp_vendor_payables p
                        WHERE p.erp_quotation_id = q.id
                          AND p.vendor_name = v.vendor_name) AS has_payable
          FROM erp_quotations q
          JOIN contract_projects cp
            ON cp.case_code = q.case_code OR cp.project_code = q.project_code
          JOIN project_vendor_association pv ON pv.project_id = cp.id
          LEFT JOIN partner_vendors v ON v.id = pv.vendor_id
         WHERE q.id = :qid AND q.deleted_at IS NULL
    """), {"qid": req.erp_quotation_id})).all()

    items = []
    for vendor_id, vendor_name, role, amount, project_id, has_payable in rows:
        if has_payable:
            continue
        items.append({
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "role": role,
            "contract_amount": float(amount or 0),
            "project_id": project_id,
            # 沒有應付的兩種原因要分得出來：填了金額卻沒建（＝橋斷了，weekly 106 會紅）
            # vs 根本沒填金額（＝待填報，不是故障）
            "reason": "未填委外金額" if not amount else "已填金額但尚未建立應付",
        })
    return SuccessResponse(data={"items": items, "total": len(items)})
