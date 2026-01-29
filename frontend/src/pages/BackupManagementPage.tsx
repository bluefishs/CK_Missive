/**
 * 備份管理頁面
 * 提供備份列表、異地備份設定、排程器管理、備份日誌查詢
 *
 * @version 1.0.0
 * @date 2026-01-29
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Tabs, Button, Space, Typography, Row, Col,
  Statistic, Alert, Modal, Input, Form, Tag, App,
  Tooltip, Popconfirm, Switch, Spin, DatePicker, Select, InputNumber
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CloudServerOutlined, ReloadOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined, SyncOutlined,
  PlayCircleOutlined, PauseCircleOutlined, HistoryOutlined,
  SettingOutlined, DatabaseOutlined, FolderOutlined,
  CloudUploadOutlined, ExclamationCircleOutlined
} from '@ant-design/icons';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  BackupItem,
  BackupListResponse,
  BackupStatistics,
  RemoteBackupConfig,
  SchedulerStatus,
  BackupLogEntry,
  BackupLogListResponse
} from '../types/api';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

export const BackupManagementPage: React.FC = () => {
  const { message, modal } = App.useApp();

  // 狀態
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('list');

  // 備份列表狀態
  const [backups, setBackups] = useState<BackupListResponse | null>(null);
  const [statistics, setStatistics] = useState<BackupStatistics | null>(null);

  // 異地備份設定狀態
  const [remoteConfig, setRemoteConfig] = useState<RemoteBackupConfig | null>(null);
  const [remoteConfigForm] = Form.useForm();

  // 排程器狀態
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);

  // 備份日誌狀態
  const [logs, setLogs] = useState<BackupLogListResponse | null>(null);
  const [logFilters, setLogFilters] = useState({
    page: 1,
    page_size: 20,
    action_filter: undefined as string | undefined,
    status_filter: undefined as string | undefined
  });

  // =========================================================================
  // 資料載入
  // =========================================================================

  const fetchBackups = useCallback(async () => {
    try {
      const data = await apiClient.post<BackupListResponse>(API_ENDPOINTS.BACKUP.LIST, {});
      setBackups(data);
      setStatistics(data.statistics);
    } catch (error) {
      console.error('載入備份列表失敗:', error);
      message.error('載入備份列表失敗');
    }
  }, [message]);

  const fetchRemoteConfig = useCallback(async () => {
    try {
      const data = await apiClient.post<RemoteBackupConfig>(API_ENDPOINTS.BACKUP.REMOTE_CONFIG, {});
      setRemoteConfig(data);
      remoteConfigForm.setFieldsValue({
        remote_path: data.remote_path || '',
        sync_enabled: data.sync_enabled,
        sync_interval_hours: data.sync_interval_hours
      });
    } catch (error) {
      console.error('載入異地備份設定失敗:', error);
    }
  }, [remoteConfigForm]);

  const fetchSchedulerStatus = useCallback(async () => {
    try {
      const data = await apiClient.post<SchedulerStatus>(API_ENDPOINTS.BACKUP.SCHEDULER_STATUS, {});
      setSchedulerStatus(data);
    } catch (error) {
      console.error('載入排程器狀態失敗:', error);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      const data = await apiClient.post<BackupLogListResponse>(API_ENDPOINTS.BACKUP.LOGS, logFilters);
      setLogs(data);
    } catch (error) {
      console.error('載入備份日誌失敗:', error);
    }
  }, [logFilters]);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchBackups(),
        fetchRemoteConfig(),
        fetchSchedulerStatus(),
        fetchLogs()
      ]);
      message.success('資料已重新整理');
    } finally {
      setLoading(false);
    }
  }, [fetchBackups, fetchRemoteConfig, fetchSchedulerStatus, fetchLogs, message]);

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    }
  }, [logFilters, activeTab, fetchLogs]);

  // =========================================================================
  // 備份操作
  // =========================================================================

  const handleCreateBackup = async () => {
    modal.confirm({
      title: '建立備份',
      content: '確定要立即建立備份嗎？這可能需要一些時間。',
      icon: <DatabaseOutlined />,
      okText: '確定',
      cancelText: '取消',
      onOk: async () => {
        setLoading(true);
        try {
          await apiClient.post(API_ENDPOINTS.BACKUP.CREATE, {
            include_database: true,
            include_attachments: true,
            retention_days: 7
          });
          message.success('備份建立成功');
          await fetchBackups();
        } catch (error) {
          message.error('備份建立失敗');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const handleDeleteBackup = async (item: BackupItem) => {
    const backupName = item.filename || item.dirname;
    if (!backupName) return;

    try {
      await apiClient.post(API_ENDPOINTS.BACKUP.DELETE, {
        backup_name: backupName,
        backup_type: item.type
      });
      message.success('備份已刪除');
      await fetchBackups();
    } catch (error) {
      message.error('刪除備份失敗');
    }
  };

  const handleRestoreBackup = async (item: BackupItem) => {
    if (item.type !== 'database' || !item.filename) return;

    modal.confirm({
      title: '還原資料庫',
      content: (
        <Alert
          type="warning"
          message="警告：此操作會覆蓋現有資料"
          description={`確定要從 ${item.filename} 還原資料庫嗎？此操作不可逆。`}
        />
      ),
      icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
      okText: '確定還原',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setLoading(true);
        try {
          await apiClient.post(API_ENDPOINTS.BACKUP.RESTORE, {
            backup_name: item.filename
          });
          message.success('資料庫還原成功');
        } catch (error) {
          message.error('還原失敗');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  // =========================================================================
  // 異地備份操作
  // =========================================================================

  const handleUpdateRemoteConfig = async (values: {
    remote_path: string;
    sync_enabled: boolean;
    sync_interval_hours: number;
  }) => {
    setLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.BACKUP.REMOTE_CONFIG_UPDATE, values);
      message.success('異地備份設定已更新');
      await fetchRemoteConfig();
    } catch (error) {
      message.error('更新設定失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoteSync = async () => {
    setLoading(true);
    try {
      const result = await apiClient.post<{ synced_files: number; total_size_kb: number }>(
        API_ENDPOINTS.BACKUP.REMOTE_SYNC,
        {}
      );
      message.success(`同步完成: ${result.synced_files} 個檔案，共 ${result.total_size_kb} KB`);
      await fetchRemoteConfig();
    } catch (error) {
      message.error('同步失敗');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 排程器操作
  // =========================================================================

  const handleSchedulerToggle = async () => {
    setLoading(true);
    try {
      if (schedulerStatus?.running) {
        await apiClient.post(API_ENDPOINTS.BACKUP.SCHEDULER_STOP, {});
        message.success('排程器已停止');
      } else {
        await apiClient.post(API_ENDPOINTS.BACKUP.SCHEDULER_START, {});
        message.success('排程器已啟動');
      }
      await fetchSchedulerStatus();
    } catch (error) {
      message.error('操作失敗');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 表格欄位定義
  // =========================================================================

  const backupColumns: ColumnsType<BackupItem> = [
    {
      title: '備份名稱',
      key: 'name',
      render: (_, record) => (
        <Space>
          {record.type === 'database' ? <DatabaseOutlined /> : <FolderOutlined />}
          <Text>{record.filename || record.dirname}</Text>
          {record.mode === 'incremental' && (
            <Tag color="cyan">增量</Tag>
          )}
        </Space>
      )
    },
    {
      title: '類型',
      dataIndex: 'type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'database' ? 'blue' : 'green'}>
          {type === 'database' ? '資料庫' : '附件'}
        </Tag>
      )
    },
    {
      title: '大小',
      key: 'size',
      width: 120,
      render: (_, record) => (
        record.size_kb
          ? `${record.size_kb} KB`
          : record.size_mb
            ? `${record.size_mb} MB`
            : '-'
      )
    },
    {
      title: '統計',
      key: 'stats',
      width: 180,
      render: (_, record) => {
        if (record.mode === 'incremental' && (record.copied_count !== undefined || record.file_count !== undefined)) {
          return (
            <Tooltip title={`已複製: ${record.copied_count || 0}, 跳過: ${record.skipped_count || 0}, 移除: ${record.removed_count || 0}`}>
              <Text type="secondary">
                {record.file_count || 0} 檔案
                {record.copied_count ? ` (+${record.copied_count})` : ''}
              </Text>
            </Tooltip>
          );
        }
        return record.file_count ? `${record.file_count} 檔案` : '-';
      }
    },
    {
      title: '建立時間',
      dataIndex: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-TW')
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          {record.type === 'database' && (
            <Tooltip title="還原">
              <Button
                type="link"
                size="small"
                icon={<SyncOutlined />}
                onClick={() => handleRestoreBackup(record)}
              />
            </Tooltip>
          )}
          {/* 禁止刪除增量備份主目錄 */}
          {record.dirname !== 'attachments_latest' && (
            <Popconfirm
              title="確定刪除此備份？"
              onConfirm={() => handleDeleteBackup(record)}
              okText="確定"
              cancelText="取消"
            >
              <Tooltip title="刪除">
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ];

  const logColumns: ColumnsType<BackupLogEntry> = [
    {
      title: '時間',
      dataIndex: 'timestamp',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-TW')
    },
    {
      title: '操作',
      dataIndex: 'action',
      width: 100,
      render: (action: string) => {
        const actionMap: Record<string, { text: string; color: string }> = {
          create: { text: '建立', color: 'blue' },
          delete: { text: '刪除', color: 'red' },
          restore: { text: '還原', color: 'orange' },
          sync: { text: '同步', color: 'cyan' },
          config_update: { text: '設定', color: 'purple' }
        };
        const info = actionMap[action] || { text: action, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      }
    },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 80,
      render: (status: string) => (
        status === 'success'
          ? <Tag icon={<CheckCircleOutlined />} color="success">成功</Tag>
          : <Tag icon={<CloseCircleOutlined />} color="error">失敗</Tag>
      )
    },
    {
      title: '詳細資訊',
      dataIndex: 'details',
      ellipsis: true
    },
    {
      title: '操作者',
      dataIndex: 'operator',
      width: 100
    }
  ];

  // =========================================================================
  // Tab 內容渲染
  // =========================================================================

  const renderBackupList = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Row justify="space-between" align="middle">
        <Col>
          <Alert
            message="備份管理"
            description="管理系統備份檔案，可建立、刪除或還原備份。"
            type="info"
            showIcon
          />
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<DatabaseOutlined />}
            onClick={handleCreateBackup}
            loading={loading}
          >
            立即備份
          </Button>
        </Col>
      </Row>

      <Card title="資料庫備份" size="small">
        <Table
          columns={backupColumns}
          dataSource={backups?.database_backups || []}
          rowKey="path"
          size="small"
          pagination={{ pageSize: 10 }}
          loading={loading}
        />
      </Card>

      <Card title="附件備份" size="small">
        <Table
          columns={backupColumns}
          dataSource={backups?.attachment_backups || []}
          rowKey="path"
          size="small"
          pagination={{ pageSize: 10 }}
          loading={loading}
        />
      </Card>
    </Space>
  );

  const renderRemoteConfig = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Alert
        message="異地備份設定"
        description="設定異地備份路徑，系統會自動將備份同步到指定位置。"
        type="info"
        showIcon
      />

      <Card title="目前狀態" size="small">
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="同步狀態"
              value={remoteConfig?.sync_status === 'idle' ? '閒置' : remoteConfig?.sync_status === 'syncing' ? '同步中' : '錯誤'}
              valueStyle={{
                color: remoteConfig?.sync_status === 'error' ? '#cf1322' : '#3f8600'
              }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="最後同步時間"
              value={remoteConfig?.last_sync_time
                ? new Date(remoteConfig.last_sync_time).toLocaleString('zh-TW')
                : '尚未同步'}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="同步間隔"
              value={remoteConfig?.sync_interval_hours || 24}
              suffix="小時"
            />
          </Col>
        </Row>
      </Card>

      <Card title="設定" size="small">
        <Form
          form={remoteConfigForm}
          layout="vertical"
          onFinish={handleUpdateRemoteConfig}
        >
          <Form.Item
            name="remote_path"
            label="異地備份路徑"
            rules={[{ required: true, message: '請輸入異地備份路徑' }]}
            extra="可使用本地路徑或網路共享路徑 (如: \\\\server\\backup)"
          >
            <Input
              prefix={<FolderOutlined />}
              placeholder="例如: D:\Backup 或 \\server\backup"
            />
          </Form.Item>

          <Form.Item
            name="sync_enabled"
            label="啟用自動同步"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="sync_interval_hours"
            label="同步間隔 (小時)"
            rules={[{ required: true, message: '請輸入同步間隔' }]}
          >
            <InputNumber min={1} max={168} style={{ width: 120 }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                儲存設定
              </Button>
              <Button
                icon={<CloudUploadOutlined />}
                onClick={handleRemoteSync}
                loading={loading}
                disabled={!remoteConfig?.remote_path}
              >
                立即同步
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );

  const renderScheduler = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Alert
        message="排程器設定"
        description="管理自動備份排程，系統會在設定的時間自動執行備份。"
        type="info"
        showIcon
      />

      <Card title="排程器狀態" size="small">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="運行狀態"
              value={schedulerStatus?.running ? '運行中' : '已停止'}
              valueStyle={{
                color: schedulerStatus?.running ? '#3f8600' : '#cf1322'
              }}
              prefix={schedulerStatus?.running ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="備份時間"
              value={schedulerStatus?.backup_time || '--:--'}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="下次執行"
              value={schedulerStatus?.next_backup
                ? new Date(schedulerStatus.next_backup).toLocaleString('zh-TW')
                : '-'}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="上次執行"
              value={schedulerStatus?.last_backup
                ? new Date(schedulerStatus.last_backup).toLocaleString('zh-TW')
                : '-'}
            />
          </Col>
        </Row>

        <Row gutter={16} style={{ marginTop: 24 }}>
          <Col span={8}>
            <Statistic
              title="總備份次數"
              value={schedulerStatus?.stats?.total_backups || 0}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="成功次數"
              value={schedulerStatus?.stats?.successful_backups || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="失敗次數"
              value={schedulerStatus?.stats?.failed_backups || 0}
              valueStyle={{ color: schedulerStatus?.stats?.failed_backups ? '#cf1322' : undefined }}
            />
          </Col>
        </Row>
      </Card>

      <Card title="控制" size="small">
        <Space>
          <Button
            type={schedulerStatus?.running ? 'default' : 'primary'}
            icon={schedulerStatus?.running ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={handleSchedulerToggle}
            loading={loading}
          >
            {schedulerStatus?.running ? '停止排程器' : '啟動排程器'}
          </Button>
        </Space>
      </Card>
    </Space>
  );

  const renderLogs = () => (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Alert
        message="備份日誌"
        description="查看所有備份操作的歷史記錄。"
        type="info"
        showIcon
      />

      <Card title="篩選條件" size="small">
        <Row gutter={16}>
          <Col span={6}>
            <Select
              placeholder="操作類型"
              style={{ width: '100%' }}
              allowClear
              value={logFilters.action_filter}
              onChange={(v) => setLogFilters(prev => ({ ...prev, action_filter: v, page: 1 }))}
              options={[
                { value: 'create', label: '建立' },
                { value: 'delete', label: '刪除' },
                { value: 'restore', label: '還原' },
                { value: 'sync', label: '同步' },
                { value: 'config_update', label: '設定' }
              ]}
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="狀態"
              style={{ width: '100%' }}
              allowClear
              value={logFilters.status_filter}
              onChange={(v) => setLogFilters(prev => ({ ...prev, status_filter: v, page: 1 }))}
              options={[
                { value: 'success', label: '成功' },
                { value: 'failed', label: '失敗' }
              ]}
            />
          </Col>
          <Col span={6}>
            <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
              重新整理
            </Button>
          </Col>
        </Row>
      </Card>

      <Table
        columns={logColumns}
        dataSource={logs?.logs || []}
        rowKey="id"
        size="small"
        loading={loading}
        pagination={{
          current: logs?.page || 1,
          pageSize: logs?.page_size || 20,
          total: logs?.total || 0,
          showTotal: (total) => `共 ${total} 筆記錄`,
          onChange: (page, pageSize) => setLogFilters(prev => ({
            ...prev,
            page,
            page_size: pageSize
          }))
        }}
      />
    </Space>
  );

  // =========================================================================
  // 主要渲染
  // =========================================================================

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        {/* 頁面標題 */}
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

        {/* 統計卡片 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="資料庫備份"
                value={statistics?.database_backup_count || 0}
                prefix={<DatabaseOutlined style={{ color: '#1976d2' }} />}
                suffix="個"
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="附件備份"
                value={statistics?.attachment_backup_count || 0}
                prefix={<FolderOutlined style={{ color: '#52c41a' }} />}
                suffix="個"
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="總備份大小"
                value={statistics?.total_size_mb || 0}
                precision={2}
                suffix="MB"
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="排程狀態"
                value={schedulerStatus?.running ? '運行中' : '已停止'}
                valueStyle={{
                  color: schedulerStatus?.running ? '#3f8600' : '#cf1322'
                }}
                prefix={schedulerStatus?.running ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* 主要內容 */}
        <Card>
          <Spin spinning={loading}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                {
                  key: 'list',
                  label: <span><DatabaseOutlined /> 備份列表</span>,
                  children: renderBackupList()
                },
                {
                  key: 'remote',
                  label: <span><CloudUploadOutlined /> 異地備份</span>,
                  children: renderRemoteConfig()
                },
                {
                  key: 'scheduler',
                  label: <span><SettingOutlined /> 排程器</span>,
                  children: renderScheduler()
                },
                {
                  key: 'logs',
                  label: <span><HistoryOutlined /> 備份日誌</span>,
                  children: renderLogs()
                }
              ]}
            />
          </Spin>
        </Card>
      </div>
    </div>
  );
};
