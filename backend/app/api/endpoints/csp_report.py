"""
CSP 違規回報收集端點

2026-08-19 建立。起因是一個**無法證偽的計畫**：

`get_default_csp()` 以 Report-Only 上線時，寫的是「先觀察一段時間，確認零違規再轉強制」。
但實測 prod 標頭發現 —— `Content-Security-Policy-Report-Only` **既沒有 `report-uri`
也沒有 `report-to`**（標頭裡那個 `Report-To` 是 Cloudflare 的 NEL，與 CSP 無關）。

也就是說：瀏覽器算出違規後，回報給沒有人。
「觀察一段時間」永遠不會有資料，「零違規」永遠會成立 —— 因為根本沒在收。
這是本專案反覆出現的 L37 靜默失敗譜系：機制裝好了、看起來正確、但不產生訊號。

──────────────────────────────────────────────────────────────────────
設計上刻意處理的兩件事（都是這一輪自己踩過的坑）
──────────────────────────────────────────────────────────────────────

**1. 這個端點本身就是負載來源。**
一個壞掉的頁面可以在幾秒內送出上千份報告。同一輪稍早，我把 Prometheus 以 60s
接上一個每次做 7 次 KV list 的端點，兩小時燒光 Cloudflare 一整天的額度。
教訓是：加監控時要問「這個東西被我加上去之後，會不會自己變成負載來源」。
所以這裡**在記憶體內去重**：同一組 (directive, blocked-uri) 每小時只寫一行 log，
其餘只累加計數。爆量時 log 不會被灌爆，而次數仍然看得到。

**2. 報告內容不可原樣寫進 log。**
CSP 報告的 `document-uri` / `referrer` 會帶完整網址，而網址可能含 token
（`?code=`、`#access_token=` 之類）。所以**白名單取欄位、且對 URI 去查詢字串**。
「現在沒洩」不等於「不會洩」—— 輸出契約要用白名單，不是靠相信來源乾淨。

端點刻意**不需認證**：瀏覽器送 CSP 報告時不會帶憑證，要求認證等同關掉回報。
代價是它對外開放，因此有限流 + 大小上限 + 不回傳任何內容。
"""

import json
import logging
import time
from threading import Lock
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response

from app.core.rate_limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security", tags=["資安管理"])

# 單份報告的大小上限。正常的 CSP 報告是幾百 bytes；
# 超過這個數量級的東西不是瀏覽器送的，直接丟掉不解析。
MAX_BODY_BYTES = 8 * 1024

# 同一組 (directive, blocked-uri) 的 log 冷卻時間
DEDUPE_WINDOW_SECONDS = 3600

# 去重表的容量上限 —— 沒有上限的話，攻擊者只要每次送不同的 blocked-uri
# 就能把這張表撐爆記憶體。滿了就整批清掉重來（寧可多寫幾行 log，不要吃掉記憶體）。
MAX_TRACKED_KEYS = 500

_seen: dict[tuple[str, str], dict] = {}
_lock = Lock()


def _strip_query(uri: str) -> str:
    """
    去掉查詢字串與 fragment —— OAuth 的 code / access_token 就住在那裡。
    保留 scheme + host + path，那已足夠判斷是哪個來源被擋。
    """
    if not uri or uri in ("self", "inline", "eval", "data", "blob"):
        return uri or ""
    try:
        p = urlsplit(uri)
        if not p.scheme and not p.netloc:
            return uri.split("?")[0][:200]
        return f"{p.scheme}://{p.netloc}{p.path}"[:200]
    except ValueError:
        return "<unparsable>"


def _should_log(directive: str, blocked: str) -> tuple[bool, int]:
    """
    回傳 (要不要寫 log, 這組在本視窗內累積的次數)。

    第一次出現就寫，之後一小時內只累加。這樣「新出現的違規」會立刻看得到，
    而「已知的違規一直在發生」不會把 log 洗掉。
    """
    key = (directive, blocked)
    now = time.time()
    with _lock:
        if len(_seen) >= MAX_TRACKED_KEYS:
            _seen.clear()
        entry = _seen.get(key)
        if entry is None or now - entry["first"] > DEDUPE_WINDOW_SECONDS:
            _seen[key] = {"first": now, "count": 1}
            return True, 1
        entry["count"] += 1
        return False, entry["count"]


@router.post("/csp-report", include_in_schema=False)
@limiter.limit("60/minute")
async def collect_csp_report(request: Request) -> Response:
    """
    接收瀏覽器的 CSP 違規回報。

    一律回 204 —— 包含解析失敗的情況。這個端點的存在與否、能不能解析某份報告，
    都不該讓外面看出來；而瀏覽器也不會對回應內容做任何事。
    """
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return Response(status_code=204)

    try:
        payload = json.loads(raw or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status_code=204)

    # report-uri 送的是 {"csp-report": {...}}；
    # 較新的 Reporting API（report-to）送的是一個陣列，每項在 body 底下。
    reports = []
    if isinstance(payload, dict) and "csp-report" in payload:
        reports = [payload["csp-report"]]
    elif isinstance(payload, list):
        reports = [r.get("body", {}) for r in payload if isinstance(r, dict)]
    elif isinstance(payload, dict):
        reports = [payload]

    for rep in reports:
        if not isinstance(rep, dict):
            continue
        # ⚠️ 白名單取欄位。不要 `logger.info(rep)` —— 那會把整份報告
        #    （含帶 token 的完整網址）原樣寫進 log。
        directive = str(rep.get("effective-directive") or rep.get("violated-directive") or "?")[:80]
        blocked = _strip_query(str(rep.get("blocked-uri") or "?"))
        document = _strip_query(str(rep.get("document-uri") or "?"))
        disposition = str(rep.get("disposition") or "report")[:20]

        write, count = _should_log(directive, blocked)
        if write:
            logger.warning(
                "[CSP-VIOLATION] directive=%s blocked=%s document=%s disposition=%s",
                directive, blocked, document, disposition,
            )
        elif count in (10, 100, 1000):
            # 只在數量級跨越時再出一次聲，讓「持續大量發生」不會完全消失在去重裡
            logger.warning(
                "[CSP-VIOLATION] directive=%s blocked=%s 本小時已累積 %d 次",
                directive, blocked, count,
            )

    return Response(status_code=204)
