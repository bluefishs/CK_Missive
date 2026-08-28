# 待辦與待決議題總表（2026-08-19 收斂）

> 建立：2026-08-19
> 用途：這一輪跨越斷電復原、標案三缺陷、ERP 一條龍、既有 XLS 匯入，
> 產生的待辦散在四份文件與十幾個 commit 裡。**這一份是唯一的入口**，
> 不重複內容，只指路並標明狀態。

---

## A. 需要 owner 決定（我不會自己做）

| # | 議題 | 為什麼需要你決定 | 詳見 |
|---|---|---|---|
| A1 | **實際執行匯入**（彙整表 277 列／回簽 5 檔） | 寫入業務資料的時機是你的判斷（可能想先確認備份）。功能已驗證可用 | `QUOTATION_LIFECYCLE_PLAN` §4 |
| A2 | **報價單狀態機**是否採 `draft → issued → signed → confirmed` | 動的是既有 75 筆 `confirmed` 的語意周邊 | 同上 §1.2 |
| A3 | **可見性策略** A（只加篩選鈕，建議）／B（預設只看自己） | B 會讓 77 張 `created_by` 為 NULL 的舊資料在預設檢視中消失 | 同上 §2.2 |
| A4 | **77 張報價單的 `created_by`** 留 NULL 還是回填 | 回填需要你指認每張是誰開的，我無從得知 | 同上 §2 |
| A5 | **回簽是否為成案的必要條件** | 若是，只能對新案件生效（既有 88 件無一有回簽檔） | 同上 §1.2 |
| A6 | **兩支 Logon 排程需提權啟用** | `Enable-ScheduledTask` 一般權限回 `Access is denied` | `unexpected-shutdown-recovery` §0 |
| A7 | **發票號在哪** | 兩份彙整表 25 欄逐一確認**都沒有發票號**，只有發票日期 | `QUOTATION_LIFECYCLE_PLAN` §6 |
| A8 | **角色模型**：先做 A（`position` 表達職稱）還是直接 B（RBAC） | 取決於人資站點的時程 —— **順序不能顛倒** | `ROLE_MODEL_PLAN` §4 |
| A9 | **`D:\tmp` 18 個檔案**（7/14 起累積）是否清理 | 非本輪產生，但確實是資料四散的來源 | — |
| A10 | **✅ 已由 pile session 處理（08-24：62 個端點收斂、真缺口 319→161），可降級。**原文：**CK_PileMgmt 確認有公開外洩，而它沒有 session 在處理** —— **完整診斷已落檔：`PILE_AUTH_GAP_20260821.md`**（含公網實測證據、48 條控制點端點、⚠️ 含爬蟲任務 cancel/pause/resume 等**控制**類、修法判準）。2026-08-21 再次公網實測未帶憑證仍 200（22 縣市控制點統計、含衛星追蹤站）| 2026-08-21 跨 repo 探測：395 條無認證端點，其中含 **11,025 個控制點**的資料。其餘四個 repo 當日都已開 session 自行處理，pile 沒有 ⇒ **需要你指派**。工具已可直接用：`AUTH_AUDIT_CONTAINER=ck_pilemgmt-backend-1 python scripts/checks/public_endpoint_auth_audit.py`（⚠️ 先依判準 11 由 pile 自己列白名單） | 本檔判準 11 |
| A11 | **`require_scope` 的 token→scope 對照要不要做**（原 B9 升級為需決策） | 跨 repo：`MCP_SERVICE_TOKEN` 由 Hermes／LINE／CK_Website 共用，改成多把或帶 scope 宣告要各消費端同步改。2026-08-21 已先讓它**出聲**（每次通過都記 log 說明未做對照），不再只寫在註解裡 | 本檔 B9 |
| A12 | **CK_Website 沒有異地備份** | 四系統的 SSO IdP。08-11 已知 `ck-kv-snapshot` 失敗（PM2 非互動環境缺 `CLOUDFLARE_API_TOKEN`），最新可用備份停在 07-18；NAS 上完全沒有目錄 | `RETRO_AND_PLAN_20260824` |
| A13 | **dataform frontend／ORS 埠是否收斂** | 收斂會移除 CLAUDE.md 明載的「從別台機器開 UI」功能。⚠️ ORS `0.0.0.0:8080` 自區網 `/ors/v2/health` 回 200 ⇒ 別人可用我們的路徑運算資源（§0） | 同上 |
| A14 | **dataform 的 NAS 備份路徑與 push 授權** | 動到共用資源與遠端 | 同上 |
| A15 | **pile 的 82 條公開業務查詢是否去識別化** | 已補 60/min 防爬取；公開與否屬產品決策 | 同上 |
| A16 | **DT 點雲／裂縫影像的內容認證** | 08-09 判為產品決策；**新論據＝頻寬成本**（§0） | 同上 |
| A17 | **`FT_StorageTank` NAS 備份停在 54 天前，且該專案無 session** | 需指派 | 同上 |
| ~~A18~~ | ~~**L43 的 503 防禦只覆蓋了一半**~~ | **2026-08-26 由 CK_AaaP 推翻前提，已撤銷**。我原本要 owner 去 CF Dashboard 查「該 tunnel 的 health path 指向哪一個」—— **那個角色根本不存在**。他們從外部打四條路徑證明：任意路徑都被原樣轉發到同一個 origin service，由應用決定回什麼 ⇒ CF Tunnel 的 ingress 是 **hostname → service** 的映射，**它不會挑一個 health path 去探 origin**（除非另掛 CF Load Balancer 並設 origin health monitor，那是 LB 的設定不是 tunnel 的）。⇒ 容器 healthcheck 指 `/health`（正確、實測 `ok=True docs=2023 KG=49919`）與 CF 是**兩件互不相干的事**，L43 的防禦沒有缺口。`configs/cloudflare-tunnel.yml` 不生效仍然是事實（已在檔頭標明），但它不生效**不代表有另一份設定在別處決定 health path** | 無需 owner 動作。⚠️ 副產品已落地：他們同時指出本站 **SPA catch-all 讓任意路徑回 200 + text/html**，而 `/api/*` 才回 404 JSON ⇒ **「200 就是通過」會把 catch-all 讀成認證繞過**。已加進 `probe_fingerprint_guard`（weekly 67）當第二種指紋 |

