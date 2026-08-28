# 重啟前狀態固定與復原指引（2026-08-28）

> 用途：**重啟後要能分辨「本來就有的」與「重啟造成的」。**
> 沒有這份基線，任何重啟後的紅燈都會被當成新問題查一遍。
> 前一份：`reboot-pre-flight-20260824.md`（該次的已知紅燈與待辦仍請對照）

---

## 1. 重啟前的量測基線（10:30 實測）

| 項目 | 值 |
|---|---|
| 公網首頁 / `/health` | **200 / 200** |
| 業務量 | documents **2,032**｜canonical_entities **49,984** |
| 容器 | **56** 個 Up（另 3 個非 Up 屬既有：lvrland frontend-dev、tunnel builder、ollama_dev「Created」）|
| runtime 身分 | `v6.63 @ 90d93c4f-dirty`（dirty 來自其他 session 未提交的檔案，非我的）|
| CK_Missive 未推送 | **0** |
| 異地備份四類 | **GREEN 且新鮮**（資料庫／里程碑／附件／金鑰）|

### 排程稽核的 5 個 RED —— **重啟後應該還在，不是新問題**

    CK_lvrland_Webmap-SelfAudit-Static   LastTaskResult=2（未宣告的失敗碼）
    CK_lvrland_Webmap-StaticChecks       LastTaskResult=2
    CK_Missive-SOUL-Mirror-Sync          State=Disabled ／ result=3 ／ 04:45 沒跑

* lvrland 兩支：等該 repo 回覆退出碼語意（我不猜，猜錯會吞掉真的失敗）
* SOUL-Mirror-Sync 三條：**它被停用是對的**（跑的腳本 08-02 起就設計成拒絕執行），
  處置見 **A28**。⚠️ 不要因為看到紅燈就把它啟用 —— 我 08-27 這樣做過，是錯的。

---

## 2. ⚠️ 重啟前沒清掉的：其他 repo 有 19 筆未推送

    CK_Hermes        16 筆    ← session 已關閉，通知不到
    CK_AaaP           3 筆    ← session 已關閉
    CK_Website        1 筆
    shared-modules    3 筆
    CK_Missive        0（已清空）
    CK_DigitalTunnel  0（他們昨日已推完 15 筆）

**重啟不會弄丟 commit。** 真正的風險是：未推送的工作在重啟後很容易被下一個
session 當成「還沒做完」而重做一次。恢復後請先在各 repo 跑
`git log @{u}..HEAD` 確認，再決定要不要推。

---

## 3. 重啟後**必然**會看到、但不是故障的三件事

| 現象 | 為什麼 | 怎麼判 |
|---|---|---|
| `CK-Hermes-Cron-Tick` 等高頻排程「上次執行在重啟前」 | 關機期間不可能 fire | 稽核已有 boot-clamp（取「距上次執行」與「距開機」較小值），30 分鐘內不報 |
| `CK-Hermes-Health-Smoke-Daily` 仍是 `1999-11-30` 形態 | 它 08-27 才註冊，首跑是每日 09:10 | `NumberOfMissedRuns=0` 且 `NextRunTime` 在未來 ⇒ 正常 |
| Redis host 埠 `127.0.0.1:6380` 連不上 | **L76 殭屍轉發**（TCP 連得上、立刻被關閉；容器內 `redis-cli ping` 回 PONG）| ⚠️ **重啟後很可能自己好** —— 若好了，那是埠轉發重建，**不是修好了什麼**，別記成成果 |

---

## 4. 重啟後的復原順序

```bash
# ① 基礎設施（--profile tunnel 不可省，否則公網入口不會建回來）
cd D:/CKProject/CK_Missive
docker compose -f docker-compose.infra.yml --profile tunnel up -d

# ② 三層驗證（本機 → 公網 → ORM/認證鏈）
bash scripts/checks/deploy_verify.py   # 或 python scripts/checks/deploy_verify.py

# ③ 與本文件的基線對照
python scripts/checks/windows_task_liveness_audit.py    # 應仍是那 5 個 RED
python scripts/checks/business_vital_signs.py           # 業務量對照 §1
curl -s https://missive.cksurvey.tw/health              # documents 應 ≥ 2032
```

### ⚠️ 已知的重啟陷阱（不要重踩）

* **NVIDIA Container Toolkit prestart hook 崩潰**（`ld.so _dl_setup_hash` 斷言）會讓
  GPU 容器（`ck-ollama`）起不來、推論全斷，**而 healthcheck 仍是綠的**。
  解法是 `wsl --shutdown` 重啟 Docker 引擎，**不是 `docker restart`**。
* **L76 殭屍埠**：後端 rebuild 後容器 healthy 而公網 502。所以 §4 的驗證必須驗到公網，
  本機 200 不算數。
* **有程式會持續停用 Windows 排程**（C1）。復原後用
  `python scripts/checks/windows_task_liveness_audit.py` 確認，
  ⚠️ 但 `State=Disabled` **不等於該啟用**（見 §1 的 SOUL-Mirror-Sync）。

---

## 5. 重啟後最該先看的一件事（本輪新發現）

**A31：Groq 與 NVIDIA 的模型都已下架，agent 已在本地 ollama 上跑了約 27 天。**

    GROQ_DEFAULT_MODEL   = llama-3.3-70b-versatile                  → 不在 Groq 模型清單
    NVIDIA_DEFAULT_MODEL = nvidia/llama-3.3-nemotron-super-49b-v1.5 → 不在 NVIDIA 清單
    （兩家 models API 皆回 200 ⇒ API key 有效，是模型名的問題）

現場：`Groq circuit OPEN → 走 NVIDIA` → `NVIDIA circuit OPEN → 走 Ollama` →
`Synthesis timed out after 35s`。

⚠️ **重啟會清掉斷路器狀態**（它是 per-process 的記憶體物件），所以重啟後
「Groq circuit OPEN」那幾行會暫時消失 —— **但模型仍然不存在**，
幾次請求後又會開回來。**不要把那個空窗讀成問題消失了。**

換哪個模型是 owner 決策（影響品質、TPM 假設與成本），可用清單見 `OPEN_ITEMS` A31。

---

## 6. 待 owner 決定的清單（重啟不會改變它們）

`docs/architecture/OPEN_ITEMS_20260819.md`：**A19–A31**。其中本輪新增：

* **A28** SOUL-Mirror-Sync 排程要不要移除（它只剩製造紅燈的功能）
* **A29** `ck_missive_frontend` 容器去留（健康、陳舊、連不到、不在使用者路徑上）
* **A30** `actual_llm_provider` 修法已上線但**生產尚未驗到**
* **A31** 兩個雲端模型已下架（見 §5）
