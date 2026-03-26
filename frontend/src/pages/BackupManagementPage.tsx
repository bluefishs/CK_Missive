import React, { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card, Tabs, Button, Typography, Row, Col,
  Alert, Form, App, Spin
} from 'antd';
import {
  CloudServerOutlined, ReloadOutlined,
  DatabaseOutlined, CloudUploadOutlined,
  ExclamationCircleOutlined, WarningOutlined,
  SettingOutlined, HistoryOutlined, ClearOutlined
} from '@ant-design/icons';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  BackupItem,
  BackupListResponse,
  RemoteBackupConfig,
  SchedulerStatus,
  BackupLogListResponse
} from '../types/api';
import {
  BackupListTab,
  RemoteBackupTab,
  SchedulerTab as SchedulerTabComponent,
  BackupLogsTab,
  BackupStatsCards,
} from './backup';

const { Title, Text } = Typography;

interface EnvironmentStatus {
  docker_available: boolean;
  docker_path: string;
  last_success_time: string | null;
  consecutive_failures: number;
  backup_dir_exists: boolean;
  uploads_dir_exists: boolean;
}

export const BackupManagementPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState('list');
  const [remoteConfigForm] = Form.useForm();
  const [logFilters, setLogFilters] = useState({
    page: 1,
    page_size: 20,
    action_filter: undefined as string | undefined,
    status_filter: undefined as string | undefined
  });

  const {
    data: envStatus = null,
    isError: envError,
    refetch: refetchEnvStatus,
  } = useQuery({
    queryKey: ['backup', 'environment-status'],
    queryFn: () => apiClient.post<EnvironmentStatus>(API_ENDPOINTS.BACKUP.ENVIRONMENT_STATUS, {}),
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: backups = null,
    isLoading: backupsLoading,
    isError: backupsError,
  } = useQuery({
    queryKey: ['backup', 'list'],
    queryFn: () => apiClient.post<BackupListResponse>(API_ENDPOINTS.BACKUP.LIST, {}),
    staleTime: 5 * 60 * 1000,
  });

  const statistics = backups?.statistics || null;

  const {
    data: remoteConfig = null,
  } = useQuery({
    queryKey: ['backup', 'remote-config'],
    queryFn: () => apiClient.post<RemoteBackupConfig>(API_ENDPOINTS.BACKUP.REMOTE_CONFIG, {}),
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (remoteConfig && activeTab === 'remote') {
      remoteConfigForm.setFieldsValue({
        remote_path: remoteConfig.remote_path || '',
        sync_enabled: remoteConfig.sync_enabled,
        sync_interval_hours: remoteConfig.sync_interval_hours,
      });
    }
  }, [remoteConfig, remoteConfigForm, activeTab]);

  const {
    data: schedulerStatus = null,
  } = useQuery({
    queryKey: ['backup', 'scheduler-status'],
    queryFn: () => apiClient.post<SchedulerStatus>(API_ENDPOINTS.BACKUP.SCHEDULER_STATUS, {}),
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: logs = null,
    refetch: refetchLogs,
  } = useQuery({
    queryKey: ['backup', 'logs', logFilters],
    queryFn: () => apiClient.post<BackupLogListResponse>(API_ENDPOINTS.BACKUP.LOGS, logFilters),
    staleTime: 2 * 60 * 1000,
    enabled: activeTab === 'logs',
  });

  const refreshAll = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['backup'] });
    message.success('資料已重新整理');
  }, [queryClient, message]);

  const createBackupMutation = useMutation({
    mutationFn: () => apiClient.post(API_ENDPOINTS.BACKUP.CREATE, {
      include_database: true,
      include_attachments: true,
      retention_days: 7
    }),
    onSuccess: () => {
      message.success('備份建立成功');
      queryClient.invalidateQueries({ queryKey: ['backup', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['backup', 'logs'] });
    },
    onError: () => {
      message.error('備份建立失敗');
    },
  });

  const deleteBackupMutation = useMutation({
    mutationFn: (params: { backup_name: string; backup_type: string }) =>
      apiClient.post(API_ENDPOINTS.BACKUP.DELETE, params),
    onSuccess: () => {
      message.success('備份已刪除');
      queryClient.invalidateQueries({ queryKey: ['backup', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['backup', 'logs'] });
    },
    onError: () => {
      message.error('刪除備份失敗');
    },
  });

  const restoreBackupMutation = useMutation({
    mutationFn: (backupName: string) =>
      apiClient.post(API_ENDPOINTS.BACKUP.RESTORE, { backup_name: backupName }),
    onSuccess: () => {
      message.success('資料庫還原成功');
      queryClient.invalidateQueries({ queryKey: ['backup', 'logs'] });
    },
    onError: () => {
      message.error('還原失敗');
    },
  });

  const updateRemoteConfigMutation = useMutation({
    mutationFn: (values: { remote_path: string; sync_enabled: boolean; sync_interval_hours: number }) =>
      apiClient.post(API_ENDPOINTS.BACKUP.REMOTE_CONFIG_UPDATE, values),
    onSuccess: () => {
      message.success('異地備份設定已更新');
      queryClient.invalidateQueries({ queryKey: ['backup', 'remote-config'] });
    },
    onError: () => {
      message.error('更新設定失敗');
    },
  });

  const remoteSyncMutation = useMutation({
    mutationFn: () => apiClient.post<{ synced_files: number; total_size_kb: number }>(
      API_ENDPOINTS.BACKUP.REMOTE_SYNC, {}
    ),
    onSuccess: (result) => {
      message.success(`同步完成: ${result.synced_files} 個檔案，共 ${result.total_size_kb} KB`);
      queryClient.invalidateQueries({ queryKey: ['backup', 'remote-config'] });
    },
    onError: () => {
      message.error('同步失敗');
    },
  });

  const cleanupOrphansMutation = useMutation({
    mutationFn: () => apiClient.post<{ cleaned_count: number; files: string[] }>(
      API_ENDPOINTS.BACKUP.CLEANUP, {}
    ),
    onSuccess: (result) => {
      if (result.cleaned_count > 0) {
        message.success(`已清理 ${result.cleaned_count} 個孤立檔案`);
        queryClient.invalidateQueries({ queryKey: ['backup', 'list'] });
      } else {
        message.info('沒有需要清理的孤立檔案');
      }
    },
    onError: () => {
      message.error('清理失敗');
    },
  });

  const schedulerToggleMutation = useMutation({
    mutationFn: (isRunning: boolean) => {
      if (isRunning) {
        return apiClient.post(API_ENDPOINTS.BACKUP.SCHEDULER_STOP, {});
      } else {
        return apiClient.post(API_ENDPOINTS.BACKUP.SCHEDULER_START, {});
      }
    },
    onSuccess: (_data, isRunning) => {
      message.success(isRunning ? '排程器已停止' : '排程器已啟動');
      queryClient.invalidateQueries({ queryKey: ['backup', 'scheduler-status'] });
    },
    onError: () => {
      message.error('操作失敗');
    },
  });

  const handleCreateBackup = () => {
    modal.confirm({
      title: '建立備份',
      content: '確定要立即建立備份嗎？這可能需要一些時間。',
      icon: <DatabaseOutlined />,
      okText: '確定',
      cancelText: '取消',
      onOk: () => createBackupMutation.mutateAsync(),
    });
  };

  const handleDeleteBackup = (item: BackupItem) => {
    const backupName = item.filename || item.dirname;
    if (!backupName) return;
    deleteBackupMutation.mutate({ backup_name: backupName, backup_type: item.type });
  };

  const handleRestoreBackup = (item: BackupItem) => {
    if (item.type !== 'database' || !item.filename) return;
    modal.confirm({
      title: '還原資料庫',
      content: (
        <Alert
          type="warning"
          title="警告：此操作會覆蓋現有資料"
          description={`確定要從 ${item.filename} 還原資料庫嗎？此操作不可逆。`}
        />
      ),
      icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
      okText: '確定還原',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => restoreBackupMutation.mutateAsync(item.filename!),
    });
  };

  const handleUpdateRemoteConfig = (values: {
    remote_path: string;
    sync_enabled: boolean;
    sync_interval_hours: number;
  }) => {
    updateRemoteConfigMutation.mutate(values);
  };

  const handleRemoteSync = () => {
    remoteSyncMutation.mutate();
  };

  const handleCleanupOrphans = () => {
    cleanupOrphansMutation.mutate();
  };

  const handleSchedulerToggle = () => {
    schedulerToggleMutation.mutate(!!schedulerStatus?.running);
  };

  const loading = backupsLoading
    || createBackupMutation.isPending
    || deleteBackupMutation.isPending
    || restoreBackupMutation.isPending
    || updateRemoteConfigMutation.isPending
    || remoteSyncMutation.isPending
    || cleanupOrphansMutation.isPending
    || schedulerToggleMutation.isPending;

  return (
    <ResponsiveContent maxWidth="full" padding="medium" style={{ background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        {(envError || backupsError) && (
          <Alert type="warning" showIcon closable style={{ marginBottom: 16 }}
            message="部分備份資料載入失敗，顯示內容可能不完整" />
        )}
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={2} style={{ margin: 0, color: '#1976d2' }}>
              <CloudServerOutlined style={{ marginRight: 12 }} />
              備份管理
            </Title>
            <Text type="secondary">管理系統備份、異地同步與排程設定</Text>
          </Col>
          <Col>
            <Button
              icon={<ReloadOutlined />}
              onClick={refreshAll}
              loading={loading}
            >
              重新整理
            </Button>
          </Col>
        </Row>

        {envStatus && !envStatus.docker_available && (
          <Alert
            title="Docker 環境不可用"
            description={`Docker CLI 路徑: ${envStatus.docker_path}。資料庫備份功能將無法使用，請確認 Docker Desktop 已啟動。`}
            type="error"
            showIcon
            icon={<WarningOutlined />}
            style={{ marginBottom: 16 }}
            action={
              <Button size="small" onClick={() => refetchEnvStatus()}>
                重新檢測
              </Button>
            }
          />
        )}

        {envStatus && envStatus.consecutive_failures > 0 && (
          <Alert
            title={`備份連續失敗 ${envStatus.consecutive_failures} 次`}
            description={
              envStatus.last_success_time
                ? `最後成功備份: ${new Date(envStatus.last_success_time).toLocaleString('zh-TW')}`
                : '尚無成功的備份記錄'
            }
            type="warning"
            showIcon
            closable
            style={{ marginBottom: 16 }}
            action={
              <Button size="small" icon={<ClearOutlined />} onClick={handleCleanupOrphans}>
                清理孤立檔案
              </Button>
            }
          />
        )}

        <BackupStatsCards statistics={statistics} envStatus={envStatus} />

        <Card>
          <Spin spinning={loading}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                {
                  key: 'list',
                  label: <span><DatabaseOutlined /> 備份列表</span>,
                  children: (
                    <BackupListTab
                      backups={backups}
                      loading={loading}
                      onCreateBackup={handleCreateBackup}
                      onDeleteBackup={handleDeleteBackup}
                      onRestoreBackup={handleRestoreBackup}
                    />
                  )
                },
                {
                  key: 'remote',
                  label: <span><CloudUploadOutlined /> 異地備份</span>,
                  children: (
                    <RemoteBackupTab
                      remoteConfig={remoteConfig}
                      form={remoteConfigForm}
                      loading={loading}
                      onUpdateConfig={handleUpdateRemoteConfig}
                      onRemoteSync={handleRemoteSync}
                    />
                  )
                },
                {
                  key: 'scheduler',
                  label: <span><SettingOutlined /> 排程器</span>,
                  children: (
                    <SchedulerTabComponent
                      schedulerStatus={schedulerStatus}
                      loading={loading}
                      onSchedulerToggle={handleSchedulerToggle}
                    />
                  )
                },
                {
                  key: 'logs',
                  label: <span><HistoryOutlined /> 備份日誌</span>,
                  children: (
                    <BackupLogsTab
                      logs={logs}
                      logFilters={logFilters}
                      loading={loading}
                      onLogFiltersChange={setLogFilters}
                      onRefreshLogs={() => refetchLogs()}
                    />
                  )
                }
              ]}
            />
          </Spin>
        </Card>
      </div>
    </ResponsiveContent>
  );
};