| A19 | **「假死自動復原」現在是空的 —— 要不要補回來** | `ecosystem.config.js` 宣告的 `health-watchdog`（每 2 分鐘探 `/health`、連 2 次失敗就重啟）**沒有在 PM2 上跑**（`pm2 jlist` 的 14 支全屬別的 repo）。容器端看似有覆蓋其實沒有：healthcheck 只會把容器標成 **unhealthy**，而 **Docker 不會因為 unhealthy 就重啟容器**（`restart: always` 只在程序結束時作用）⇒ 一個「還活著但卡住」的 backend 會停在 unhealthy 不動。08-24 那次「56 容器 0 非健康」量的是**狀態**，不是**復原能力**。三選一：① `pm2 start ecosystem.config.js --only health-watchdog`（最快，但 PM2 是第三個排程層、只有註冊覆蓋沒有執行結果哨兵）② 加 container autoheal ③ 明確接受「假死靠人看」並把 `health-watchdog.sh` 歸檔 | `ecosystem.config.js` 檔頭（2026-08-27 已標註三支的實際接手者）|
| A20 | **CSP 轉強制的時機** | 判準已經可查證：`increase(csp_violations_total[7d]) == 0`，**且 backend 起來要滿 7 天**（counter 隨重啟歸零）。最早可判日 **2026-09-03**。已知一筆違規已修（`accounts.google.com/gsi/style`，`style-src` 已補）。轉強制只改一個參數名，回退成本很低 —— 但要你決定何時開那個維護窗 | `docs/runbooks/csp-report-only-to-enforce.md` |
| A21 | **Facade B 方案 60 天 trial 已到期 28 天** | 到期日 2026-07-30，儀表板 §10 一直列著「待 owner 結案」。建議（RETRO_20260730 §4 已寫）：**全保留 + 停止設成長目標 + 往後新增 facade 須先有 ≥3 既存 caller**。這不需要新的分析，只需要你說一句「就這樣」，然後把它從 §10 拿掉 —— **一個永遠不結案的待辦，會訓練人忽略整張待辦表** | `RETRO_20260730_POST_SWEEP_REVIEW.md` §4 |

| A22 | **`user_sessions` 的 `expires_at` 與 `created_at` 存在不同時區** | 2026-08-27 實測同一列：`created_at=11:26:33`（DB 本地 Asia/Taipei，`server_default=func.now()`）而 `expires_at=04:26:33`（Python `datetime.utcnow()`）⇒ **每一筆 session 一建立就「已過期 7 小時」**，欄位型別是 `timestamp without time zone`，沒有任何一端會做轉換。**應用本身是一致的**（`session_repository` 兩處都用 `UserSession.expires_at > datetime.utcnow()`），所以功能正常 —— 壞的是**任何拿 `expires_at` 跟 DB `NOW()` 比的東西**：`admin_backup_smoke_test.py:55` 就是這樣寫的，它永遠找不到有效 session、每次都新插一筆（靠 fallback 才沒出事）；`ui_smoke_auth.py:130` 的註解已經記過同一件事。⚠️ **我沒有動它** —— 時區慣例屬「帳號／權限架構」，而本專案 SSO 反覆回歸（L74／L78／L80）的教訓都指向同一件事：這一區改動的失敗不在 happy path。要修的話兩條路（統一為 UTC ／統一為 DB `func.now()`），**都需要先盤點所有讀這三個欄位的地方**，是獨立一輪的工作 | 本輪由 owner console 的 `auth/renew 401` 追出（該 401 本身來自 CK_Website 的 IdP 端，Missive 側無對應錯誤；11:26 有新 session 建立＝已重新登入自行復原）|

| A23 | **4 個權限沒有任何角色拿得到 —— 命名怎麼收** | 2026-08-27 七層鏈路盤點。`hasPermission` **只對 superuser 短路，admin 走正常過濾** ⇒ 這四個功能除了超級管理員之外沒有人做得了。**`projects:write`**（erp/expenses 的 approve／batch-approve／reject／delete 四支端點＋前端「新增承攬案件」與費用審核）與 **`admin:access`**（ERPEInvoiceSyncPage 管理區塊）**兩份 SSOT 都沒有這個名字** ⇒ 權限編輯畫面不會列出，**任何人都無法授予**；**`operational:write`／`operational:approve`** 在兩份 SSOT 裡都有、只是還沒分派 ⇒ 會以「未分派紅點」出現，你在畫面上就能給（⚠️ 但對應端點只要 `require_auth`，目前是前端擋、後端不擋）。**待你決**：`projects:write` 改成 `projects:create`／新開 `expenses:approve`／或補進 SSOT；`admin:access` 多半應改成 `admin:settings` | `scripts/checks/permission_unreachable_baseline.json`（每條註明理由）；檢核＝`role_permissions_consistency_check` 第 5 項 |
| A24 | **兩位 admin 的實際權限是唯讀 6 項** | 張坤樹（id 29）與賴秀玲（id 30）role='admin'，而 `users.permissions` 只有 `documents:read／projects:read／agencies:read／vendors:read／calendar:read／reports:view`，**角色定義是 33 項**。兩人 `last_login` 皆為 NULL ⇒ 從沒登入過，所以沒有人發現。成因同 A25：改角色不會改既有使用者的權限。**待你決**：在 `/admin/permissions/admin` 按「同步至所有用戶」即可補齊（會一併影響其他 3 位 admin，但他們已經是 33 項、屬「已對齊」會被略過）| 2026-08-27 盤點；新的 `pending_sync_users` 計數會顯示 admin=2 |
| A25 | **6 位在職業務同仁的權限尚未套用角色定義** | 你 08-27 11:22 把「業務同仁」設成 14 項含 `vendors:create/edit`，但 `update_role_permissions` 只寫角色定義表 —— `role_permissions` 只在**建立新帳號**那一刻被讀一次。曾廷睿／邱元宏／張浩翊／馮俊翔 各 8 項（缺 6）、**王駿穠與賴柏霖各只有 5 項唯讀**（缺 9，連 `documents:create` 都沒有）。何丞穎 `permissions` 是 NULL 但已停用、不受同步影響 | 修法已上線：該頁現在會顯示「尚未套用到 N 位在職使用者」，儲存時也會提醒。按右上角「同步至所有用戶」執行 |

