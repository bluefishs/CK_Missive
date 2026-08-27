/**
 * 回歸鎖：角色的中文名稱只能有一個來源。
 *
 * ## 起因
 *
 * owner 2026-08-27：「/profile 顯示『承辦同仁』，但右上角仍顯示『一般使用者』」。
 *
 * 同一個 `role='staff'`，三個地方三個答案：
 *
 *     USER_ROLES.staff.name_zh        「業務同仁」   ← SSOT，早就存在
 *     AccountInfoCard.getRoleTag      「承辦同仁」   ← 自己一份
 *     Header.getRoleDisplayName       「一般使用者」 ← 自己一份，**沒有 staff 這個 case**
 *
 * Header 那份最難看的不是漏了 case，是它的 `default:` 把**任何認不得的角色**
 * 都降級成「一般使用者」—— 一個看起來完全正常的值。DB 裡有 8 個人 role='staff'，
 * 他們在右上角一直看到「一般使用者」，而畫面上看不出那是「沒對應到」。
 *
 * 而且 Header 的本地函式與 SSOT **同名**（`getRoleDisplayName`），
 * 等於把 SSOT 那支遮蔽掉了 —— import 少了一行，行為就整個換人。
 *
 * 順帶修掉的兩個：篩選清單 `userTableColumns` 漏 staff（8 人篩不出來）、
 * `useUserColumns` 漏 staff 且多一個系統裡不存在的 `guest`（永遠篩不到任何人）。
 *
 * 這支測試鎖的是：**名稱與選項都必須從 USER_ROLES 導出**。
 */
import { describe, it, expect } from 'vitest';
import {
  USER_ROLES,
  ROLE_ORDER,
  ROLE_FILTER_OPTIONS,
  getRoleDisplayName,
} from '../constants/permissions';

/** DB 實測存在的角色值（2026-08-27：staff 8 / admin 7 / user 2 / superuser 1）。 */
const ROLES_IN_DB = ['superuser', 'admin', 'staff', 'user'] as const;

describe('角色顯示名稱 SSOT', () => {
  it('DB 裡出現的每一個角色，SSOT 都對得出中文名', () => {
    for (const r of ROLES_IN_DB) {
      expect(USER_ROLES[r], `USER_ROLES 缺少 ${r}`).toBeDefined();
      expect(getRoleDisplayName(r)).not.toBe(r);
    }
  });

  it('staff 是「業務同仁」，不是「承辦同仁」', () => {
    // 「承辦同仁」在本系統是另一個概念（專案人員指派 project_staff），
    // 角色用同一個詞會撞在一起——這個斷言是為了擋住有人再改回去。
    expect(getRoleDisplayName('staff')).toBe('業務同仁');
    expect(getRoleDisplayName('staff')).not.toBe('承辦同仁');
  });

  it('認不得的角色回 roleKey 本身，不得降級成某個正常值', () => {
    // Header 原本的 `default: '一般使用者'` 就是這個反例：
    // 「我不認得」與「這個人是一般使用者」在畫面上長得一模一樣。
    expect(getRoleDisplayName('nonexistent_role')).toBe('nonexistent_role');
    expect(getRoleDisplayName('nonexistent_role')).not.toBe('一般使用者');
  });

  it('篩選選項由 SSOT 導出，涵蓋所有角色且沒有多餘的', () => {
    const values = ROLE_FILTER_OPTIONS.map((o) => o.value);
    expect(values).toEqual([...ROLE_ORDER]);
    // staff 必須在（原本兩處都漏了，8 位業務同仁篩不出來）
    expect(values).toContain('staff');
    // guest 不是這個系統的角色（useUserColumns 原本有，永遠篩不到人）
    expect(values).not.toContain('guest');
    // 每一個選項的文字都必須等於 SSOT 的 name_zh
    for (const o of ROLE_FILTER_OPTIONS) {
      expect(o.text).toBe(getRoleDisplayName(o.value));
      expect(o.label).toBe(o.text);
    }
  });

  it('位階由高到低', () => {
    expect(ROLE_ORDER[0]).toBe('superuser');
    expect(ROLE_ORDER[ROLE_ORDER.length - 1]).toBe('unverified');
  });
});
