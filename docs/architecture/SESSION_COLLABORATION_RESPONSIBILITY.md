# 多 Session 協同作業與權責劃分（2026-09-02 建立）

> **為什麼建立**：2026-09-02 owner 同時開了 6 個 session 在不同 repo 工作，
> 而當天發生一起**宿主層**事故（Docker 資料磁碟 ext4 損毀），
> 讓六個 repo 的容器全部停擺。
> **每個 session 都看到自己的服務掛了，而真因不在任何一個 repo 裡。**
>
> 這份文件解決的是：**當故障不屬於任何人時，它屬於誰。**

---

## 1. Session ↔ repo 對應（2026-09-02 實測）

| Session | 負責 repo | 當時狀態 |
|---|---|---|
| `ck-missive-b2` | `CK_Missive` | 本檔作者 |
| `ck-aaap-58` | `CK_AaaP`（平台治理） | — |
| `ck-website-37` | `CK_Website`（SSO IdP） | — |
| `ck-lvrland-webmap-24` | `CK_lvrland_Webmap` | — |
| `ck-lvrland-dataform-a8` | `CK_lvrland_dataform` | — |
| `ck-facilitydev-67` | `CK_FacilityDev` | — |

用 `ListAgents` 取得當下的清單；**名稱就是位址**，`SendMessage({to: "<name>", ...})`。

⚠️ 對應關係是**推定的**（由名稱推 repo），不是系統保證的。
要別人做事之前，先在訊息裡說明你認為他負責什麼，讓他有機會更正。

---

## 2. 三條權責界線

### 界線一：**只動自己的 repo**

跨 repo 的修改一律**改成通知**，不是代勞。

理由不是禮貌，是**可追溯性**：別的 session 正在那個 repo 裡工作，
你的寫入會出現在他的 `git status` 裡而他不知道來源；
若他正在 debug，你就是他的變因。

**例外**：owner 明確指派。此時仍要**通知該 repo 的 session**你動了什麼。

### 界線二：**共用資源要有指定的記錄者，但不是指揮者**

宿主層（Docker engine / WSL2 VM / 磁碟 / 記憶體 / Windows 排程）**不屬於任何 repo**，
而它故障時**每個 session 都會看到自己的服務掛掉**。

| 角色 | 做什麼 | 不做什麼 |
|---|---|---|
| **記錄者**（本次是 `ck-missive-b2`） | 診斷、修復、寫 runbook、**主動廣播給所有 session** | 不決定別人 repo 要不要重啟／回滾／部署 |
| **其他 session** | 收到廣播後自行判斷對自己的影響 | 不重複診斷同一件事（浪費且會得到互相矛盾的結論） |

**為什麼要有指定記錄者**：2026-09-01 的 A66（全機 segfault），
CK_Missive 與 CK_AaaP 兩個 session **各自獨立**對 `docker inspect .State.ExitCode` 讀到 0，
各自得出「主進程正常結束」，**兩邊都往錯的方向找了數小時**（L127）。
矛盾其實從對方那側直接可見，只是沒有人在對照。

### 界線三：⛔ **權限邊界不可轉包**

**在你的 session 被拒絕或擋下的操作，不可以請別的 session 代做。**

那是繞過 owner 的權限決定（cross-session permission laundering），
即使對方做得到、即使那件事看起來很合理。

**正確做法**：把它退回給 owner，並說清楚你想做什麼、為什麼需要。

實例（2026-09-02）：`ck-missive-b2` 的 `git push` 被權限分類器擋下。
**不可以**請 `ck-aaap-58` 代為推送 CK_Missive。
已改為在重啟指引 §0 明列「這件事需要 owner 執行」，並附上指令。

---

## 3. 什麼時候該廣播

| 情況 | 廣播？ | 理由 |
|---|---|---|
| **宿主層故障**（Docker / WSL / 磁碟 / 記憶體 / 全機重啟） | **一定要** | 每個 session 都會看到症狀，而真因不在他們的 repo |
| **即將重開機／長時間停機** | **一定要** | 別人可能有未提交的工作 |
| 跨 repo 共用元件變更（`shared-modules`、SSO 契約、Docker network） | 要 | 消費端會壞而他們不知道為什麼 |
| **通用型教訓**（不是某個 repo 的 bug，是「這個環境會這樣咬人」） | 要 | 見 §4 |
| 自己 repo 的一般進度 | 不用 | 噪音；廣播太頻繁會讓人學會忽略它 |

### 廣播內容的最低要求

1. **第一行自成一句**，講清楚是什麼事（收訊端只看得到第一行預覽）
2. **明說「你不用查」**——省下對方重複診斷的時間，這是廣播最大的價值
3. 給**對方 repo 的具體數字**（未提交幾個、哪些容器受影響），不要只給通則
4. **不要求對方做事**，給事實讓他自己判斷
5. ⛔ **把「這是實測」與「這是推論」分開標記** —— 見下

---

## 3.5 ⛔ 轉達 ≠ 背書（2026-09-02 立，L137）

**收到別的 session 的結論並轉進自己的待辦時，標「來源是誰」不夠，要標「我查了嗎」。**

### 為什麼