| A26 | **⚠️ ERP／財務資料現在沒有被角色保護 —— 是否本來就不該人人可見** | `erp/` 端點 **60 支只有 `require_auth`**（4 支 `require_permission`、1 支 `require_admin`）。實測 uid=7（`role='staff'`、`users.permissions` 只有 5 項唯讀、**選單完全看不到 ERP**）直接打 API：統一帳本 200／5 筆、營運帳目 200／3 筆、報價單 200／5 筆、ERP 財務總覽 200 ⇒ **唯一的屏障是「選單看不到」，而選單不是安全機制**。修法是把 router 從 `require_auth` 改為 `require_permission("reports:erp:view")`（加在 **router 層**，逐一改會漏）。⚠️ **這會改變現況行為**，需要你先確認「ERP 資料本來就不該人人可見」；⚠️ 且**順序不能顛倒** —— 目前連兩位 `admin` 都只有 6 項唯讀權限（A24），端點一鎖他們立刻被擋在外面，**必須先同步使用者權限再鎖端點** | `ROLE_MODEL_PLAN` §6.1／§7 階段 0 |
| A27 | **角色扁平：三個職能角色要不要開**（owner 08-27 提「財務角色／高階主管／ERP 財務與營運等管理」） | 現況 `reports:erp:view` **只有 `admin` 這一個角色擁有** ⇒ 想讓財務看 ERP 的 9 個選單，唯一做法是給 `admin`，**順帶給 23 個系統管理選單＋使用者權限管理＋部署＋備份＋資安**。賴秀玲現在的 role 正是 `admin`。✅ 好消息：`users.role` **沒有任何 CHECK 約束**、`role_permissions` 是普通表 ⇒ **加角色零 schema 成本**，`/admin/permissions/:role` 現成可編輯。建議 `finance`／`ops`／`exec` 三個；**`exec` 刻意設計成全域唯讀**（預設是「不給」而不是「admin 減幾項」，新增功能時才不會自動放行）。**待你決**：三個角色的名稱與中文顯示、`exec` 是否需要簽核類寫入 | `ROLE_MODEL_PLAN` §6.3／§7 階段 1 |
| A28 | **`CK_Missive-SOUL-Mirror-Sync` 這支排程只剩下製造紅燈的功能 —— 要不要移除** | 它跑的是 `sync_soul_to_hermes.sh --apply`，而那支腳本**自 2026-08-02 起被寫成拒絕執行**（commit `53195de1`「把『不應執行』寫成 exit —— 註解擋不住 scheduler」）：目標檔不生效（Hermes `active_profile=meta`，寫的是 root 檔）、前提已被 ADR-CK-003 推翻（坤哥與 meta 是**不同意識體**，內容不同是設計）、真改成寫 meta 會蓋掉 06-16 的業務查詢強制規則。實測 `LastTaskResult=3`，`soul_mirror_drift_check` 也直接印「**不要**跑這支」。⇒ 排程存在的唯一效果是每次稽核固定三個紅燈（Disabled／9 天沒跑／沒補跑），**而沒有任何人能處理它們**，那與「連 9 週 RED 無人知」是同一個下場。⚠️ **2026-08-27 我先把它啟用了，那是錯的** —— 我只看了稽核的紅燈，沒有先問這支排程在做什麼；發現後已還原為 `Disabled`。刪除動作被權限守衛擋下（正確），因此列為需你決定。**還原用**：任務 XML 已備份於 `%TEMP%\soul_mirror_task_backup.xml`（3,356 bytes）| `schtasks /delete /TN CK_Missive-SOUL-Mirror-Sync /F`；腳本本身留在 repo 不動 |

---

| A29 | **`ck_missive_frontend` 這個容器：健康、陳舊、外面連不到、也不在使用者路徑上 —— 要不要留** | 2026-08-28 實測四件事合起來才看得懂：① `docker ps` 顯示 **Up 8 days (healthy)**，容器內 `wget /nginx-health` 也回 `healthy`；② **但發布出去的埠是死的** —— `curl http://127.0.0.1:3000/` 回 `000`（連不上），因為執行中的容器仍是 `80/tcp → 3000`，而容器內 nginx 聽的是 3000；③ **它沒有任何 mount**，供的是 image 裡烘進去的內容，`index.html` 日期 **Jun 2**（三個月前的 build）；④ **公網不是它在供** —— 公網 index.html 引用 `assets/main-NZ6nPzVL.js`，與我剛 build 的本地 dist **完全一致**，而 `frontend/dist` 是 bind mount 進 **backend**（`docker-compose.production.yml:310`），由 FastAPI 供 SPA。<br>⚠️ **我自己的半接通**：08-27 我把 compose 從 `"3000:80"` 改成 `"3000:3000"`，**但沒有重建容器** ⇒ 修法在檔案裡，不在系統裡。<br>⚠️ **而我不建議現在重建** —— 重建之後它會變成「一個能連的埠，供著三個月前的應用」，那比一個死埠更危險。<br>⇒ 真正該問的是**這個容器還該不該存在**：沒有 mount、沒有流量、內容陳舊，而 healthcheck 永遠是綠的。 | **待你決**：①移除它（compose 拿掉該 service）②保留但重建＋改為掛 `frontend/dist`，讓它真的能供最新版 ③維持現狀並在 compose 註明「刻意不使用」。<br>⚠️ 另註：它綁的是 `0.0.0.0:3000` 而非 `127.0.0.1`，與 08-10「資料層全綁 127.0.0.1」的處置不一致（雖然目前那個埠是死的） |

| A30 | **`actual_llm_provider` 空了 27 天 —— 根因已定案，修法二選一需你決定** | 每日 pipeline 的 `shadow_baseline` 長期 RED（真人平均 19.1s／合成 40.4s），而**指不出是哪個 LLM**：`provider` 欄只是通道標籤（web→`gemma-local`），真答案在 `actual_llm_provider`，**最後一次有值是 2026-08-01**。<br>**根因（已驗證，非推論）**：合成跑在 `agent_orchestrator.py:457` 的 `asyncio.create_task(_run_tool_loop())` **子任務**裡，而 `set_actual_provider` 就在那個子任務的 context 副本中執行。六行腳本實測：async generator **會**把 ContextVar 傳回父層，**`create_task` 與 `gather` 都不會** ⇒ 父層的 `fire_shadow_trace` 永遠讀到 None。<br>⚠️ 過程中我三個假設錯了兩個（`wait_for` 阻斷／走 stream fallback），一個因為**我自己剛部署過、日誌只剩一分鐘**而驗不了。現場證據：容器起來 13 分鐘內 30 次查詢、**5 次 `synthesis_end`**，而同期 trace 仍全空。 | **待你決**（動到核心推論接線，我沒有自行實作）：<br>**①（正解）** ContextVar 改存**可變容器**，請求進入時設一次 —— 子任務共用同一個物件，改它父層看得到；但要動請求生命週期。<br>**②（一行）** `shadow_logger` 在 ContextVar 為空時退回 `connector._last_provider`（該屬性已存在，`agent_orchestrator:80` 正是這樣取 model_used）—— 但**跨併發請求會互相污染**。本站真人一天 2 次、污染機率低，可是那正是「日後沒人會質疑的錯數字」。 |

