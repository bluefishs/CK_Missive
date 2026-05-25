/**
 * ck-navigation v2.0 - NavigationItem TS contract
 *
 * Consumer should fetch nav tree from
 *   POST /api/secure-site-management/navigation/action  body: { action: "get_tree" }
 * and render with their own Sidebar/Header components.
 *
 * (v1.0 ship 過 frontend layout components, 5/18 因 ROUTES hardcode +
 *  5 層 transitive deps 半接通失敗 → v2.0 改 backend-only)
 */

export interface NavigationItem {
  key: string;
  title: string;
  path: string;
  icon?: string;
  permission_required?: string[];
  is_visible: boolean;
  is_enabled: boolean;
  sort_order: number;
  children?: NavigationItem[];
}

export interface NavigationTreeResponse {
  success: boolean;
  data: {
    items: NavigationItem[];
  };
}
