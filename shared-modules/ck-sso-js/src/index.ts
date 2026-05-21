/**
 * ck-sso-js public API.
 *
 * Vanilla TS / Vue / Svelte: import { attemptSSOBridge }
 * React: import { useSSOBridge }
 */
export {
  attemptSSOBridge,
  resetSSOBridgeState,
  getSSOBridgeState,
  type SSOBridgeConfig,
  type SSOBridgeResult,
} from './sso-bridge';

export { useSSOBridge, type UseSSOBridgeReturn, type SSOBridgeUIState } from './react/useSSOBridge';

export const CK_SSO_JS_VERSION = '1.0.0';