| A31 | ⭐⭐ **兩個雲端模型都已下架，agent 已在本地慢速備援上跑了約 27 天 —— 換成哪一個要你決** | 追 `actual_llm_provider` 為何全空時追到的，**比原本要查的嚴重得多**。<br>**現場日誌**：`Synthesis timed out after 35s` → `Groq circuit OPEN → skip 直接走 NVIDIA` → `NVIDIA circuit OPEN → skip 直接走 Ollama`。<br>**錯誤**：Groq 回 **HTTP 404**、NVIDIA 回 **HTTP 410 Gone**。<br>**已向兩家的 models API 查證（不是推論）**：API key 都有效（models 端點皆回 200），而設定的模型**都不在清單裡**：<br>　· `GROQ_DEFAULT_MODEL = llama-3.3-70b-versatile` → **已下架**<br>　· `NVIDIA_DEFAULT_MODEL = nvidia/llama-3.3-nemotron-super-49b-v1.5` → **已下架**<br>⇒ 每次推論都退到本地 ollama（記憶：p50 52.8s），合成 35s 逾時 ⇒ 答案走 fallback、`actual_llm_provider` 因為 `chat_completion` 從未成功返回而永遠空。<br>⚠️ 這也解釋了 `shadow_baseline` 連續 27 天 RED，以及 `actual_llm_provider` 最後一次有值正是 **2026-08-01**。 | **待你決**：換哪一個模型。<br>Groq 現有可用（實查）：`openai/gpt-oss-120b`／`openai/gpt-oss-20b`／`qwen/qwen3.6-27b`／`groq/compound`<br>NVIDIA 現有 nemotron 系列：`nvidia/llama-3.1-nemotron-70b-instruct`／`nvidia/llama-3.1-nemotron-51b-instruct`／`nvidia/llama-3.1-nemotron-ultra-253b-v1`<br>⚠️ 換模型會改變回答品質與 TPM 限制（`ai_connector.py:60` 的註解記著 llama-3.3-70b 的 TPM 是 12K，換模型要重看那個假設），且**不得引入新增費用**（`development-rules.md` §0）—— 兩家都要確認新模型仍在免費 tier。<br>⚠️ 我沒有自行改模型名：那是**會改變系統行為與成本**的決策。 |

| A32 | ⭐⭐ **175 筆 legacy 案號要不要轉成建案案號（工具已備妥，預設不寫入）** | owner 2026-08-27~28 確立：`case_code` = **建案案號**（案子的身分），而報價單彙整匯入把**報價單編號**寫了進去 ⇒ **175 個已承攬的案子無法成案**（`promote_to_project` 的新規則是「去掉 `_PM_`」，legacy 案號去不了），而它們的畫面看起來流程已經走完。<br>**dry-run 實測**（`scripts/sync/backfill_case_code_ck.py`）：待轉換 175／新案號互異 175／**與既有 292 個案號逐筆實查零相撞**／轉換後可直接成案 95／仍被防重擋 80／缺合約金額 0。<br>要一併替換的引用：pm_cases 175／報價單 175／承辦同仁 101。 | **待你決**：要不要跑 `--apply`。<br>執行前我會先做完整備份並再產一次 dry-run 給你對照。<br>⚠️ 舊編號保存在 `erp_quotations.legacy_quotation_no`（該欄位本來就為此存在）⇒ 轉換後仍可用舊編號回溯，回簽 PDF 掛回不受影響。 |
| A33 | **80 筆同名的案子：是「已建過只是沒接上」還是「不同案」** | A32 轉換後仍會被既有防重擋下的 80 筆，判準是「同名 + 同年度 + 同委託單位」。實測訊息長這樣：`同名承攬案件已存在：CK2026_01_01_008（南投縣政府115年度委外辦理圖根點清理…）`。<br>⇒ 多半是**已經建過案、只是 `case_code` 沒接上**，需要的是「接上」而不是「補建」。 | **待你決**：逐批確認後，是把它們的 `case_code` 指向既有承攬案件，還是確實要新建。<br>我不會自己判 —— 判錯會產生兩個代表同一件工作的承攬案件。 |
| A34 | **26 組分身（`B114-B003` vs `B114-B003-0`）怎麼處理** | 匯入只比對**完整** `case_code`，於是彙整表帶子號的那一側被當成新案建立，兩側案名完全相同。<br>⚠️ **26 組的「有碼那一側」都有金流** ⇒ **分身沒有金流是正常的，不要當成漏記帳去補**。<br>⚠️ 也**不要把子號當版次去掉** —— 實測推翻過：`B114-B026`（平鎮區土地協議市價查估）與 `B114-B026-2`（翠64透地雷達）是**完全不同的案子**，去尾碼會造成 4 組硬掛在一起、36 組重複建立。 | **待你決**：逐組確認要合併哪些、保留哪些。<br>合併是**語意變更**（兩筆併一筆），與 A32 的機械式替換風險不同級，應分開決定。 |
| A35 | **3 筆廠商「同一張單、兩個名字」哪個對** | `vendor_identity_ssot_audit`（weekly 70）RED：<br>　應付#47 自存「竣吉不動產估價師」 vs FK「竣吉不動產估價師事務所」<br>　應付#39 自存「**林晉廷**」 vs FK「**林宥廷**測量技師事務所」<br>　應付#51 自存「銢欣有限公司乃耳企業社」 vs FK「銢欣有限公司」<br>⚠️ **#39 是不同的字，不是簡稱差異** —— 比較像掛錯 `vendor_id`，而那代表**那筆錢會算到別人頭上**。 | **待你決**：三筆各以哪一個為準。<br>系統無法自己決定 —— 尤其當兩個名字是不同的人時。 |
| A36 | **金粟科技 320 萬應付（4 期）沒有合約經費** | `vendor_contract_payable_consistency`（weekly 69）：`CK2025_01_03_001` 有 4 期共 $3,200,000 的應付，而協力廠商那邊**沒有填合約經費**。<br>依你 2026-08-27 的規範「**合約經費是上位，應付在它之下執行**」⇒ 那 320 萬**沒有任何上限在管**。 | **待你決**：補填合約經費金額，或確認這個案子不走合約經費管控。 |
| A37 | **`careful-guard` 修好後的誤判要不要收斂** | 該守衛原本沒有 UTF-8 BOM ⇒ PS 5.1 cp950 解析失敗 ⇒ **12,491 次呼叫一次都沒攔到東西**（已修，實測危險刪除指令現在 exit 2 擋下）。<br>**代價**：修好後一小時內就擋下一個正常的 `git commit` —— 因為 commit message 裡引用了危險指令的字面值當說明。守衛掃的是**整個指令字串**，分不出「要執行的指令」與「heredoc／訊息裡的文字」。 | **待你決**：要不要讓它忽略 heredoc 與 `-m`／`-F` 之後的內容。<br>⚠️ **不要因為誤判就關掉它** —— 它壞了 30 天沒人發現，正是因為它從不出聲。目前繞法：`git commit -F <file>`。 |

