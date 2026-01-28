# UI 設計規範

> **版本**: 1.0.0
> **建立日期**: 2026-01-26
> **適用範圍**: CK_Missive 公文管理系統前端

---

## 1. 導航模式 vs Modal 模式

### 規範原則

**一律採用導航模式，禁止使用 Modal 進行資料編輯**

### 導航模式 (Navigation Mode) - 採用

```typescript
// ✅ 正確 - 使用路由導航
const handleEdit = (id: number) => {
  navigate(`/entity/${id}/edit`);
};

const handleCreate = () => {
  navigate(`/entity/create`);
};
```

**優點**：
- URL 可分享、可書籤
- 瀏覽器返回/前進正常運作
- 支援多分頁開啟
- 與權限系統整合容易
- 表單狀態不易丟失

### Modal 模式 - 禁止

```typescript
// ❌ 禁止 - 不要使用 Modal 進行資料編輯
const [modalVisible, setModalVisible] = useState(false);

<Modal visible={modalVisible} onOk={handleSave}>
  <Form>...</Form>
</Modal>
```

**為何禁止**：
- URL 不變，無法分享
- 瀏覽器返回會直接離開頁面
- 不利於 SEO 和可存取性
- 與系統整體設計風格不一致

### 例外情況

Modal 僅允許用於以下場景：

1. **確認對話框** (Confirm Dialog)
   ```typescript
   Modal.confirm({
     title: '確定要刪除？',
     onOk: handleDelete,
   });
   ```

2. **快速預覽** (Preview)
   ```typescript
   <Image.PreviewGroup>
     <Image src={url} preview={{ visible: previewVisible }} />
   </Image.PreviewGroup>
   ```

3. **輕量級選擇器** (Picker)
   - 日期選擇
   - 顏色選擇
   - 簡單的單選/多選

---

## 2. 檔案上傳統一機制

### 架構原則

**所有檔案上傳功能必須遵循統一的技術架構**

### 後端 API 規範

```python
# 端點命名規範
POST /{entity}/{id}/upload-attachment    # 上傳
POST /{entity}/{id}/download-attachment  # 下載
POST /{entity}/{id}/delete-attachment    # 刪除

# 必須實作的功能
- 檔案類型白名單驗證
- 檔案大小限制
- SHA256 校驗碼計算
- 結構化目錄儲存
- 舊檔案自動覆蓋（單一附件）或追加（多附件）
```

### 前端 API 規範

```typescript
// 使用 apiClient.uploadWithProgress 支援進度追蹤
async uploadAttachment(
  entityId: number,
  file: File,
  onProgress?: (percent: number) => void
): Promise<UploadResult>

// 使用 apiClient.downloadPost 下載（POST-only 安全機制）
async downloadAttachment(entityId: number): Promise<Blob>

// 使用 apiClient.post 刪除
async deleteAttachment(entityId: number): Promise<void>
```

### 前端 UI 規範

**單一附件場景**（如證照掃描檔）：

```tsx
<Form.Item label="附件">
  {/* 預覽區域 */}
  {attachmentPreview && (
    <div className="attachment-preview">
      {isImage ? <Image src={url} /> : <FileIcon />}
      <Button onClick={handleDelete}>刪除</Button>
    </div>
  )}

  {/* 上傳按鈕 */}
  <Upload beforeUpload={handleFileSelect} showUploadList={false}>
    <Button icon={<UploadOutlined />}>
      {attachmentPreview ? '更換附件' : '選擇檔案'}
    </Button>
  </Upload>

  {/* 進度條 */}
  {uploading && <Progress percent={uploadProgress} />}

  {/* 格式說明 */}
  <div className="help-text">
    支援格式: JPG、PNG、PDF，最大 10MB
  </div>
</Form.Item>
```

**多附件場景**（如公文附件）：

- 使用 `FileUploadSection` 元件
- 使用 `ExistingAttachmentsList` 元件
- 參考 `frontend/src/components/document/operations/`

### 檔案儲存路徑規範

```
uploads/
├── {year}/{month}/doc_{documentId}/     # 公文附件
├── certifications/user_{userId}/         # 證照附件
├── projects/project_{projectId}/         # 專案附件（如有）
└── temp/                                  # 暫存檔案
```

### 安全規範

| 項目 | 規範 |
|------|------|
| HTTP 方法 | 所有檔案操作使用 POST（POST-only 機制）|
| 檔案驗證 | 前後端雙重驗證（類型 + 大小）|
| 權限控制 | 使用 RLS (Row-Level Security) 檢查 |
| 檔案命名 | UUID 前綴防止重複和猜測 |
| 校驗碼 | SHA256 完整性驗證 |

---

## 3. 表單頁面統一模式

### FormPageLayout 元件

所有新增/編輯頁面應使用 `FormPageLayout` 元件：

```tsx
import { FormPageLayout } from '../components/common/FormPage';

<FormPageLayout
  title={isEdit ? '編輯xxx' : '新增xxx'}
  backPath="/list"
  onSave={handleSave}
  onDelete={isEdit ? handleDelete : undefined}
  loading={isLoading}
  saving={isSaving}
>
  <Form form={form} layout="vertical">
    {/* 表單欄位 */}
  </Form>
</FormPageLayout>
```

### 路由結構規範

```typescript
// 列表頁
/entities                    → EntitiesPage

// 詳情頁
/entities/:id                → EntityDetailPage

// 新增頁
/entities/create             → EntityFormPage (isEdit=false)

// 編輯頁
/entities/:id/edit           → EntityFormPage (isEdit=true)

// 子實體
/entities/:id/sub/create     → SubEntityFormPage
/entities/:id/sub/:subId/edit → SubEntityFormPage
```

---

## 4. Tab 頁面拆分規範

### 目錄結構

```
pages/
└── entityName/
    ├── EntityDetailPage.tsx      # 主頁面（組合 Tabs）
    └── tabs/
        ├── index.ts              # 統一匯出
        ├── types.ts              # Props 型別定義
        ├── constants.ts          # Tab 相關常數
        ├── InfoTab.tsx           # 基本資訊 Tab
        ├── RelatedTab.tsx        # 關聯資料 Tab
        └── AttachmentsTab.tsx    # 附件 Tab
```

### Tab Props 型別定義

```typescript
// types.ts
export interface InfoTabProps {
  data: EntityData;
  isEditing: boolean;
  setIsEditing: (editing: boolean) => void;
  form: FormInstance;
  onSave: (values: FormValues) => Promise<void>;
}

export interface AttachmentsTabProps {
  entityId: number;
  attachments: Attachment[];
  loading: boolean;
  onRefresh: () => void;
  onUpload: (file: File) => Promise<void>;
  onDownload: (id: number) => void;
  onDelete: (id: number) => void;
}
```

---

## 5. 既有實作參考

| 功能 | 參考檔案 |
|------|----------|
| 導航模式表單 | `frontend/src/pages/CertificationFormPage.tsx` |
| Tab 拆分模式 | `frontend/src/pages/contractCase/tabs/` |
| 檔案上傳 UI | `frontend/src/components/document/operations/FileUploadSection.tsx` |
| 附件列表 UI | `frontend/src/components/document/operations/ExistingAttachmentsList.tsx` |
| 檔案 API | `frontend/src/api/filesApi.ts` |

---

## 變更記錄

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-01-26 | 初版建立，含導航模式、檔案上傳、表單頁面規範 |
