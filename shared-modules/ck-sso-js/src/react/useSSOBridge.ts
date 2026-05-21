/**
 * React hook wrapping attemptSSOBridge.
 *
 * 用途：consumer EntryPage / 「未登入入口」mount 時自動觸發 SSO bridge。
 *
 * @example
 * function EntryPage() {
 *   const navigate = useNavigate();
 *   const { state, retry } = useSSOBridge({
 *     apiBaseURL: 'https://lvrland.cksurvey.tw/api',
 *     onSuccess: () => navigate('/dashboard'),
 *   });
 *
 *   if (state === 'loading') return <div>正在驗證 SSO...</div>;
 *   return <LoginUI onRetrySSO={retry} />;
 * }
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  attemptSSOBridge,
  resetSSOBridgeState,
  type SSOBridgeConfig,
  type SSOBridgeResult,
} from '../sso-bridge';

export type SSOBridgeUIState = 'loading' | 'success' | 'failed' | 'skipped';

export interface UseSSOBridgeReturn {
  /** UI 渲染用的高階狀態 */
  state: SSOBridgeUIState;
  /** 上次 attempt 的完整結果 */
  result: SSOBridgeResult | null;
  /** 重置 lock + 重試（給「重新嘗試」按鈕） */
  retry: () => void;
}

export function useSSOBridge(
  config: SSOBridgeConfig & {
    /** false 則不自動觸發（給 conditional 用） */
    enabled?: boolean;
  },
): UseSSOBridgeReturn {
  const { enabled = true, storagePrefix = 'ck_sso_bridge', ...rest } = config;
  const [state, setState] = useState<SSOBridgeUIState>(enabled ? 'loading' : 'skipped');
  const [result, setResult] = useState<SSOBridgeResult | null>(null);
  // ref to avoid re-trigger on config 物件 identity 變
  const triggeredRef = useRef(false);

  const run = useCallback(async () => {
    const r = await attemptSSOBridge({ storagePrefix, ...rest });
    setResult(r);
    setState(r.ok ? 'success' : 'failed');
  }, [storagePrefix, rest]);

  useEffect(() => {
    if (!enabled) {
      setState('skipped');
      return;
    }
    if (triggeredRef.current) return;
    triggeredRef.current = true;
    void run();
  }, [enabled, run]);

  const retry = useCallback(() => {
    resetSSOBridgeState(storagePrefix);
    triggeredRef.current = false;
    setState('loading');
    void run();
  }, [storagePrefix, run]);

  return { state, result, retry };
}
