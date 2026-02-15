/**
 * 部署管理 API 服務
 *
 * @version 1.0.0
 * @date 2026-02-02
 */

import apiClient from './client';
import { API_ENDPOINTS } from './endpoints';

// 型別從 types/ 匯入 (SSOT)
import type {
  ServiceStatus,
  DeploymentStatus,
  ServiceHealth,
  SystemStatusResponse,
  DeploymentRecord,
  DeploymentHistoryResponse,
  TriggerDeploymentRequest,
  TriggerDeploymentResponse,
  RollbackRequest,
  RollbackResponse,
  DeploymentLog,
  DeploymentLogsResponse,
  DeploymentConfig,
  DeploymentHistoryParams,
} from '../types/api';

// 向後相容 re-export
export type {
  ServiceStatus,
  DeploymentStatus,
  ServiceHealth,
  SystemStatusResponse,
  DeploymentRecord,
  DeploymentHistoryResponse,
  TriggerDeploymentRequest,
  TriggerDeploymentResponse,
  RollbackRequest,
  RollbackResponse,
  DeploymentLog,
  DeploymentLogsResponse,
  DeploymentConfig,
  DeploymentHistoryParams,
};

// =============================================================================
// API 函數
// =============================================================================

/**
 * 取得系統狀態 (POST-only 安全模式)
 */
export async function getSystemStatus(): Promise<SystemStatusResponse> {
  return apiClient.post<SystemStatusResponse>(API_ENDPOINTS.DEPLOYMENT.STATUS, {});
}

/**
 * 取得部署歷史 (POST-only 安全模式)
 */
export async function getDeploymentHistory(
  params?: DeploymentHistoryParams
): Promise<DeploymentHistoryResponse> {
  return apiClient.post<DeploymentHistoryResponse>(
    API_ENDPOINTS.DEPLOYMENT.HISTORY,
    params || {}
  );
}

/**
 * 觸發部署
 */
export async function triggerDeployment(
  request: TriggerDeploymentRequest
): Promise<TriggerDeploymentResponse> {
  return apiClient.post<TriggerDeploymentResponse>(
    API_ENDPOINTS.DEPLOYMENT.TRIGGER,
    request
  );
}

/**
 * 回滾部署
 */
export async function rollbackDeployment(
  request: RollbackRequest
): Promise<RollbackResponse> {
  return apiClient.post<RollbackResponse>(
    API_ENDPOINTS.DEPLOYMENT.ROLLBACK,
    request
  );
}

/**
 * 取得部署日誌 (POST-only 安全模式)
 */
export async function getDeploymentLogs(
  runId: number
): Promise<DeploymentLogsResponse> {
  return apiClient.post<DeploymentLogsResponse>(
    API_ENDPOINTS.DEPLOYMENT.LOGS(runId),
    {}
  );
}

/**
 * 取得部署配置 (POST-only 安全模式)
 */
export async function getDeploymentConfig(): Promise<DeploymentConfig> {
  return apiClient.post<DeploymentConfig>(API_ENDPOINTS.DEPLOYMENT.CONFIG, {});
}

// =============================================================================
// 匯出
// =============================================================================

const deploymentApi = {
  getSystemStatus,
  getDeploymentHistory,
  triggerDeployment,
  rollbackDeployment,
  getDeploymentLogs,
  getDeploymentConfig,
};

export default deploymentApi;