2026-09-02：`ck-website-37` 交接一條 CK_PileMgmt 的問題，我依權責「只轉不動」寫進
`OPEN_ITEMS` 並**標明了來源**，並向 owner 覆述兩次。他同日主動撤回——那是錯的判型
（真因是 `pm2` 撞 EPERM 使 node abort ⇒ rc=255，而**實際恢復是成功的**）。

我標了來源，**但沒有標查證狀態** ⇒ 它在清單上與我自己實測過的項目**長得一模一樣**。

> **標「來源是誰」只回答了「這是誰說的」，沒有回答「我查了嗎」。
> 跨 session 協作裡，後者才是接收端需要的。**

### 規則

| 情況 | 必須怎麼標 |
|---|---|
| 轉述其他 session 的結論，本 repo 未查證 | **「未經本 repo 查證」** |
| 轉述後自己查過 | 標明**查了什麼、結果是什麼**（例：「照他的判準量出 15%」） |
| 對方明確標為未查證 | **照原樣轉，不要因為轉述而變成斷言** |

### 兩個方向都要

- **發送端**：把推論與實測分開標記（今天四個 session 各犯過至少一次）
- **接收端**：不因為「有來源」就當成已驗證

⇒ 這是「把推論與實測分開標記」的跨 session 版本——**同一條紀律，
只是不確定性的來源從我自己換成了別人。**

---

## 4. 通用型教訓 vs repo 專屬教訓

**判準：把 repo 名稱換掉之後，這條還成立嗎？**

成立 ⇒ 通用型 ⇒ 廣播，並考慮收進 `CK_AaaP/CONVENTIONS.md`。

2026-09-02 的三條通用型教訓（已廣播）：

| 教訓 | 為什麼通用 |
|---|---|
| `docker desktop status` 的 `starting` **是狀態不是進度** —— 卡住與很慢在狀態欄裡長得一樣，超過 5 分鐘就去看 `dmesg` | 所有用 Docker Desktop 的 repo |
| **CRLF 讓容器內的 shell 直接死掉**，而 `git status` 看不見、host 的 Git Bash 又容忍它 ⇒ 手動跑永遠全綠 | 所有在 Windows 開發、在 Linux 容器執行的 repo |
| **Python 在 Windows 上 `open(p,"w")` 會把 LF 寫成 CRLF** —— 寫檔一律帶 `newline=""` | 所有用 Python 改檔案的 repo |

⚠️ **收不收進 CONVENTIONS.md 是 `CK_AaaP` 的決定**，本 repo 只提供材料。
這正是界線一的示範：**建議可以跨 repo，寫入不行。**

---

## 5. 無人看管的 repo

沒有 session 在跑、但有累積工作的 repo，**只回報、不處理**——
處置屬 owner，因為那些改動的脈絡已經不在任何一個活著的 session 裡。

2026-09-02 實測：

| repo | 未推送 | 未提交 |
|---|---|---|
| `shared-modules` | 1 | **99** |
| `CK_KMapAdvisor` | 0 | **58** |
| `CK_Hermes` | **16** | 0 |
| `CK_DigitalTunnel` | 0 | 10 |
| `CK_PileMgmt` | 0 | 5 |
| `FT_StorageTank` | 0 | 1 |

⚠️ `shared-modules` 的 99 個未提交**特別值得注意**：它是跨 repo 共用元件，
未提交代表**其他 repo 正在消費一份沒有進版控的東西**。

---

## 5.5 跨 repo 修好但頂層記載未更新（2026-09-02 傍晚）

`ck-pilemgmt-7c` 通報：`D:\CKProject\CLAUDE.md` 頂層記著「pilemgmt 的 `/api/ai/query` 答案路徑是死的（HTTP 200 帶著失敗）」——**已修**（真因是 `create_success_result()` 一行漏傳 `response_text`；18 字元 → 182 字元；守門 4 tests 有鑑別力；commit `dc45a990f`）。

**我沒有改頂層那份**：它的權責不在 CK_Missive（界線一）。記在這裡讓下一個從本 repo 啟動的 session 知道那句已過期，並建議由 pile 或 AaaP 更新。

同一則通報附的跨 repo 警示已採用：`pm2 jlist` 在互動 session 對排程 spawn 的 daemon **必然 EPERM**（named pipe session 隔離）——「拿不到清單」是常態不是異常，正確表態是 YELLOW。本 repo `lib/pm2_guard.py` 的成因註解已更正。

## 6. 這份文件不涵蓋的

- **誰先做**（工作排序）——那是 owner 的決定，不是 session 之間協商出來的
- **衝突仲裁**——兩個 session 對同一件事結論相反時，把兩邊的證據交給 owner，
  不要私下說服對方。2026-08-29 的跨 session 互查證明**矛盾本身就是最好的錯誤偵測器**
  （`cross_session_review_beats_solo` 記憶檔），把它消掉反而損失資訊。

---

> 建立：2026-09-02（A67 事故當日）
> 觸發：一起不屬於任何 repo 的故障，讓六個 repo 同時停擺
> 相關：L127（兩個 session 各自讀到同一個誤導欄位）／L130–L134／
> `CK_AaaP/CONVENTIONS.md` §7 Session 工作目錄分流（既有規範，本檔為其行為面補充）
