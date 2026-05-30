---
title: L44 — SSO frontend session lock 跨 subdomain 不同步
type: lesson
date: 2026-05-25
fqid: CK_Missive#L44
family: cross-file-ssot
related: [L41, L43, L45, L52]
---

# L44 — SSO frontend session lock 跨 subdomain 漂移

> **日期**：2026-05-25
> **觸發**：跨 subdomain (missive ↔ lvrland) 認證失敗
> **dormant**：< 1 天
> **修法**：ck-sso-js v2.0 移除 lock

---

## 真因

sessionStorage hard-coded `sso_lock` key (跨 tab 防雙開) 與 cookie storage 不同步：
- 同 tab 內走 sessionStorage check OK
- 跨 subdomain 走 cookie 沒看到 lock 算 NEW session
- 兩處檢查 logic 漂移 → silent 認證失敗

---

## 修法

`ck-sso-js v2.0`：
- 移除 sessionStorage `sso_lock`
- 只用 cookie SSOT（跨 subdomain 共用 `.cksurvey.tw` 域）
- 同 tab 雙開風險改由 backend session 限制

---

## 治理立法（cross-file-ssot-governance）

L44 = 跨檔 SSOT 治理失效第三案（L41 → L43 → L44）。
共通模式：同一 contract（auth state）在多處宣告，沒 enforce 一致 → silent drift.

對應規範：cross-file-ssot-governance.md §1 表格「Endpoint URLs」+ §4 dual-validation

---

## 元洞察

auth state 必須 single source — cookie or sessionStorage 二擇一，不可雙軌。
雙軌就是 silent drift 溫床。
