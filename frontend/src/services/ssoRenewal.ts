/**
 * SSO session 隨活動延長（sliding renewal）— 消費端呼叫。
 *
 * ## 為什麼
 *
 * `ck_employee` 原本是「從登入那刻起固定 8 小時」，時間一到整條鏈同時死亡
 * （消費端 session、refresh_token、IdP cookie），I7「無痛續命」無憑證可用。
 * owner 2026-08-07 實測：08:49 登入 → 16:49 cookie 死 → 17:39 操作直接失敗、
 * 刪除動作遺失。8h ≈ 一個完整工作日，**上滿一天班必然撞到一次**。
 *
 * IdP 端 `POST https://www.cksurvey.tw/auth/renew` 負責驗證＋重簽（含撤銷檢查
 * 與 7 天絕對上限）；本模組只負責「在使用者還在用的時候，適時去敲它一下」。
 *
 * ## 設計取捨
 *
 * - **沿用既有的活動訊號**（`useIdleTimeout` 的事件監聽），不另建一套監聽器 ——
 *   否則就是同一件事兩套實作。
 * - **30 分鐘節流**：cookie 壽命 8h，半小時續一次已遠遠足夠；更密只是浪費請求。
 * - **失敗不阻斷**：續期失敗不代表當下 session 壞了（可能只是網路抖動），
 *   使用者的操作不該因此中斷。但**也不能永遠沉默** —— 連續失敗會 warn，
 *   且 401 代表「IdP 認為這個 session 不該再延長」（撤銷／停用／達絕對上限），
 *   那時停止再試，避免對 IdP 空打。
 * - **cookie 由瀏覽器帶**：`.cksurvey.tw` 與各子網域屬同一 site，
 *   `SameSite=Lax` 允許此請求攜帶 cookie；故必須 `credentials: 'include'`。
 */
import { logger } from './logger';

const RENEW_URL = 'https://www.cksurvey.tw/auth/renew';

/** 兩次續期之間的最小間隔 —— cookie 壽命 8h，半小時一次已遠遠足夠 */
const RENEW_INTERVAL_MS = 30 * 60 * 1000;

let lastAttemptAt = 0;
let consecutiveFailures = 0;
/** IdP 明確拒絕（401）後就停手 —— 再試也不會成功，只是對 IdP 空打 */
let disabled = false;
let inFlight: Promise<void> | null = null;

/** 測試/重登後重置 */
export function resetSsoRenewalState(): void {
  lastAttemptAt = 0;
  consecutiveFailures = 0;
  disabled = false;
  inFlight = null;
}

/**
 * 有活動時呼叫。內建節流與單飛，重複呼叫是安全的。
 * 僅在公網（跨子網域 SSO 情境）有意義；內網 mock 認證不需要。
 */
export function maybeRenewSsoSession(): void {
  if (disabled) return;
  if (inFlight) return;

  const now = Date.now();
  if (now - lastAttemptAt < RENEW_INTERVAL_MS) return;
  lastAttemptAt = now;

  inFlight = fetch(RENEW_URL, {
    method: 'POST',
    credentials: 'include', // 必要：cookie 在 .cksurvey.tw，屬同 site 但跨 origin
    headers: { 'Content-Type': 'application/json' },
  })
    .then(async (res) => {
      if (res.ok) {
        consecutiveFailures = 0;
        logger.log('[SSO-Renew] session 已延長');
        return;
      }
      if (res.status === 401) {
        // IdP 明確表示不該再延長（撤銷／停用／達 7 天絕對上限）。
        // 這不是錯誤 —— 是政策。停止再試，讓既有的到期流程接手。
        disabled = true;
        let reason = '';
        try {
          reason = ((await res.json()) as { reason?: string }).reason || '';
        } catch {
          /* 回應非 JSON 時不強求 */
        }
        logger.log(`[SSO-Renew] IdP 不再延長此 session（${reason || 'unknown'}）`);
        return;
      }
      throw new Error(`HTTP ${res.status}`);
    })
    .catch((e: unknown) => {
      consecutiveFailures += 1;
      // 單次失敗多半是網路抖動，不吵；連續失敗代表真的有問題，要留下痕跡 ——
      // 「續期一直失敗」的最終症狀是使用者在 8h 後被中斷，那時已無從追查。
      if (consecutiveFailures >= 3) {
        logger.warn(
          `[SSO-Renew] 連續 ${consecutiveFailures} 次續期失敗，session 將於原到期時間結束`,
          e,
        );
      }
    })
    .finally(() => {
      inFlight = null;
    });
}
