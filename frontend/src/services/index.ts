/**
 * 服務統一導出
 * 
 * @version 2.0
 * @author Claude Desktop
 * @date 2024-09-04
 */

export { apiConfig, API_ENDPOINTS } from './apiConfig';
export type { ApiEnvironment } from './apiConfig';

export { httpClient, HttpError } from './httpClient';

export * from './documentService';

// Ensure this file is treated as a module
export {};