| **A38** | 🔴🔴 **公文附件的異地備份只涵蓋 1,552 檔裡的 120 檔（92% 從未備份），而每天回報「全部已同步」** | 2026-08-28 起因是 CK_Website 的備份掃描回報 54 個檔案複製失敗（`ERROR 123` 路徑過長）。查證後**問題比他們診斷的更基本**：<br>**① 他們建議的修法已經做過了** —— `LongPathsEnabled` 登錄檔值**已是 1**，且用 .NET 長路徑 API 列舉全部 1,507 個備份檔，**最長來源路徑 213 字元、超過 260 的有 0 個**。⇒ 來源端乾淨。<br>**② 真正的缺口在涵蓋範圍**：<br>　　`backend/uploads` 實際 **1,552 檔 / 1.2G**<br>　　`manifest_20260828` 列出 **120 檔**<br>　　**在 uploads 但不在 manifest：1,432 檔（92%）**<br>**③ 而它每天回報正常**：08-22 到 08-28 七份 manifest 的數字**完全相同** —— `total=120 copied=0 skipped=120 removed=0 size=0.0MB`。「copied=0」被讀成「沒有新東西要備份」，實際是「它只看得到那 120 個」。<br>**④ 漏掉的正是最長檔名那些**（`2026/02/doc_885/357f752c_電115年02月25日_桃工用字第1150006974號_檢送...`）⇒ CK_Website 的 ERROR 123 指向的是真問題，只是機制不同。<br>**⑤ `attachments_latest` 最後修改停在 5 月 18 日**（1,169 檔 / 772M），而 7 個目錄快照停在 **2026-03-09** —— 舊機制（L49.5 改為 manifest O(1) 之前）的殘留，每次仍被複製到 NAS。<br>⚠️ `remote_backup.json` 的 `sync_enabled: False`，但 DB dump 確實有跑（`ck_missive_backup_20260828_015959.sql` 526MB，02:00）⇒ 那個旗標控制的**不是**整體備份，語意待查。 | **⚠️ 我沒有在重啟前動備份機制** —— 改備份是高風險操作，而重啟前不是做它的時機。<br>**待你決 + 需要先查清楚的**：<br>① manifest 為什麼只看得到 120 檔（掃描起點？過濾條件？長路徑在**掃描階段**就被跳過？）<br>② `sync_enabled: False` 的實際語意<br>③ 7 個 2026-03 的目錄快照與停在 5/18 的 `attachments_latest` 要不要清（**它們可能是那個時期附件的唯一副本，我不會自行刪**）<br>**這一條與 2026-08-24 的判準同族：備份成功 ≠ 備份到我們需要的東西。** |

## B. 已查明根因、尚未實作

| # | 議題 | 根因（已查證） | 規模 |
|---|---|---|---|
| ~~B1~~ | ~~**標案決標資訊全庫 0 筆**~~ | **2026-08-26 查證後根因與原記載完全不同，已修並接上排程**。原記「抓取端只抓招標公告、analytics 在分析從來沒進來的資料」—— **兩句都不準**：① dashboard 實打回 200／0.17s、`total_found=2286`、本週決標 11 筆、得標廠商 top 10 有真實公司名 ⇒ **它是活的**（即時查外部，不讀 DB）；② 真正的斷點是 **`detail_enrichment.py` 從建立起沒有任何人呼叫它**（全 repo 零 import）—— scheduler 的 `tender_pcc_enrichment_job` 跑的是名字很像的另一支（`enrichment.py`，做 ezbid↔PCC 配對）。它一跑就暴露四個 bug：`unit_id` 對 ezbid／pcc 是兩種東西（點分機關代碼 vs base64 pkPmsMain）⇒ org_ok=0；`_pick` 無優先序且命中「**是否**訂有底價」⇒ `base_price='否'`；`bidders` 收到廠商代碼與地址；SQL 參數未 CAST ⇒ 整筆 UPDATE 失敗、**且一筆壞掉後剩下全部陪葬**（統計上長得像「這些案子都沒資料」）| 四個 bug 全修，實測 `org_ok 5/5 enriched 5 errors 0`、`bidders=['合記書局','藝軒圖書','黎明書店']`（與 `tender_company_links` 一致）。已接排程 **每日 03:45**，只跑 ezbid 那一段（`unit_id` 本身就是 org_id、**不打 PCC**、零反爬風險）。⚠️ **`award_amount` 仍會是 0 且那是正確的** —— 實測該案 openfun 有 `決標資料:總決標金額是否公開` 但**沒有金額欄位**，即機關選擇不公開。L77「enrichment 死結」**完全不成立**（08-19 推翻預算那一半，今日推翻 org_id 這一半：實測 3 筆 PCC 詳情頁全 200、orgId 可取）|
| B2 | **報價單附件上傳與預覽** | `PreviewDrawer` 可重用；`ExistingAttachmentsList` 綁死 `DocumentAttachment` 型別 | 需新建共用元件 |
| ~~B3~~ | ~~**報價單入口在 ERP 側**~~ | **2026-08-27 複核已全數收束**。三段都在 `/pm/cases` 了：新增報價（08-20）／線上填明細（08-26）／**輸出報價單與 PDF（08-27）** —— 最後一段是 owner 指出的：「為何 `/erp/quotations/150` 會輸出報價單與 PDF，此機制應在 `/pm/cases`」。輸出抽成 `useQuotationExport` 兩頁共用（空工項提醒／`Content-Disposition` 檔名／PDF 預覽／blob 釋放時機四件事容易各自演化，複製一份等於承諾兩邊都要記得改）| 已完成 |
| ~~B4~~ | ~~**`/tender/ezbid/A.47.3` 定位不到**~~ | **2026-08-26 查證後原記載只對了一半，已修**。「`A.47.3` 是機關代碼不是標案 id」正確，但它暗示的修法（改路由參數）不成立：`SourceTenderLink` 用 `encodeURIComponent(ezbid_id)` ⇒ 斜線編成 `%2F`、**單段路徑 match 得到**；`LegacyTenderRedirect` 只在純數字時才導到 ezbid，`A.47.3` 走的是 PCC 分支 ⇒ **系統自己產生的連結都沒問題**，那個 URL 來自人手動輸入或舊書籤。DB 實測 ezbid_id 兩種格式：純數字 **37,980** 筆（舊）／`{機關}/{案號}` 含斜線 **11,470** 筆（08-02 站台改版後）| 真正缺的是**查不到時什麼都沒說**：原訊息「PCC 開放資料中查無此標案」①這是 ezbid 路由卻說 PCC，來源講錯；②**沒說出真正的問題** —— 使用者會讀成「這筆資料不存在」，實際上是**編號少了一半**，而那兩件事在畫面上長得一模一樣（同 08-20「空清單退化成數字」、同日 StaffPage「空表格 vs 載不到」）。已改為：偵測「只有機關代碼」的形態並明說、給出「用這個機關搜尋」的出口、外部連結依格式分派（含斜線走改版後的 `/detail/{機關}/{案號}`）。tsc EXIT=0 |
| ~~B5~~ | ~~**08-15 標案寫入 0 筆**~~ | **2026-08-26 查證後原描述兩處不準，已收束**。逐日攤開：08-15(六)／08-16(日)／08-22(六)／08-23(日) 是 0 **而那是正常的**（政府週末不發標，實測平日 780–1939 筆）；**真異常只有 08-17 週一**，而它不在原記載裡 ——原記把正常現象當異常，真正的異常反而沒被記下來。追 `cron_events`：`pcc_today_scrape`（每 2 小時、預期 12 次/日）在 **08-16~08-17 連續 48 小時 0 次執行**，同期 `health_check_broadcast` 跑了 208 次 ⇒ scheduler 活著、只有這一支停了。⚠️ `cron_silent_dormant_check` 門檻 4 小時卻沒報，**為什麼沒報查不出來**（daily 歷史只記步驟名不記內容）| 已加**第九條生命跡象**（commit `8b9e782c`）：既有那條看 `MAX(announce_date)`（政府公告日），而**爬蟲停擺後恢復會一次補回前幾天的 announce_date ⇒ 看起來完全正常**；新條目改看 `created_at` 並只算平日，**刻意不依賴 cron 機制本身**。鑑別力：過去 14 天逐日模擬，08-18／08-19 會報，其餘 12 天 0，**零誤報含所有週末** |
| B6 | **匯出表單格式** | owner 指示「先完成前述整合再議」；已知不輸出委託單位 ID | 待 A1 完成後 |
| B9 | **`require_scope` 是裝飾性的 —— token→scope 對照從未實作** | `_ALL_SCOPES = VALID_SCOPES`，所以 `require_scope("admin:system")` 與 `require_scope("read:kg")` 效果**完全相同**：有 token 就過，從不檢查這把 token 有沒有被授予該 scope | **具體後果**：CK_Website 為了送一則通知呼叫 `/api/notify/digest`（宣告 `admin:system`），實際拿到能讀 KG、改 agent、跑備份的憑證。⚠️ **要修需要跨 repo**：`MCP_SERVICE_TOKEN` 由 Hermes／LINE／CK_Website 共用，改成多把或帶 scope 宣告要各消費端同步 ⇒ **屬 owner 決策**。2026-08-21 已先讓它出聲（每次通過都記 log 說明未做對照），不再只寫在註解裡 |
| B8 | **廠商重複（勤典工程行／勤典測量工程行）** | ⛔ **owner 2026-08-20 決定不做**：「此非系統問題，實為人為填報機制要修正」。量測支持這個判斷 —— 5 組名稱相似裡**只有 1 組是真重複**（台電三個發電廠、工務局與用地科、「楊長燁加李雅倫」「祐鴻+昱緯+建倫」都是有意義的不同），自動判重會產生 4/5 假陽性 | **不要再提議加相似度比對**。另：補建的 137 件邀標案件裡 130 件的委託單位只有文字沒有連結，而 101 個不重複客戶名裡有「何明利」「劉庚霖之繼承人(4人)」「劉進財、孫瑟花」等**自然人地主** —— 那些本來就不該建成「廠商」，自動補建會把資料模型弄錯 |
| ~~B7~~ | ~~**管理動作按鈕對一般使用者可見但按下去 403**~~ | **2026-08-26 收束**。原記的 4 頁實查後只有 `/ai/erp-graph` 真的漏（另三頁都已有 `isAdmin` 且真的用在渲染上）；接著建 `admin_action_visibility_audit.py`（weekly 68）**自動掃全**，另抓到兩個原本不在清單裡的：`/ai/db-graph`（選單權限已是 `admin:settings`、**但路由沒鎖 ⇒ 直接打網址就進得去**）與 `/staff`（選單權限 `projects:read` ⇒ **一般同仁看得到，點進去是空表格＋統計全 0，看起來像「公司沒有同仁」**）| 三頁修法各不相同且都**不放寬端點權限**：erp-graph 分頁依 `isAdmin` 顯示／db-graph 路由補 `roles={['admin']}` 與選單一致／staff **只治症狀**（載不到要說出來、不給必然失敗的按鈕），該不該對一般同仁開放仍是 owner 的產品決策。⚠️ 這支檢核自己踩了兩個坑才有鑑別力，見 `scripts/checks/README.md` weekly 68 |

