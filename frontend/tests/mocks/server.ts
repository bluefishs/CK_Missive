/**
 * MSW Mock Server
 * 測試用 Mock Server
 */
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// 建立 mock server
export const server = setupServer(...handlers);
