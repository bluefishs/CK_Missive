# 關聯記錄 ID (link_id) 處理規範

> **版本**: 1.0.0
> **建立日期**: 2026-01-21
> **狀態**: 生效中

---

## 1. 問題背景

### 1.1 事件描述

2026-01-21 發現 `unlinkDispatch` API 返回 404 錯誤：
```
POST /api/taoyuan-dispatch/project/175/unlink-dispatch/175 404 (Not Found)
```

### 1.2 根因分析

**問題核心**：前端使用了危險的回退邏輯 `link_id ?? id`，導致當 `link_id` 為 `undefined` 時，錯誤地使用實體 ID 作為關聯記錄 ID。

**錯誤代碼示例**：
```typescript
// ❌ 危險的回退邏輯
const linkId = proj.link_id ?? proj.id;  // 如果 link_id 是 undefined，會使用工程 ID
```

**ID 概念混淆**：

| ID 類型 | 說明 | 來源表 |
|---------|------|--------|
| 實體 ID (`id`) | 業務實體的主鍵 | `taoyuan_projects`, `official_documents` 等 |
| 關聯 ID (`link_id`) | 多對多關聯表的主鍵 | `taoyuan_dispatch_project_link`, `taoyuan_dispatch_document_link` 等 |

---

## 2. 影響範圍

### 2.1 受影響的 API 端點

| 端點 | 參數 | 風險等級 |
|------|------|----------|
| `/project/{project_id}/unlink-dispatch/{link_id}` | link_id = TaoyuanDispatchProjectLink.id | 高 |
| `/dispatch/{dispatch_id}/unlink-document/{link_id}` | link_id = TaoyuanDispatchDocumentLink.id | 高 |
| `/document/{document_id}/unlink-dispatch/{link_id}` | link_id = TaoyuanDispatchDocumentLink.id | 高 |
| `/document/{document_id}/unlink-project/{link_id}` | link_id = TaoyuanDocumentProjectLink.id | 高 |

### 2.2 受影響的前端頁面

| 頁面 | 功能 | 修復狀態 |
|------|------|----------|
| `TaoyuanDispatchDetailPage.tsx` | 工程關聯、公文關聯移除 | ✅ 已修復 |
| `TaoyuanProjectDetailPage.tsx` | 派工關聯移除 | ✅ 已有保護 |
| `DocumentDetailPage.tsx` | 派工關聯移除 | ✅ 類型安全 |

---

## 3. 修復方案

### 3.1 前端修復原則

#### 禁止回退邏輯

```typescript
// ❌ 禁止 - 危險的回退邏輯
const linkId = proj.link_id ?? proj.id;

// ✅ 正確 - 嚴格要求 link_id 存在
const linkId = proj.link_id;
if (linkId === undefined || linkId === null) {
  message.error('關聯資料缺少 link_id，請重新整理頁面');
  console.error('[unlink] link_id 缺失:', proj);
  refetch();  // 自動重新載入
  return;
}
```

#### UI 條件渲染

```typescript
// ✅ 只有當 link_id 存在時才顯示移除按鈕
{canEdit && item.link_id !== undefined && (
  <Popconfirm onConfirm={() => handleUnlink(item.link_id)}>
    <Button danger>移除關聯</Button>
  </Popconfirm>
)}
```

### 3.2 後端修復原則

#### 詳細錯誤訊息

```python
@router.post("/project/{project_id}/unlink-dispatch/{link_id}")
async def unlink_dispatch_from_project(project_id: int, link_id: int, ...):
    """
    參數說明：
    - project_id: TaoyuanProject.id（工程 ID）
    - link_id: TaoyuanDispatchProjectLink.id（關聯記錄 ID，非工程 ID）
    """
    link = await find_link(link_id, project_id)
    if not link:
        # 區分錯誤類型
        existing = await find_link_by_id(link_id)
        if existing:
            raise HTTPException(404, f"link_id={link_id} 對應的工程 ID 是 {existing.project_id}，而非 {project_id}")
        else:
            raise HTTPException(404, f"關聯記錄 ID {link_id} 不存在。請確認傳入的是 link_id，而非工程 ID")
```

---

## 4. 預防措施

### 4.1 類型系統強化

**前端類型定義**（`types/api.ts`）：

```typescript
/** 基礎關聯介面 - 所有關聯類型必須包含 link_id */
export interface BaseLink {
  /** 關聯記錄 ID (必填，用於刪除操作) */
  link_id: number;  // 不可為 optional
  link_type?: LinkType;
  created_at?: string;
}
```

### 4.2 開發檢查清單

新增關聯功能時，必須檢查：

- [ ] 後端 API 響應是否包含 `link_id` 欄位
- [ ] 前端類型定義是否正確標記 `link_id: number`（非 optional）
- [ ] 前端移除操作是否使用 `link_id` 而非實體 `id`
- [ ] 是否有防禦性檢查（`link_id !== undefined`）
- [ ] 後端錯誤訊息是否能區分「ID 不匹配」和「ID 不存在」

### 4.3 程式碼審查重點

**搜尋危險模式**：
```bash
# 搜尋可能的回退邏輯
grep -r "link_id \?\?" frontend/src/
grep -r "link_id ||" frontend/src/

# 搜尋 any 類型的使用（可能繞過類型檢查）
grep -r "as any" frontend/src/pages/
grep -r ": any" frontend/src/pages/
```

---

## 5. 關聯表設計規範

### 5.1 命名規範

| 規範 | 說明 | 範例 |
|------|------|------|
| 關聯表名稱 | `{entity1}_{entity2}_link` | `taoyuan_dispatch_project_link` |
| 關聯記錄 ID | `link_id` | 在 API 響應中統一使用 |
| 外鍵命名 | `{entity}_id` | `dispatch_order_id`, `project_id` |

### 5.2 API 響應結構

**關聯資料必須包含**：
```json
{
  "link_id": 123,        // 關聯記錄 ID（必填）
  "entity_id": 456,      // 被關聯實體 ID
  "link_type": "...",    // 關聯類型（若適用）
  "created_at": "..."    // 建立時間
}
```

---

## 6. 相關文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | 開發檢查清單（需新增 Link ID 處理項目） |
| `.claude/skills/type-management.md` | 型別管理規範 |
| `docs/specifications/API_ENDPOINT_CONSISTENCY.md` | API 端點一致性規範 |

---

## 7. 變更記錄

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-01-21 | 初版建立，定義 link_id 處理規範 |
