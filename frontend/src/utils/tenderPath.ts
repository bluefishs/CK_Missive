/**
 * ADR-0032: Tender 多源識別的 URL 決策集中點
 *
 * 所有 navigate 到 tender detail 的地方都應經此函式，
 * 而非直接拼字串。新增資料源只需改這裡。
 */

const EZBID_ID_PATTERN = /^\d+$/;

export interface TenderLikeRecord {
  source?: string;
  unit_id?: string;
  job_number?: string;
  ezbid_id?: string;
}

/**
 * 判斷一筆 tender 記錄是否為 ezbid 來源
 */
export function isEzbidRecord(record: TenderLikeRecord): boolean {
  if (record.source === 'ezbid' || record.source === 'ezbid_db') return true;
  if (record.ezbid_id) return true;
  // 啟發式 fallback：純數字 unit_id + 無 job_number
  if (
    record.unit_id &&
    EZBID_ID_PATTERN.test(record.unit_id) &&
    !record.job_number
  ) {
    return true;
  }
  return false;
}

/**
 * 組出 tender detail 頁的 URL
 *
 * PCC: /tender/pcc/:unit_id/:job_number
 * ezbid: /tender/ezbid/:ezbid_id
 */
export function getTenderDetailPath(record: TenderLikeRecord): string {
  if (isEzbidRecord(record)) {
    const id = record.ezbid_id || record.unit_id || '';
    return `/tender/ezbid/${encodeURIComponent(id)}`;
  }
  return `/tender/pcc/${encodeURIComponent(record.unit_id || '')}/${encodeURIComponent(record.job_number || '')}`;
}
