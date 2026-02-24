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

      if (statusCode === 403) {
        notification.warning({
          message: '權限不足',
          description: message || '您沒有權限執行此操作',
          duration: 5,
        });
      } else if (statusCode >= 500) {
        notification.error({
          message: '伺服器錯誤',
          description: message || '伺服器暫時無法處理請求，請稍後重試',
          duration: 5,
        });
      } else if (statusCode === 0) {
        notification.error({
          message: '網路連線失敗',
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
