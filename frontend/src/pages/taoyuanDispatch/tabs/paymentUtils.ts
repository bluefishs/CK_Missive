/**
 * 契金維護工具函數
 *
 * 從 DispatchPaymentTab.tsx 提取，避免 React 元件檔案混合匯出工具函數
 * 導致 Vite Fast Refresh 失敗 (hmr invalidate)。
 *
 * @version 1.0.0
 * @date 2026-02-11
 */

/** 作業類別代碼與標籤對照 */
export const WORK_TYPE_MAP: Record<string, string> = {
  '01': '地上物查估',
  '02': '土地協議市價查估',
  '03': '土地徵收市價查估',
  '04': '相關計畫書製作',
  '05': '測量作業',
  '06': '樁位測釘作業',
  '07': '辦理教育訓練',
};

/**
 * 從 work_type 字串解析出作業類別代碼列表
 * 例如: "01.地上物查估作業, 03.土地徵收市價查估作業" => ["01", "03"]
 */
export const parseWorkTypeCodes = (workType: string | string[] | undefined): string[] => {
  if (!workType) return [];

  // 如果是陣列（表單中的 Checkbox.Group 值）
  if (Array.isArray(workType)) {
    const result: string[] = [];
    for (const item of workType) {
      if (typeof item === 'string') {
        const match = item.match(/^(\d{2})\./);
        if (match && match[1]) {
          result.push(match[1]);
        }
      }
    }
    return result;
  }

  // 如果是字串
  const matches = workType.match(/(\d{2})\./g);
  return matches ? matches.map(m => m.replace('.', '')) : [];
};

/**
 * 檢查契金金額與作業類別的一致性
 * 返回不一致的欄位列表
 */
export const validatePaymentConsistency = (
  workTypeCodes: string[],
  amounts: Record<string, number | undefined>
): { field: string; code: string; label: string; amount: number }[] => {
  const inconsistencies: { field: string; code: string; label: string; amount: number }[] = [];

  for (let i = 1; i <= 7; i++) {
    const code = i.toString().padStart(2, '0');
    const field = `work_${code}_amount`;
    const amount = amounts[field];

    // 如果有金額但不在作業類別中
    if (amount && amount > 0 && !workTypeCodes.includes(code)) {
      inconsistencies.push({
        field,
        code,
        label: WORK_TYPE_MAP[code] || `作業${code}`,
        amount,
      });
    }
  }

  return inconsistencies;
};
