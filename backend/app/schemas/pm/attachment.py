"""案件附件回應 schema（SSOT）。

## 為什麼要有這一份

2026-08-22：`pm/attachments.py` 的列表回應是**手寫 dict**，而 08-19 加的
`doc_type` 沒有被加進去 ⇒ 前端「類型」欄永遠顯示「—」。

危險的不是漏一個欄位，是**它漏得無聲無息**：

* 前端型別把它宣告成 `doc_type?: string | null`，`undefined` 是合法值，
  意思是「還沒有人分類過」—— 與「後端根本沒送」在畫面上長得一模一樣；
* tsc 抓不到（optional 欄位）；
* `model_response_field_reach_audit`（weekly 61）也抓不到 ——
  它比對的是 **ORM 類別 ↔ Pydantic schema 類別**，而手寫 dict
  沒有 schema 可比，**整個端點在那支檢核的座標系外**。

⇒ 定義 schema 不只是為了「規範好看」，是為了讓這個端點**進入既有檢核的
視野**。這與 08-21 那條判準同源：座標系裡沒有的維度，檢核再多也照不到。

## 欄位取捨

刻意不對外的欄位寫在 `model_response_field_reach_audit` 的
`INTENTIONALLY_INTERNAL`，每一條都要有理由 —— 沒有理由的豁免等於沒有豁免。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CaseAttachmentResponse(BaseModel):
    """對應 `pm_case_attachments` 的對外形狀。

    ⚠️ 與 `frontend/src/types/attachment.ts` 的 `CaseAttachment` 是一組契約，
    改這裡要同步改那裡（08-18 立的「契約鏈第三面」：Response→前端型別）。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    #: 對外一律給原始檔名（`original_name`），沒有才退回儲存檔名
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    #: `generated_quotation`／`signed_quotation`／`other`；
    #: **`None` 代表「還沒有人分類過」，與 `other` 意思不同**
    doc_type: Optional[str] = None
    notes: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: Optional[str] = None


class CaseAttachmentListResponse(BaseModel):
    success: bool = True
    attachments: List[CaseAttachmentResponse]
    total: int
