/**
 * Layout hooks 共用型別
 * 提取至獨立檔案以消除 useMenuItems ↔ useNavigationData 循環依賴
 */

import { NavigationItem as PermissionNavigationItem } from '../../../hooks';

/** 擴展導覽項目介面 */
export interface NavigationItem extends PermissionNavigationItem {
  id?: number;
  parent_id?: number;
  level?: number;
  description?: string;
  target?: string;
}
