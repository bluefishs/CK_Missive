"""
跨系統通知投遞 —— 讓別的 repo 把告警併進每日晨報

2026-08-20 建立。起因是 CK_Website 的治理告警整層送不出去：五條檢查
（admin-audit / secret-drift / contract-probe / cross-repo-health / sso-health）
沒有一條有出口，其中四條卡在同一個從未設定的 SSO_HEALTH_SLACK_WEBHOOK，
第五條連 alert 函式都沒有。

08-20 pilemgmt 後端卡死那次展示了後果：ck-sso-health 每 15 分鐘正確報一次
unhealthy=1 resilience=DEGRADED，連續九次（偵測延遲只有 5 分鐘），
但每一次都只是寫一行 log。兩小時後才由人手動發現。
偵測從來不是問題，問題是那九次警報沒有任何一次離開過本機。

為什麼是 queue_digest 而不是直接推播
------------------------------------
LINE 免費月配額 200 則、軟上限 185。2026-08-20 本月已用 93 則而月份才過
三分之二，推估月底約 144 —— 餘裕不足以再開一個直接推播的來源。
queue_digest 由每日 07:30 晨報一次帶走併成一則，額外推播數為 0。

加監控時要先問「這個東西被我加上去之後，會不會自己變成負載來源」。
同一週已經有過反例 —— 把 Prometheus 以 60s 接上一個每請求做 7 次 KV list
的端點，兩小時燒光 Cloudflare 一整天的額度。

為什麼同時接受兩種 body
----------------------
那四支腳本原本是寫給 Slack incoming webhook 的，送 {"text": "..."}。
接受裸 text 讓它們只需改「送去哪、加一個 header」，不必動訊息組裝。

已知限制（不要當成已解決）
--------------------------
下面這個 `require_scope("admin:system")` **目前不提供任何授權控制**。

2026-08-21 與 ck-missive session 協同查證的結論比「過度授權」更嚴重：
`require_scope` 只驗 scope **名稱合不合法**，從不檢查這把 token 有沒有被
授予它（`_ALL_SCOPES = VALID_SCOPES`）。所以
`require_scope("admin:system")` 與 `require_scope("read:kg")` 效果完全相同 ——
**有 token 就過**。

也就是說：呼叫端為了送一則通知而持有的憑證，實際上同時能讀 KG、改 agent、
跑備份。而這行程式碼**讀起來像有授權控制，那比沒有更糟** ——
下一個人會以為這裡已經收斂過了。

寫成 "admin:system" 而不是留白，是為了在對照表真的生效那天不必回頭改；
在那之前它是宣告意圖，不是防線。真正的修法要動 MCP_SERVICE_TOKEN 的發放
方式，而 Hermes／LINE／CK_Website 三方共用同一把，屬跨 repo 決策。
已登記於 CK_Missive `docs/architecture/OPEN_ITEMS_20260819.md` B9。

在那之前，呼叫端限於本機同一台機器上的治理腳本。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.service_auth import require_scope
from app.services.integration.line_digest_buffer import queue_digest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notify", tags=["跨系統通知"])

# 晨報把當日所有主題併成一則推播，LINE 單則有長度上限，
# 任何一個來源灌爆都會拖垮整封晨報。
# 超長拒收而不截斷 —— 截斷會產生「看起來完整、其實少了結論」的訊息。
MAX_TEXT_LEN = 800
MAX_TOPIC_LEN = 40
DEFAULT_TOPIC = "治理告警"


class DigestIn(BaseModel):
    """
    兩種都收：
      {"topic": "SSO 健康", "text": "..."}   明確指定主題
      {"text": "..."}                        Slack webhook 相容，主題用預設值
    """

    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LEN,
                      description="內容；超長請自行摘要，這裡不截斷而是拒收")
    topic: Optional[str] = Field(None, max_length=MAX_TOPIC_LEN,
                                 description="主題（會成為晨報裡的分段標題）")

    @model_validator(mode="after")
    def _fill_topic(self):
        # 空字串與 None 一律視為未指定 —— 空主題會讓晨報出現一個沒有標題的段落
        if not (self.topic or "").strip():
            self.topic = DEFAULT_TOPIC
        return self


@router.post("/digest", status_code=202, summary="把一則告警併入每日晨報（不即時推播）")
async def post_digest(
    body: DigestIn,
    _auth: bool = Depends(require_scope("admin:system")),
) -> dict:
    """
    把一段文字排入 LINE 晨報摘要。

    不會即時送出 —— 由每日 07:30 的 morning_report_job 一次帶走。
    需要即時通知的情境不該用這個端點（而在加之前，請先確認月配額撐得住）。

    回 202 而不是 200：這是「已收下、稍後處理」，不是「已送達」。
    兩者的差別在通知系統裡很重要 —— 回 200 會讓呼叫端以為使用者已經看到了。
    """
    topic = (body.topic or DEFAULT_TOPIC).strip()
    ok = await queue_digest(topic, body.text.strip())
    if not ok:
        # queue_digest 自身吞掉所有例外（best-effort 通知層，ADR-0028），
        # 回 False 代表連 in-memory fallback 都沒收下 —— 那是真的沒排進去。
        # 這裡不吞：呼叫端有權知道它的告警沒有被接受。
        logger.warning("[notify] queue_digest 拒絕收下 topic=%s", topic[:40])
        raise HTTPException(status_code=503, detail="digest 緩衝不可用，本則未排入")

    logger.info("[notify] digest 已排入 topic=%s len=%d", topic[:40], len(body.text))
    return {"queued": True, "topic": topic, "delivery": "每日 07:30 晨報"}
