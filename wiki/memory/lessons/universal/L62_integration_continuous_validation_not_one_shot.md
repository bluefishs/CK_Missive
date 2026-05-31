---
title: L62 — 整合連通 = 持續驗證機制，不是一次性 endpoint
type: lesson
scope: universal
category: integration
created: 2026-05-31
trigger_event: owner 訴求「期待本次整合優化程序能突破性成長 非一次性成功」
related: [[L51_container_image_freshness]], [[L57_backend_dir_logs_vs_mount_drift]]
tags: [integration, e2e, continuous-validation, anti-one-shot]
---

# L62 — 整合連通 = 持續驗證機制，不是一次性 endpoint

## 觸發事件

Owner 在「坤哥+Hermes+智能體 整合連通」核心議題反饋：

> 「已多次針對坤哥 Hermes agents 智能體整合列為核心議題
>  期待本次整合優化程序能**突破性成長 非一次性成功**」

之前 v6.6 / v6.7 / v6.12 多次新增整合 endpoint / skill tool，但都「一次寫好就放著」，無持續驗證機制 → 任一鏈 silent dormant 無人發現。

## Lesson 本體

### 整合連通 ≠ 一次性 endpoint

**錯誤模式**（一次性）：
```
寫 endpoint → 寫 skill → commit → 完成 ✓
```

**正確模式**（突破性 持續真活）：
```
寫 endpoint → 寫 skill → 寫 E2E 驗證 script → 排 cron 每日跑
            → 任一鏈斷 → 自動 LINE 推 → 寫 health marker
            → 驗證鏈本身也是 fitness step → 防 cron silent dormant
```

### 5 鏈 E2E 通用模板

任何「A 整合 B」場景必走 5 鏈驗證：

1. **A 自身健康** (e.g. /health 業務量 OK)
2. **A 對外 endpoint** (e.g. /api/.../snapshot E2E)
3. **A 公開 contract** (e.g. tool manifest 含新 tool)
4. **B 自身可達** (e.g. B container HTTP reachable)
5. **A↔B 對齊** (e.g. skill 端 tool_endpoint 對齊)

### 突破性 3 要素

突破 = 結構性而非個案：
- **持續驗證**：cron / fitness step 每日跑（防 silent dormant）
- **自動揭發**：任一鏈斷 → LINE 推 owner + 寫 marker（不依賴 owner 主動查）
- **本身可被檢查**：驗證機制本身也納入 fitness（防 cron 自己 silent）

## 對齊原則

- **真活大於規劃**：endpoint 寫好 + restart + curl 驗證才算真活
- **L51.7.1 同型防範**：host code change → docker cp (立即) 或 rebuild (永久)
- **owner 安全訴求**：純 read 驗證 / 獨立 try-except / 不阻塞他鏈

## 實作範本

```python
# scripts/checks/integration_e2e_validation.py

async def check_chain_N() -> Dict[str, Any]:
    try:
        # 真實呼叫 endpoint，不是 mock
        ...
        return {"ok": True, "metric_1": ..., "metric_2": ...}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

# scheduler.py
@tracked_job("integration_e2e_validation")
async def integration_e2e_validation_job():
    rc, out, _ = await _run_script_async([...])
    if rc != 0:
        # 任一鏈斷自動 LINE 推
        await IntegrationFacade().push_admin_alert(...)
```

## 反模式 vs 正模式

| 反模式 (一次性) | 正模式 (突破性) |
|---|---|
| 寫好 endpoint commit 完事 | 寫好 + E2E script + cron + LINE alert |
| 「下次有人需要再驗證」 | 每日自動驗證 |
| 只驗單鏈 | 5 鏈全綠才算 OK |
| 驗證 silent fail 無人知 | 驗證鏈本身也是 fitness step |

## 衍生規範

### Cross-Repo Integration 三件套（強制）

任何新增「跨系統整合」必走：

1. **endpoint / API 真活** （host + container 雙驗證）
2. **E2E validation script** （5 鏈通用模板）
3. **cron + LINE alert** （持續監督，silent dormant 防範）

## ROI 評估

- **避免**：「endpoint 寫了沒人用」silent dormant（過去 v6.6/v6.7 多次）
- **效益**：owner 第一時間知道整合斷層（不用月底覆盤才發現）
- **成本**：每日 30 秒 cron + ~1KB marker

## 跨 repo 適用

本 lesson 可套用至：
- CK_lvrland_Webmap / CK_PileMgmt（與 Missive Hermes 整合）
- CK_AaaP（Showcase / DigitalTunnel 服務整合）
- 任何「跨系統 endpoint」場景

## 歷史軌跡

| 版本 | 整合動作 | 持續驗證？ |
|---|---|---|
| v6.6 (2026-05) | get_memory_status + get_evolution_journal tool | ❌ 一次性 |
| v6.7 (2026-05) | memory_patterns/proposals/crystals tool | ❌ 一次性 |
| v6.12 (2026-05-30) | 8 治理原則立法 | ❌ 工具未串 |
| **v6.13 (2026-05-31)** | **kunge_snapshot + 5 鏈 E2E + cron** | ✅ **本批立法** |

---

> **核心精神**：整合不是「寫好 endpoint」事件，是「持續驗證鏈」過程。
> 突破性 = 從事件變過程；非一次性 = 從一次 commit 變每日 cron。
> 對齊 owner「真活大於規劃」+「日誌+周報=靈魂」哲學。
