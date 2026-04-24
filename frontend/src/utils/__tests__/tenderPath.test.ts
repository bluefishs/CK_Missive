/**
 * Regression tests for ADR-0032 — getTenderDetailPath 集中決策
 */
import { describe, it, expect } from 'vitest';
import { getTenderDetailPath, isEzbidRecord } from '../tenderPath';

describe('getTenderDetailPath (ADR-0032)', () => {
  it('PCC: unit_id + job_number → /tender/pcc/...', () => {
    const path = getTenderDetailPath({ unit_id: 'A.15.3.2', job_number: '115-703' });
    expect(path).toBe('/tender/pcc/A.15.3.2/115-703');
  });

  it('ezbid: ezbid_id → /tender/ezbid/...', () => {
    const path = getTenderDetailPath({ ezbid_id: '2227632' });
    expect(path).toBe('/tender/ezbid/2227632');
  });

  it('ezbid source 明確標記 → /tender/ezbid/...', () => {
    const path = getTenderDetailPath({ unit_id: '2227632', source: 'ezbid' });
    expect(path).toBe('/tender/ezbid/2227632');
  });

  it('ezbid_db source → /tender/ezbid/...', () => {
    const path = getTenderDetailPath({ unit_id: '2229486', source: 'ezbid_db' });
    expect(path).toBe('/tender/ezbid/2229486');
  });

  it('啟發式 fallback: 純數字 unit_id + 無 job_number → ezbid', () => {
    const path = getTenderDetailPath({ unit_id: '1234567' });
    expect(path).toBe('/tender/ezbid/1234567');
  });

  it('PCC 格式 unit_id 含字母 → 正確辨識為 PCC', () => {
    const path = getTenderDetailPath({ unit_id: 'A.15.3.2', job_number: '115-703' });
    expect(path).not.toContain('/ezbid/');
    expect(path).toContain('/pcc/');
  });

  it('中文/特殊字元正確 encode', () => {
    const path = getTenderDetailPath({ unit_id: 'A.15.3.2', job_number: '115-測試' });
    expect(path).toContain(encodeURIComponent('115-測試'));
  });
});

describe('isEzbidRecord', () => {
  it('source=ezbid → true', () => {
    expect(isEzbidRecord({ source: 'ezbid' })).toBe(true);
  });

  it('有 ezbid_id → true', () => {
    expect(isEzbidRecord({ ezbid_id: '123' })).toBe(true);
  });

  it('PCC 複合鍵 → false', () => {
    expect(isEzbidRecord({ unit_id: 'A.15.3.2', job_number: '115-703' })).toBe(false);
  });

  it('空 record → false', () => {
    expect(isEzbidRecord({})).toBe(false);
  });
});
