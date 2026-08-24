# `scripts/query.py` — 為什麼它到 2026-08-24 才進版控

## 它是什麼

Hermes 的 `ck-missive-bridge` skill 用來呼叫 Missive API 的表驅動腳本。
Hermes 端的 `terminal: query.py agent_query --question "..."` 走的就是它 ——
2026-06-02「baseline GO」那條端到端鏈路的最後一段。

## 問題：它跑了三個月而不在任何 repo 裡

CK_AaaP session 2026-08-24 對三個 repo 全域比對雜湊，**沒有任何副本與容器裡
那支相符**，而本部署包當時只有 `tools.py`／`SKILL.md`／`install.sh`／`tests`。

容器裡那支：240 行、mtime `Jun 3 11:45`，旁邊躺著
`query.py.bak.20260603-pre-s3b` ⇒ **2026-06-03 為了 S3 段B 在容器裡手改的，
之後沒有回到任何 repo**（與 template 差 39 行，正好是 digest handler 那一塊）。

**後果是三層，而每一層都無聲**：

* 改動**不會進 diff、沒有人能 review**；
* 任何人重跑 `install.sh` 或 volume 被重建，改動就消失 —— **而消失時沒有訊號**；
* 本專案 08-18 有同型前科（`SOUL.md` 被排程每日覆蓋，部署前完全無症狀）。

⇒ 2026-08-24 從容器取回、原樣入版控。**先收進版控，再談改法** ——
在一個沒有人能 review 的檔案上談方法變更是沒有意義的。

## 已知待辦：`memory_digest` 用 GET

```
"memory_digest": { "method": "GET", "path": "/api/ai/memory/digest", ... }
```

違反本專案規範 §24「所有 endpoint POST」（`http_method_convention_audit`，weekly 66）。

**而它是漂移不是例外** —— WO-2 當初的契約寫的就是 POST，CK_Hermes 那份工單
卡了一個月的阻斷原文是「`POST /api/ai/memory/digest` 實測回 **405**」。

### 改的順序（CK_AaaP 2026-08-24 提出，我同意）

跨 repo ＋ 跨容器部署，兩側**沒有辦法原子切換**：

1. 端點**同時接受 GET 與 POST**（過渡窗）
2. 兩個消費端改成 POST、部署、實測
3. 回報「兩端都不再發 GET」後，才拿掉 GET

反過來做的話，下面那個第二消費端會在部署當晚**靜靜少一段**。

### ⚠️ 消費端是兩個不是一個

| 消費端 | 改動成本 | 失敗形態 |
|---|---|---|
| `scripts/query.py`（本檔） | **一格字串** —— 表驅動，送出時吃 `handler["method"]` | 會報錯 |
| `profiles/meta/scripts/daily-closing-writer.py`（CK_Hermes） | 約 3 行（加 `data`＋`method`＋Content-Type） | ⚠️ **刻意 fail-safe**：任何例外都 `return None`、只印一行「digest 跳過」，daily 頁照樣產出**只是少了坤哥摘要** |

第二個是 2026-07-07 加的「契約外第二消費端」。**只跟 query.py 對齊的話，
它會靜靜地壞掉，而壞掉的樣子是「頁面正常，內容少一段」。**

## 部署

`install.sh` 應一併安裝本目錄。⚠️ **改這支之前先確認容器裡跑的是哪一份**
—— 06-03 到 08-24 之間，容器裡的與版控裡的是兩件事。