| B10 | **`scripts/hooks/post-commit-code-graph.sh` 從來沒有被安裝** | `.git/hooks/post-commit` 實際跑的是知識地圖增量更新，裡面 **grep 不到任何 `code-graph`** ⇒ 這支腳本存在於 repo，但沒有任何東西會執行它 | 規模小、風險低。要嘛併進現有 post-commit，要嘛歸檔。**判準是 `scripts/checks/README.md` 已經寫過的那一句：「這支東西壞掉的時候，會有人知道嗎？」** |
| B11 | **「有產出端、沒有消費端」這個維度沒有任何檢核在管** | 2026-08-27 一輪覆盤，**五個發現的形狀完全一樣**：版本綁定沒人帶／治理檢核讀空目錄／前端埠沒人聽而探針探別的埠／CSP 違規沒人看／部署腳本重啟不存在的程序。全部都不會報錯 | ⚠️ **刻意不做成通用掃描**：實測掃 `scripts/`（`checks/` 以外）81 支，25 支完全沒被提到、13 支只有文件提到 —— 但多數是**刻意手動的工具**，逐一核實後真訊號只有 2 個（訊噪比約 1:19）。做成通用告警＝製造沒人看的噪音（同 08-20 那次「48 個 Select 我選擇不交付」）。**建議改為三個窄座標各一支**，都有明確判準、低誤報：① `ecosystem.config.js` 宣告 vs `pm2 jlist` 實際 ② Prometheus metric expose vs 有無 alert／dashboard／檢核在讀 ③ git hook 腳本 vs `.git/hooks` 實際安裝 |

| B12 | **細粒度權限只覆蓋 16 支端點，其餘 478 支是二分法** | 494 支端點裡：`require_auth` **313**（只要登入）／`require_admin` **165**（管理員）／`require_permission` **僅 16**。也就是說 `/admin/permissions/:role` 上調整的 33 個權限，**對絕大多數端點沒有任何作用** —— 真正在決定「誰能做什麼」的是「登入 vs 管理員」這個二分法 | ⚠️ **不建議大規模改造**：把 478 支逐一分權是高風險低回報，而且會產生大量「宣告了但沒有角色擁有」的新缺口（正是 A23 那個形狀）。建議只在**業務上真的需要分權的動作**上加（費用審核、廠商維護這類），其餘維持二分法並在文件寫明這是**刻意的**，不是還沒做完 |
| B13 | **`operational:*` 是前端擋、後端不擋** | `ERPOperationalDetailPage` 用 `hasPermission('operational:write'/'operational:approve')` 隱藏編輯與審批按鈕，而 `erp/operational.py` 的端點**全部只有 `require_auth`** ⇒ 任何登入者直接打 API 都能改。目前沒有實害（沒有 UI 入口），但這是「前端當安全機制」的形狀 | 修法方向：若那些動作真要限權，加在**端點**上；若不需要，前端就不該擋（現況是兩邊說法不同，而使用者看到的是「按鈕不見了」） |

---

## C. 觀察中（不阻斷，但要盯著）

