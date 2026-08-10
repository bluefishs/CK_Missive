/**
 * 可指派人員清單 —— 排除已合併的分身帳號（ADR-0025 身分統一）。
 *
 * ## 為什麼需要這個
 *
 * 系統裡有三個人各有兩個帳號，且已在 2026-04-21 依 ADR-0025 合併：
 *
 *   本尊 id 13 `jujuiacc`（王駿穠(fly)）  ← 分身 id 7  王駿穠
 *   本尊 id 17 `cyh0206188`（張雅惠）     ← 分身 id 12 張雅惠
 *   本尊 id 19 `luke19630612`（李昭德）   ← 分身 id 11 李昭德
 *
 * 合併只做了兩件事：RLS 查詢展開分身群組（所以**權限一直是對的**），
 * 以及登記合併紀錄。它**沒有**把分身帳號從各種人員下拉裡拿掉 ——
 * 於是「承辦同仁」「資產保管人」「PM 承辦」等下拉會把同一個人列兩次，
 * 其中張雅惠與李昭德**兩筆完全同名，使用者無從分辨該選哪一個**
 * （owner 2026-08-10 回報：「同仁變成代碼」「重複編碼問題」）。
 *
 * 選錯的後果不是壞掉、而是更難察覺：指派會掛在分身帳號上，畫面看起來正常，
 * 但那筆資料與這個人的其他資料分屬兩個 user_id。
 *
 * ## 為什麼收在這裡
 *
 * 四個頁面各自組人員下拉（承辦同仁／資產／PM 承辦／承攬案件）。
 * 分開修就是四份會各自演化的規則，下次只會修好其中一兩個。
 */

export interface AssignableUserLike {
  id: number;
  username?: string | null;
  full_name?: string | null;
  email?: string | null;
  is_active?: boolean;
  /** 分身帳號指向的本尊；null/undefined = 本人就是本尊 */
  canonical_user_id?: number | null;
}

/**
 * 只留「可以被指派」的帳號。
 *
 * @param users     API 回來的使用者清單
 * @param opts.keep 一定要保留的 id（例如編輯既有指派時，那筆的 user_id
 *                  可能正是分身帳號 —— 濾掉的話 Select 找不到對應選項，
 *                  會直接顯示原始數字，看起來就像「同仁變成代碼」）
 */
export function filterAssignableUsers<T extends AssignableUserLike>(
  users: readonly T[] | undefined | null,
  opts?: { keep?: readonly number[] },
): T[] {
  if (!Array.isArray(users)) return [];
  const keep = new Set(opts?.keep ?? []);
  return users.filter((u) => {
    if (keep.has(u.id)) return true;
    // 停用帳號不可被指派 —— 離職同仁、以及系統種子帳號 `superuser`
    // （admin@example.com，2025-12-28 起即停用）都屬此類。
    //
    // 2026-08-10 owner 回報「不該出現 superuser」。刻意**不特判帳號名稱**：
    // 「這個帳號還在不在職」本來就由 is_active 表達，另立一份系統帳號名單
    // 只會變成第二份需要維護的事實，而且下一個種子帳號還是會漏掉。
    if (u.is_active === false) return false;
    return u.canonical_user_id == null;
  });
}

/**
 * 顯示名稱：姓名優先，沒有才退回帳號，都沒有才顯示 id。
 *
 * 退到 id 時保留 `#` 前綴 —— 讓「這裡缺資料」看得出來，
 * 而不是顯示一個看起來像編號的裸數字。
 */
export function userDisplayName(u: AssignableUserLike): string {
  return u.full_name || u.username || `#${u.id}`;
}
