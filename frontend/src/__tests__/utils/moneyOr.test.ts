/**
 * fmtMoneyOr：金額為 0 或空時用語意文字，不印「0」（2026-09-09 owner「未開請款／—／0 三種並存，數字 0 容易誤解」）。
 */
import { describe, it, expect } from 'vitest';
import { fmtMoney, fmtMoneyOr } from '../../utils/money';

describe('fmtMoneyOr', () => {
  it('0／null／空字串 → 語意字', () => {
    expect(fmtMoneyOr(0, '未開請款')).toBe('未開請款');
    expect(fmtMoneyOr(null, '未開請款')).toBe('未開請款');
    expect(fmtMoneyOr('', '未收款')).toBe('未收款');
    expect(fmtMoneyOr(0.4, '已收齊')).toBe('已收齊'); // 取整到元後是 0
  });
  it('有金額 → 與 fmtMoney 同格式', () => {
    expect(fmtMoneyOr(1546613, '未開請款')).toBe(fmtMoney(1546613));
    expect(fmtMoneyOr('40888276.00', 'x')).toBe('40,888,276');
  });
});