| # | 現象 | 已排除 | 風險 |
|---|---|---|---|
| C1 | **排程被某個程式持續停用** | 非斷電所致（Adobe 2025-01、Zoom 2025-02 也在其中）；事件 ID 142 顯示分散在整個下午 | 輪到異地備份就是那天資料只有一份 |
| C2 | **`ui_smoke_auth.py` 間歇連線失敗** | 非埠耗盡（TIME_WAIT 212／動態埠 16384）、非 postgres 拒絕（log 無紀錄）、非 SSL（`ssl=disable` 同樣失敗） | 它是走查的基礎，壞了整套走查跑不了 |
| C3 | **`llm_quota_check` 曾沉默 3.5 天** | 手動觸發完全正常 ⇒ 排程器沒觸發它 | 已自行恢復（22:16 準時執行），根因未定 |
| C4 | **@768px 版面外溢** | 先前行動量測只看 390px，平板寬度從未量過 | 觀測不告警，屬產品決策 |
| ~~C5~~ | ~~**⭐⭐走查永遠以最高權限跑**~~（**2026-08-27 收束**，見下方說明）| 走查憑證挑的是 `is_admin AND is_active` 的帳號（`ui_smoke_auth.py`）。**一般同仁看到的畫面從來沒有被走查過** | 2026-08-20「同仁變成代碼」就在這個盲區裡：五個人員下拉對 `role='user'` 一律是空的，而走查、tsc、py_compile、模組匯入掃描**全部綠燈**。這不是檢核寫錯，是**座標系裡沒有「非管理員」這個維度** |

---

> **C5 已於 2026-08-27 收束 —— 但先前只做了一半，而那一半看起來很像做完了。**
>
> 08-24 就把身分維度做進引擎了（`ui_smoke_auth.py --role user`、`run.sh` 兩端擋無效身分、
> config 的 5 條 flow 宣告 `roles: ['admin']`）。**做得對，可是沒有任何排程在用它** ——
> `CK_Missive-SelfAudit-Flow` 的參數欄是空的，一年裡每一次走查都還是 admin。
> 「能力有了」與「有人在跑」是兩件事，而前者會讓人以為後者也成立。
>
> 08-27 補上缺席的那一半：
>   · **結果檔依身分分檔**（引擎層，五 repo 共用）。實跑 `--role user` 當場把 `ui-flow.json`
>     蓋成 user 的結果（pass 13/fail 2），而 producer 的門檻是照 admin 訂的 ——
>     **watchdog 會照別人的身分報紅，而檔案裡沒有一個欄位說得出這是誰跑的**。
>     現在 `role` 進 JSON，非 admin 寫 `ui-flow.<role>.json`；sweep 同治（那支引擎
>     先前連 role 這個概念都沒有，更難察覺）。
>   · **排程** `CK_Missive-SelfAudit-Flow-User`（每日 05:10，走 config 的 `extra_tasks`，
>     不手刻 schtasks）。
>   · **接收端** producer registry 兩筆（file_fresh 30h + json_result），門檻與 admin 分開 ——
>     適用 flow 是 15/20，混在同一個座標系會讓「這條本來就不適用」與「它壞了」長得一樣。
>   · **排程稽核** `windows_task_liveness_audit` 的 `SELFAUDIT_TASK_RE` 尾綴改為可選；
>     ⚠️ 改完立刻印出兩次 `CK_Missive flow: pass=20`（兩支任務讀同一個檔）——
>     **我自己當場示範了 L81**，已改為依身分取檔並在訊息帶 `[admin]`／`[user]`。
>
> **首跑結果：一般同仁 GREEN 15/15。** ⚠️ 前一次跑出 2 個 FAIL，逐一查證後
> **兩個都是同一次 Cloudflare 502**（截圖是 CF 的 Bad gateway 頁，`ck_missive_backend`
> 當時被另一個 session 重啟）—— 同 08-19「failure 訊息完全相同就先問是不是同一個上游」。
> 若當成兩個缺陷去修，會修出兩個不存在的問題。
>
> 仍未做：斷言分辨「這個頁面該看不到」與「該看到卻是空的」。現況是用
> `roles` 宣告把不適用的整條排除，那是**迴避**而不是分辨 —— 一條 admin-only 的 flow
> 若哪天對一般同仁開放了，不會有任何人發現它其實沒被驗過。
>
> **2026-08-28 05:10 首次無人值守執行，整條鏈驗完**（此前都是我手動觸發）：
>
> | 環節 | 實測 |
> |---|---|
> | 排程 | `CK_Missive-SelfAudit-Flow-User` 05:10 執行，result=0，下次 08-29 05:10 |
> | 產出 | `ui-flow.user.json` 05:12 寫入，`role=user`，**pass 15 / fail 0 / skip 0** |
> | **不互相覆蓋** | admin 那份仍是 04:19，**沒有被蓋掉**（這正是 08-27 手動實跑時發生的事）|
> | 接收端 | producer watchdog 兩筆皆 GREEN（`file_fresh` 0h／`json_result` pass=15 ≥10）|
> | 排程稽核 | 印 `CK_Missive flow[user]: pass=15 fail=0`，與 `flow[admin]` 分開 |
>
> ⇒ **能力 → 排程 → 產出 → 接收端 → 稽核**五段全部接上且各自可辨識。
> 依 `adr-anti-half-wired-sop` 的「真活」判準，這一條現在才算真的活。
>
> 順帶一提：這個盲區在 2026-08-10 就以另一種形態出現過（員工「看得到卻
> 用不了」，管理員判定有四份規則）。那次修的是**判定邏輯**，08-20 是
> **資料源**——同一個維度缺席，換了個地方長出來。

---

## D. 本輪確立的判準（寫進判斷，不只是紀錄）

1. **「這個東西被誰讀？」** —— 加欄位、組網址、寫規則之後都要能回答。
   答不出來就是只做了一半。本輪三個最貴的缺陷全是這一類。
2. **在有豁免的環境驗證安全機制，等於沒有驗證**（本機 `AUTH_DISABLED=true`
   讓 CSRF 中介層完全跳過，我因此得出「不是認證問題」的錯誤結論）。
3. **同一件事量兩次，兩次一致才算數**（斷電後的排程狀態、間歇性連線失敗）。
4. **查詢加了 `LIMIT` 就不能拿來證明「不存在」**。
5. **build log 說成功不代表東西在映像裡** —— 要進映像 grep 才算數。
6. **要求人先統一格式才能匯入，等於把工作推回給填表的人**
   （`B115-C017a-0` vs `B115-C017-a` 用正規化解決，而非要求改檔）。
7. **「我用什麼身分在驗？」** —— 全部用管理員跑，等於只驗了一種人的畫面。
   與判準 2（在有豁免的環境驗證安全機制等於沒驗證）是同一件事的兩面：
   **驗證環境本身若不具備該條件，結果不成立**。
8. **同一個 queryKey 用不同資料源，等於誰先載入誰說了算** ——
   key 撞號本身不是錯（同一份資料就該共用快取），源不一致才是。
   已由 `queryKey_drift_audit` 的第二種形態擋住。
