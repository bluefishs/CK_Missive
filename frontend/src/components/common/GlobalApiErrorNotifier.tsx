/**
 * 全域 API 錯誤通知元件
 *
 * 訂閱 apiErrorBus，自動顯示 403/500/網路錯誤通知。
 * 業務邏輯錯誤 (400/409/422) 不在此處處理，由元件自行 catch。
 *
 * 放置於 <AntdApp> 內部，確保可使用 App.useApp() 的 notification。
 *
 * @version 1.0.0
 * @date 2026-02-24
 */

import { useEffect, useRef } from 'react';
import { App } from 'antd';
import { apiErrorBus, ApiException } from '../../api/errors';

const GlobalApiErrorNotifier: React.FC = () => {
  const { notification } = App.useApp();
  const lastErrorTime = useRef(0);

  useEffect(() => {
    const unsubscribe = apiErrorBus.subscribe((error: ApiException) => {
      // 防抖：3 秒內同類錯誤不重複顯示
      const now = Date.now();
      if (now - lastErrorTime.current < 3000) return;
      lastErrorTime.current = now;

      const { statusCode, message } = error;

      if (statusCode === 429) {
        notification.warning({
          title: '請求過於頻繁',
          description: '系統偵測到短時間內大量請求，已暫時限制。請稍候再試。',
          duration: 5,
        });
      } else if (statusCode === 403) {
        // L68 (2026-06-10): 403 須區分 CSRF vs 真權限。CSRFMiddleware 的 detail 含
        //   「csrf_token」/「X-CSRF-Token」字樣（cookie 過期 / iOS Safari 清除）→ 非權限問題，
        //   提示重新整理即可；否則誤標「權限不足」會誤導 owner 往權限方向排查（誤導成本高）。
        const isCsrf = /csrf|x-csrf/i.test(message || '');
        notification.warning({
          title: isCsrf ? '安全憑證已過期' : '權限不足',
          description: isCsrf
            ? '請重新整理頁面以更新安全憑證後再試（若持續發生請重新登入）'
            : message || '您沒有權限執行此操作',
          duration: 5,
        });
      } else if (statusCode >= 500) {
        notification.error({
          title: '伺服器錯誤',
          description: message || '伺服器暫時無法處理請求，請稍後重試',
          duration: 5,
        });
      } else if (statusCode === 0) {
        notification.error({
          title: '網路連線失敗',
          description: message || '請檢查網路連線後重試',
          duration: 5,
        });
      }
    });

    return unsubscribe;
  }, [notification]);

  return null;
};

export default GlobalApiErrorNotifier;
