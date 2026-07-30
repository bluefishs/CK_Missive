/**
 * API 錯誤訊息萃取 — SSOT
 *
 * 2026-07-30 建立。觸發：owner 反覆遇到「操作其實成功／後端已說明真因，
 * 但畫面只顯示通用失敗訊息」，導致誤判與反覆重試：
 *   - 核銷審核 `onError: () => message.error('審核失敗')`
 *     → 吞掉後端真因「此發票狀態為『verified』，不可進行審核操作」
 *       （＝其實前一次已審核成功，只是畫面沒更新）
 *   - 同型前例：建案 409 曾顯示通用「建案失敗」而非「此標案已建案: XXX」（07-20 已修）
 *
 * 規則：能拿到後端 detail/message 就顯示它，拿不到才退回通用字串。
 */
import { ApiException } from '../api/errors';

/** FastAPI 常見錯誤負載形狀（detail 可能是字串或驗證錯誤陣列） */
interface ErrorPayload {
  detail?: string | { msg?: string }[];
  message?: string;
  error?: { message?: string };
}

/**
 * 從任意錯誤物件萃取「可讀且具體」的訊息。
 *
 * @param err       catch 到的錯誤（ApiException / AxiosError / Error / unknown）
 * @param fallback  萃取不到時的通用訊息
 */
export function extractApiMessage(err: unknown, fallback: string): string {
  if (!err) return fallback;

  // 1) 專案標準錯誤型別
  if (err instanceof ApiException && err.message) return err.message;

  // 2) axios 風格：error.response.data.{detail|message|error.message}
  const data = (err as { response?: { data?: ErrorPayload } })?.response?.data
    ?? (err as { data?: ErrorPayload })?.data;
  if (data) {
    const { detail } = data;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) {
      const msgs = detail.map((d) => d?.msg).filter(Boolean);
      if (msgs.length) return msgs.join('；');
    }
    if (data.message) return data.message;
    if (data.error?.message) return data.error.message;
  }

  // 3) 一般 Error（排除無資訊的預設訊息）
  if (err instanceof Error && err.message && !/^Request failed/i.test(err.message)) {
    return err.message;
  }
  return fallback;
}
