/**
 * 路由照「選單自己的宣告」擋（owner 2026-09-07）。
 *
 * ## 問題
 *
 * owner：「erp 圖譜前端無須檢視，但目前架構**知道網址就可檢視**」。
 *
 * 實測：`AppRouter` 用了 **117 次** `<ProtectedRoute>`，傳 `permissions` 的
 * **0 次** —— 也就是說路由層只問「有沒有登入」，不問「有沒有這個權限」。
 * 選單把項目藏起來，而網址照樣進得去。**藏起來不是擋住。**
 *
 * `ProtectedRoute` 本來就支援 `permissions`，只是沒有人傳 ——
 * 「能力做好了不等於有人在用」那一族。
 *
 * ## 為什麼不逐條路由標權限
 *
 * 117 條要標，而且會與選單的宣告**分成兩份各自演化**——這個 repo 對
 * 「同一件事有兩份宣告、沒有任何檢核在對」已經付過很多次學費
 * （最近一次是 `UserRole` 與 `role_permissions` 差了三個角色）。
 *
 * ⇒ 這支直接讀 `site_navigation_items.permission_required`：
 *   **選單說要什麼權限，路由就擋什麼**。兩者結構上不可能分家，
 *   而且在權限管理頁改一次，選單與路由同時生效。
 *
 * ## 這一層的定位（不要誤讀）
 *
 * 這是**介面層**的守衛，不是資安邊界。真正的邊界在 API 的
 * `require_permission`——前端擋不住 curl。它解決的是 owner 說的那件事：
 * 不該看到的頁面不會因為知道網址就打得開。
 * API 層的收斂是另一件事（`erp/` 之外仍有端點只有 `require_auth`）。
 *
 * ## 失效方向
 *
 * 選單資料載入失敗時**放行並記一筆 warning**，不是鎖住整個系統：
 * 一個暫時的網路錯誤讓所有人什麼都打不開，比讓人多看到一頁更糟，
 * 而真正的邊界本來就在後端。
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { navigationService } from '../services/navigationService';
import { logger } from '../services/logger';

interface NavPermissionRow {
  path?: string | null;
  permission_required?: string[] | string | null;
  is_enabled?: boolean;
}

/** 宣告表：`/erp/ledger` → `reports:erp:view` */
export type NavPermissionMap = Record<string, string>;

function normalizeRequired(v: NavPermissionRow['permission_required']): string | null {
  if (!v) return null;
  if (Array.isArray(v)) return v.length > 0 ? String(v[0]) : null;
  // DB 存的是 jsonb，取回來可能已是陣列，也可能是字串化的陣列
  const s = String(v).trim();
  if (!s || s === '[]') return null;
  try {
    const parsed = JSON.parse(s);
    if (Array.isArray(parsed)) return parsed.length > 0 ? String(parsed[0]) : null;
  } catch {
    /* 不是 JSON 就當成單一權限碼 */
  }
  return s;
}

export function buildNavPermissionMap(rows: NavPermissionRow[]): NavPermissionMap {
  const map: NavPermissionMap = {};
  for (const r of rows) {
    const path = (r.path || '').trim();
    if (!path || !path.startsWith('/')) continue;
    if (r.is_enabled === false) continue;
    const perm = normalizeRequired(r.permission_required);
    if (perm) map[path] = perm;
  }
  return map;
}

/**
 * 找出 `pathname` 適用的宣告：**最長的路徑前綴**。
 *
 * 詳情頁（`/erp/quotations/541`）在選單裡沒有自己的項目，但它屬於
 * `/erp/quotations` ——不做前綴比對的話，列表擋住了而詳情頁照樣打得開，
 * 那種擋法等於沒擋。
 *
 * 沒有任何宣告命中 ⇒ 回 null ＝**這條路由沒有宣告要什麼權限**，放行。
 * 這是誠實的：這一層只執行既有的宣告，不自己發明限制。
 */
export function resolveRequiredPermission(
  pathname: string, map: NavPermissionMap,
): string | null {
  let best: string | null = null;
  let bestLen = -1;
  for (const [path, perm] of Object.entries(map)) {
    if (pathname === path || pathname.startsWith(path.endsWith('/') ? path : `${path}/`)) {
      if (path.length > bestLen) {
        best = perm;
        bestLen = path.length;
      }
    }
  }
  return best;
}

export function useNavPermissionMap(): { map: NavPermissionMap; isLoading: boolean; isError: boolean } {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['nav-permission-map'],
    queryFn: async () => {
      // 走選單自己的服務 —— 不另開一條取單路徑，否則兩邊會拿到不同的資料
      const rows = (await navigationService.getNavigationItems()) as unknown as NavPermissionRow[];
      return buildNavPermissionMap(rows ?? []);
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  return useMemo(() => {
    if (isError) {
      // 放行並出聲 —— 靜默放行與靜默擋住一樣糟
      logger.warn('[NavPermissionGate] 選單宣告載入失敗，本次不做路由層權限檢查');
    }
    return { map: data ?? {}, isLoading, isError };
  }, [data, isLoading, isError]);
}