9. **⭐⭐安全驗證的結論，取決於量測方法本身有沒有先被驗證**（2026-08-21）。
   同一輪有**四次**機會宣告「已經擋住了」而每一次都會是錯的：
   Cloudflare 擋掉 `Python-urllib` 預設 UA（全 403，看起來像應用層擋住）／
   bash `while read` 迴圈裡的 curl 吃掉 stdin（全 000）／連續快打觸發速率限制
   （同樣全 000）／token 解析寫壞（`token=無` 卻仍印 403）。
   **四種失敗都長得像「安全」**，這是與判準 2（在有豁免的環境驗證安全機制
   等於沒驗證）同一族的第三種形態。
10. **CSRF 不是認證** —— `/api/secure-site-management/csrf-token` 是**刻意公開**的
   （L68 自癒需要），未登入即可取得。**判準：帶著公開可取的 CSRF token 之後
   仍然 401 才算真的擋住**；只看第一輪的 403 會得到相反結論。
11. **跨 repo 套用檢核工具，必須先由該 repo 自己列白名單**（2026-08-21）。
   `public_endpoint_auth_audit` 對 lvrland 掃出 147 條無認證，而前幾條是
   `/api/auth/{login,register,refresh,logout}` —— 登入流程本來就該公開。
   ⚠️ lvrland 起初判斷「探測跑在 `enforce_route_auth` 之前」，**那不成立**：
   用與容器啟動指令完全相同的匯入方式重跑，log 印出 `hardened_routes=276`
   而結果不變。**工具沒錯，錯的是拿別人的座標系直接下結論。**
   ⚠️ **座標系有兩半**（lvrland 後續補充並經雙向重現）：白名單一半、
   **認證函式名單另一半**。他們 147 條裡 96 條白名單命中、**~49 條是
   「有認證，但走 service-token 家族」**（`require_service_scope`／
   `get_user_or_service`／`verify_telegram_secret`）而我的預設清單認不得。
   實測補上後消掉 44 條 ⇒ **只帶白名單仍會拿到 49 條假陽性，而假陽性
   正是這次外洩被淹沒的原因**。已加 `--auth-names`。
12. **⭐用 `py_compile` 驗語法，不帶 `force` 只證明 pyc 已存在**（2026-08-21）。
   先前多次回報的「829 檔 0 失敗」是這樣來的 —— 它讀既有 pyc 就回成功，
   **不代表原始碼可編譯**。帶 `force=True` 重跑才發現真相是另一回事：
   全部失敗於寫入 `__pycache__` 的 `PermissionError`（容器非 root），
   仍然不是語法檢查。**正解＝`compile(source, path, 'exec')` 編到記憶體、
   完全不寫檔**，這才真的驗語法（實測 829 檔 0 失敗）。
   與判準 9 同族：**驗證工具的副作用會決定它到底驗了什麼**。
13. **三態不是選配 —— 訊息說對了而狀態說錯了，讀報告的人只看得到狀態**
   （2026-08-21，L89 在新地方重演）。`integration_e2e_validation` 的
   `chain_3` 缺 token 時已正確附上「無法驗證（不是整合斷了）」，
   **但值仍是 `ok=False`** ⇒ 進 `broken_chains`、`all_ok=false`、
   OVERALL BROKEN。已改 `ok=None` 第三態並分開統計
   （現況 ALL PASS／1 條未驗完；注入真斷仍 BROKEN + exit 1）。
14. **⭐⭐三種發現方式，各自抓到不同的東西**（2026-08-23，與 CK_AaaP 交叉驗證後
   拿本 repo 當日紀錄逐項核實）。我原本說「真正抓到我的沒有一次是自查」，
   **那句話是錯的**，攤開來看形狀更準：

   | 方式 | 抓到的是什麼 | 本 repo 當日實例 |
   |---|---|---|
   | **自查** | 我**已經在看**的東西壞了 | NAS 掃描說「空」但稽核說 1528（**兩個數字打架**）／tar 用錯支（跑它，大聲失敗）／備份順序（稽核的新鮮度門檻報 40.6h） |
   | **互查** | 我**連那個維度都沒有** | 認證名單那一半（lvrland）／baseline 假理由（FacilityDev）／備份判準歧義（AaaP）／`doc_type` 契約斷裂（stop hook）／「67 則」實為 1 則 67 筆（owner） |
   | **⭐互查提問＋自查作答** | 對方**看不到我的系統**，但說出了值得我自己查一遍的問句 | AaaP 報「版次四個來源三個數字」→ 我查出自己**更嚴重**（`health.version` 是 `None`，事故當下無從得知線上跑哪一版）／AaaP 的 PT72H → 我查出**自己也有兩支**／AaaP 的死碼分支 → 我回頭確認自己的狀態檔分支不是死碼 |

   **自查的三個實例全都是「有第二個來源，或它會大聲失敗」** ——
   沒有第二個來源的地方，自查用的是同一個座標系，**而錯的往往就是座標系本身**。

   **第三類的槓桿最大**：發現者不需要存取被發現者的系統，也不需要雙方同時在跑
   —— 那個問句**可以留在文件裡等下一個人**。當日四次裡有三次，發現者
   看不到被發現者的系統。

   ⇒ 覆盤時要問的兩句（前者需要對方在場，後者不需要）：
   **「我有什麼是你看得到而我看不到的？」**
   **「你剛在自己身上發現了什麼，值得我去自己查一遍？」**

   ⚠️ 界限（CK_AaaP 立的，我同意）：**互查依賴對方當時剛好在跑，不能取代
   自查，也不寫成流程** —— 寫成流程就會變成一個沒有人跑得動的儀式。
15. **⭐跨 session 訊息裡的「已」只能寫已經 commit 的事**
   （CK_AaaP 2026-08-21 主動更正自己時提出，對我同樣適用）。
   他們對我說了兩句「已記進 X」，事後自查發現當時只是打算做。
   **訊息是一個完全沒有守門的紀錄面** —— 送出就進入對方的工作脈絡、
   會影響對方接下來做什麼，而沒有任何檢核會比對它與現實；
   比文件更糟的是**它無法事後修正**。
   規則：先改、先 commit、再說；必須先回覆時寫「我會」而不是「我已」。

---

## E. 相關文件索引

| 文件 | 涵蓋 |
|---|---|
| **`RETRO_AND_PLAN_20260824.md`** | **08-21～24 四天跨 8 repo 的覆盤、八條判準、權責劃分（A owner／B 各 repo／C Missive 自己）與優先序** ← 最新入口 |
| `QUOTATION_LIFECYCLE_PLAN.md` | 回簽流程、帳號對應、既有案件補件、發票架構、已完成清單 |
| `ROLE_MODEL_PLAN.md` | 人／帳號／職能三層、兩個頁面的定位、RBAC 路徑 |
| `TENDER_DATA_GAPS.md` | 決標資料 0 筆、三條取得路徑的實測、PCC 預算已解決 |
| `docs/runbooks/unexpected-shutdown-recovery.md` §0 | 排程被停用的診斷程序與指令 |
| `CLAUDE.md` v6.59 | 本輪完整里程碑 |
