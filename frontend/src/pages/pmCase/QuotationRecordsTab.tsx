/**
 * 報價紀錄 Tab — PM 案件的報價單上傳/管理
 *
 * 2026-08-19：**實作已抽到 `components/common/AttachmentPanel`**。
 *
 * 這裡保留為薄包裝，只做兩件事：把「報價紀錄」這組用詞傳進去，
 * 以及維持既有的 import 路徑（引用它的頁面不必改）。
 *
 * 為什麼是抽取而不是新寫共用元件：盤點全前端 9 處附件實作後，
 * 這一份是唯一四項功能都齊全的（上傳/列表/預覽/刪除）——
 * 另外新寫一個等於製造第 10 份。
 *
 * @version 3.0.0 — 改為 AttachmentPanel 的薄包裝（行為不變）
 */
import { AttachmentPanel } from '../../components/common/AttachmentPanel';

interface QuotationRecordsTabProps {
  caseCode: string;
  isEditing?: boolean;
}

export default function QuotationRecordsTab({ caseCode, isEditing = false }: QuotationRecordsTabProps) {
  return (
    <AttachmentPanel
      caseCode={caseCode}
      isEditing={isEditing}
      title="報價紀錄"
      uploadTitle="上傳報價單"
      emptyText={isEditing ? '尚無報價紀錄，請上傳報價單' : '尚無報價紀錄'}
      showDocType
    />
  );
}
