/**
 * 資料庫檢視器共用型別定義
 */
import type { TableInfo } from '../../../types/api';

/** 增強的表格資訊介面（含中文名稱、分類等） */
export interface EnhancedTableInfo extends TableInfo {
  chinese_name: string;
  description: string;
  category: string;
  frontend_pages: string[];
  api_endpoints: string[];
  main_fields: string[];
  color: string;
}
