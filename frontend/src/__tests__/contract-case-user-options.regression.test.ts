/**
 * 回歸鎖：承攬案件的人員／廠商下拉，跨頁面共用快取時形狀必須一致。
 *
 * ## 為什麼有這支測試
 *
 * owner 三次回報 `/contract-cases/194/staff/create`「同仁變成代號」：
 *
 *   2026-08-04  我把 label 從「姓名 (email)」簡化成只剩姓名 → 清單資訊變少
 *   2026-08-20  該頁打 `users/list`（admin-only）→ 非管理員 403 → 選項為空
 *   2026-08-27  **兩處都改打 assignable 了、源對齊了，但回傳形狀沒有對齊**
 *
 * 第三次的形狀是：詳情頁與新增頁共用 queryKey `contract-case-user-options`，
 * 但一個回 `{id, name, email}`、一個回原始 `User[]`。誰先載入誰決定快取內容，
 * 而使用者的動線正是「詳情頁 → 新增承辦同仁」⇒ 新增頁拿到 `{id,name,email}`，
 * `userDisplayName` 要的 `full_name`／`username` 都不存在 ⇒ 退回 `#${id}`。
 *
 * **它只在那一條動線上出現** —— 直接開新增頁的網址是正常的。
 * 這就是它被修過兩次還能反覆回報、而走查也驗不出來的原因，
 * 也是這支測試存在的理由：把「動線」寫成可執行的斷言。
 *
 * 現在兩處共用 `useUsersDropdown`（回原始 `User[]`），結構上不可能再分岔；
 * `queryKey_drift_audit` 的第三種形態會擋住它再度分岔。
 * 這支測試鎖的是**退化本身**：一旦快取裡放的是已 map 過的形狀，label 就會變代號。
 */
import { describe, it, expect } from 'vitest';
import { filterAssignableUsers, userDisplayName } from '../utils/assignableUsers';

const RAW_USERS = [
  { id: 3,  full_name: '洪慶忠',      username: '洪慶忠',   email: 'a@x', is_active: true,  canonical_user_id: null },
  { id: 13, full_name: '王駿穠(fly)', username: 'jujuiacc', email: 'b@x', is_active: true,  canonical_user_id: null },
  { id: 7,  full_name: '王駿穠',      username: '王駿穠',   email: 'c@x', is_active: true,  canonical_user_id: 13 },
  { id: 1,  full_name: 'SuperUser',   username: 'superuser', email: 'd@x', is_active: false, canonical_user_id: null },
];

const buildOptions = (cached: unknown[]) =>
  filterAssignableUsers(cached as never)
    .map((u) => ({ value: u.id, label: userDisplayName(u) }));

describe('承攬案件人員下拉：跨頁面共用快取的形狀契約', () => {
  it('拿到原始 User[] 時顯示姓名，並濾掉分身與停用帳號', () => {
    const opts = buildOptions(RAW_USERS);
    expect(opts).toEqual([
      { value: 3,  label: '洪慶忠' },
      { value: 13, label: '王駿穠(fly)' },
    ]);
  });

  it('姓名缺漏時退回帳號，而不是裸數字', () => {
    expect(userDisplayName({ id: 9, full_name: null, username: 'someone' })).toBe('someone');
  });

  it('⚠️ 快取裡若是已 map 過的形狀，label 會退化成「代號」——這正是被回報的症狀', () => {
    // 詳情頁曾經放進同一個 cache key 的形狀
    const mappedByDetailPage = filterAssignableUsers(RAW_USERS)
      .map((u) => ({ id: u.id, name: userDisplayName(u), email: u.email }));

    const degraded = buildOptions(mappedByDetailPage);
    expect(degraded.map((o) => o.label)).toEqual(['#3', '#13']);

    // 斷言的用意不是「這樣才對」，而是把退化的形狀釘住：
    // 只要有人再讓已 map 過的資料進到這個快取，畫面就會是這個樣子。
    expect(degraded.every((o) => /^#\d+$/.test(o.label))).toBe(true);
  });

  it('#id 前綴要保留 —— 讓「這裡缺資料」看得出來，而不是像一個編號', () => {
    expect(userDisplayName({ id: 42 })).toBe('#42');
    expect(userDisplayName({ id: 42 })).not.toBe('42');
  });
});
