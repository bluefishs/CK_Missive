/**
 * 部署管理 API 服務
 *
 * @version 1.0.0
 * @date 2026-02-02
 */

import apiClient from './client';
import { API_ENDPOINTS } from './endpoints';

// =============================================================================
// 型別定義
// =============================================================================

/** 服務狀態 */
export type ServiceStatus = 'running' | 'stopped' | 'error' | 'unknown';

/** 部署狀態 */
export type DeploymentStatus = 'success' | 'failure' | 'in_progress' | 'cancelled' | 'pending';

/** 服務健康狀態 */
export interface ServiceHealth {
  name: string;
  status: ServiceStatus;
  version?: string;
  uptime?: string;
  last_check: string;
}

/** 系統狀態回應 */
export interface SystemStatusResponse {
  overall_status: ServiceStatus;
  services: ServiceHealth[];
  current_version?: string;
  last_deployment?: string;
  environment: string;
}

/** 部署記錄 */
export interface DeploymentRecord {
  id: number;
  run_number: number;
  status: DeploymentStatus;
  conclusion?: string;
  branch: string;
  commit_sha: string;
  commit_message?: string;
  triggered_by: string;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  url: string;
}

/** 部署歷史回應 */
export interface DeploymentHistoryResponse {
  total: number;
  records: DeploymentRecord[];
}

/** 觸發部署請求 */
export interface TriggerDeploymentRequest {
  ref?: string;
  force_rebuild?: boolean;
  skip_backup?: boolean;
}

/** 觸發部署回應 */
export interface TriggerDeploymentResponse {
  success: boolean;
  message: string;
  workflow_run_id?: number;
  url?: string;
}

/** 回滾請求 */
export interface RollbackRequest {
  target_version?: string;
  confirm: boolean;
}

/** 回滾回應 */
export interface RollbackResponse {
  success: boolean;
  message: string;
  previous_version?: string;
  current_version?: string;
}

/** 部署日誌 */
export interface DeploymentLog {
  job_name: string;
  status: string;
  logs: string;
}

/** 部署日誌回應 */
export interface DeploymentLogsResponse {
  run_id: number;
  status: string;
  jobs: DeploymentLog[];
}

/** 部署配置 */
export interface DeploymentConfig {
  github_repo: string;
  workflow_file: string;
  github_token_configured: boolean;
  deploy_path: string;
  environment: string;
}

/** 部署歷史查詢參數 */
export interface DeploymentHistoryParams {
  page?: number;
  page_size?: number;
  status?: string;
}

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
