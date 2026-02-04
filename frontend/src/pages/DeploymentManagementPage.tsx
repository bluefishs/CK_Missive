/**
 * 部署管理頁面
 *
 * 提供系統部署狀態監控、部署歷史、觸發部署和回滾操作功能。
 *
 * @version 1.0.0
 * @date 2026-02-02
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Space,
  Table,
  Tag,
  Button,
  Alert,
  Modal,
  message,
  Tooltip,
  Descriptions,
  Timeline,
  Spin,
  Badge,
  Popconfirm,
  Select,
  Switch,
  Collapse,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  RocketOutlined,
  RollbackOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  HistoryOutlined,
  ReloadOutlined,
  GithubOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  BranchesOutlined,
  FileTextOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-tw';
import type { ColumnsType } from 'antd/es/table';

import deploymentApi, {
  SystemStatusResponse,
  DeploymentRecord,
  DeploymentHistoryResponse,
  TriggerDeploymentResponse,
  RollbackResponse,
  DeploymentLogsResponse,
  DeploymentConfig,
  ServiceStatus,
  DeploymentStatus,
} from '../api/deploymentApi';
import { logger } from '../utils/logger';

dayjs.extend(relativeTime);
dayjs.locale('zh-tw');

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

// =============================================================================
// 狀態標籤元件
// =============================================================================

const ServiceStatusTag: React.FC<{ status: ServiceStatus }> = ({ status }) => {
  const config: Record<ServiceStatus, { color: string; icon: React.ReactNode; text: string }> = {
    running: { color: 'success', icon: <CheckCircleOutlined />, text: '運行中' },
    stopped: { color: 'default', icon: <CloseCircleOutlined />, text: '已停止' },
    error: { color: 'error', icon: <ExclamationCircleOutlined />, text: '異常' },
    unknown: { color: 'warning', icon: <ClockCircleOutlined />, text: '未知' },
  };

  const cfg = config[status] || config.unknown;
  return (
    <Tag color={cfg.color} icon={cfg.icon}>
      {cfg.text}
    </Tag>
  );
};

const DeploymentStatusTag: React.FC<{ status: DeploymentStatus; conclusion?: string }> = ({
  status,
  conclusion,
}) => {
  const defaultConfig = { color: 'warning', icon: <ClockCircleOutlined />, text: '等待中' };
  const config: Record<DeploymentStatus, { color: string; icon: React.ReactNode; text: string }> = {
    success: { color: 'success', icon: <CheckCircleOutlined />, text: '成功' },
    failure: { color: 'error', icon: <CloseCircleOutlined />, text: '失敗' },
    in_progress: { color: 'processing', icon: <SyncOutlined spin />, text: '進行中' },
    cancelled: { color: 'default', icon: <CloseCircleOutlined />, text: '已取消' },
    pending: defaultConfig,
  };

  const key: DeploymentStatus = status === 'success' && conclusion === 'failure' ? 'failure' : status;
  const { color, icon, text } = config[key] || defaultConfig;
  return (
    <Tag color={color} icon={icon}>
      {text}
    </Tag>
  );
};

// =============================================================================
// 主頁面元件
// =============================================================================

const DeploymentManagementPage: React.FC = () => {
  // 狀態
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [deployHistory, setDeployHistory] = useState<DeploymentHistoryResponse | null>(null);
  const [deployConfig, setDeployConfig] = useState<DeploymentConfig | null>(null);
  const [selectedLogs, setSelectedLogs] = useState<DeploymentLogsResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);

  const [triggerModalVisible, setTriggerModalVisible] = useState(false);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [configModalVisible, setConfigModalVisible] = useState(false);

  // 觸發部署選項
  const [triggerRef, setTriggerRef] = useState('main');
  const [forceRebuild, setForceRebuild] = useState(false);
  const [skipBackup, setSkipBackup] = useState(false);

  // 分頁
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // =============================================================================
  // 資料載入
  // =============================================================================

  const loadSystemStatus = useCallback(async () => {
    setLoading(true);
    try {
      const data = await deploymentApi.getSystemStatus();
      setSystemStatus(data);
    } catch (error) {
      logger.error('載入系統狀態失敗:', error);
      message.error('載入系統狀態失敗');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDeployHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await deploymentApi.getDeploymentHistory({
        page: currentPage,
        page_size: pageSize,
      });
      setDeployHistory(data);
    } catch (error) {
      logger.error('載入部署歷史失敗:', error);
      // 不顯示錯誤訊息，可能是未配置 GitHub Token
    } finally {
      setHistoryLoading(false);
    }
  }, [currentPage, pageSize]);

  const loadDeployConfig = useCallback(async () => {
    try {
      const data = await deploymentApi.getDeploymentConfig();
      setDeployConfig(data);
    } catch (error) {
      logger.error('載入部署配置失敗:', error);
    }
  }, []);

  useEffect(() => {
    loadSystemStatus();
    loadDeployHistory();
    loadDeployConfig();
  }, [loadSystemStatus, loadDeployHistory, loadDeployConfig]);

  // 自動刷新 (每 30 秒)
  useEffect(() => {
    const interval = setInterval(() => {
      loadSystemStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, [loadSystemStatus]);

  // =============================================================================
  // 操作函數
  // =============================================================================

  const handleTriggerDeploy = async () => {
    setTriggerLoading(true);
    try {
      const result: TriggerDeploymentResponse = await deploymentApi.triggerDeployment({
        ref: triggerRef,
        force_rebuild: forceRebuild,
        skip_backup: skipBackup,
      });

      if (result.success) {
        message.success(result.message);
        setTriggerModalVisible(false);
        // 重新載入歷史
        setTimeout(() => loadDeployHistory(), 3000);
      } else {
        message.error(result.message);
      }
    } catch (error) {
      logger.error('觸發部署失敗:', error);
      message.error('觸發部署失敗');
    } finally {
      setTriggerLoading(false);
    }
  };

  const handleRollback = async () => {
    setRollbackLoading(true);
    try {
      const result: RollbackResponse = await deploymentApi.rollbackDeployment({
        confirm: true,
      });

      if (result.success) {
        message.success(result.message);
        loadSystemStatus();
      } else {
        message.error(result.message);
      }
    } catch (error) {
      logger.error('回滾失敗:', error);
      message.error('回滾操作失敗');
    } finally {
      setRollbackLoading(false);
    }
  };

  const handleViewLogs = async (runId: number) => {
    setLogsLoading(true);
    setLogsModalVisible(true);
    try {
      const data = await deploymentApi.getDeploymentLogs(runId);
      setSelectedLogs(data);
    } catch (error) {
      logger.error('載入日誌失敗:', error);
      message.error('載入部署日誌失敗');
    } finally {
      setLogsLoading(false);
    }
  };

  // =============================================================================
  // 表格欄位
  // =============================================================================

  const historyColumns: ColumnsType<DeploymentRecord> = [
    {
      title: '#',
      dataIndex: 'run_number',
      key: 'run_number',
      width: 70,
      render: (num: number) => <Text strong>#{num}</Text>,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: DeploymentStatus, record) => (
        <DeploymentStatusTag status={status} conclusion={record.conclusion} />
      ),
    },
    {
      title: '分支',
      dataIndex: 'branch',
      key: 'branch',
      width: 120,
      render: (branch: string) => (
        <Tag icon={<BranchesOutlined />} color="blue">
          {branch}
        </Tag>
      ),
    },
    {
      title: 'Commit',
      dataIndex: 'commit_sha',
      key: 'commit_sha',
      width: 100,
      render: (sha: string) => (
        <Tooltip title={sha}>
          <code>{sha}</code>
        </Tooltip>
      ),
    },
    {
      title: '訊息',
      dataIndex: 'commit_message',
      key: 'commit_message',
      ellipsis: true,
      render: (msg: string) => (
        <Tooltip title={msg}>
          <Text ellipsis style={{ maxWidth: 200 }}>
            {msg || '-'}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '觸發者',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
      width: 120,
      render: (user: string) => (
        <Space>
          <UserOutlined />
          {user}
        </Space>
      ),
    },
    {
      title: '開始時間',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 160,
      render: (time: string) => (
        <Tooltip title={dayjs(time).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(time).fromNow()}
        </Tooltip>
      ),
    },
    {
      title: '耗時',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      width: 80,
      render: (seconds: number) =>
        seconds ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="查看日誌">
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => handleViewLogs(record.id)}
            />
          </Tooltip>
          <Tooltip title="在 GitHub 查看">
            <Button
              type="link"
              size="small"
              icon={<GithubOutlined />}
              href={record.url}
              target="_blank"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // =============================================================================
  // 渲染
  // =============================================================================

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 標題區 */}
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              <RocketOutlined /> 部署管理
            </Title>
            <Text type="secondary">系統部署狀態監控與操作</Text>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadSystemStatus} loading={loading}>
                刷新狀態
              </Button>
              <Button
                icon={<SettingOutlined />}
                onClick={() => setConfigModalVisible(true)}
              >
                配置
              </Button>
              <Popconfirm
                title="確認回滾"
                description="確定要回滾到上一個版本嗎？此操作將重啟服務。"
                onConfirm={handleRollback}
                okText="確認回滾"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button
                  icon={<RollbackOutlined />}
                  danger
                  loading={rollbackLoading}
                >
                  回滾
                </Button>
              </Popconfirm>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => setTriggerModalVisible(true)}
              >
                觸發部署
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 配置警告 */}
        {deployConfig && !deployConfig.github_token_configured && (
          <Alert
            type="warning"
            showIcon
            message="GitHub Token 未配置"
            description="部分功能（部署歷史、觸發部署）需要配置 GITHUB_TOKEN 環境變數才能使用。"
          />
        )}

        {/* 系統狀態卡片 */}
        <Card title={<><CloudServerOutlined /> 系統狀態</>} loading={loading}>
          <Row gutter={[24, 24]}>
            <Col xs={24} sm={12} md={6}>
              <Statistic
                title="整體狀態"
                valueRender={() => (
                  <ServiceStatusTag status={systemStatus?.overall_status || 'unknown'} />
                )}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Statistic
                title="當前版本"
                value={systemStatus?.current_version || '未知'}
                prefix={<BranchesOutlined />}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Statistic
                title="最後部署"
                value={
                  systemStatus?.last_deployment
                    ? dayjs(systemStatus.last_deployment).fromNow()
                    : '未知'
                }
                prefix={<ClockCircleOutlined />}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Statistic
                title="環境"
                value={systemStatus?.environment || 'production'}
                prefix={<DesktopOutlined />}
              />
            </Col>
          </Row>

          <Descriptions
            title="服務詳情"
            style={{ marginTop: 24 }}
            bordered
            size="small"
            column={{ xs: 1, sm: 2, md: 3 }}
          >
            {systemStatus?.services.map((service) => (
              <Descriptions.Item
                key={service.name}
                label={
                  <Space>
                    {service.name === 'Backend API' && <CloudServerOutlined />}
                    {service.name === 'Frontend' && <DesktopOutlined />}
                    {service.name === 'PostgreSQL' && <DatabaseOutlined />}
                    {service.name}
                  </Space>
                }
              >
                <Space>
                  <ServiceStatusTag status={service.status} />
                  {service.version && <Tag>{service.version}</Tag>}
                </Space>
              </Descriptions.Item>
            ))}
          </Descriptions>
        </Card>

        {/* 部署歷史 */}
        <Card
          title={
            <Space>
              <HistoryOutlined />
              部署歷史
              {deployHistory && (
                <Badge count={deployHistory.total} style={{ backgroundColor: '#1890ff' }} />
              )}
            </Space>
          }
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={loadDeployHistory}
              loading={historyLoading}
              size="small"
            >
              刷新
            </Button>
          }
        >
          <Table
            columns={historyColumns}
            dataSource={deployHistory?.records || []}
            rowKey="id"
            loading={historyLoading}
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: deployHistory?.total || 0,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 筆記錄`,
              onChange: (page, size) => {
                setCurrentPage(page);
                setPageSize(size);
              },
            }}
            scroll={{ x: 1000 }}
            size="small"
          />
        </Card>

        {/* 觸發部署 Modal */}
        <Modal
          title={
            <Space>
              <RocketOutlined />
              觸發部署
            </Space>
          }
          open={triggerModalVisible}
          onOk={handleTriggerDeploy}
          onCancel={() => setTriggerModalVisible(false)}
          confirmLoading={triggerLoading}
          okText="觸發部署"
          cancelText="取消"
        >
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>分支/標籤：</Text>
              <Select
                style={{ width: '100%', marginTop: 8 }}
                value={triggerRef}
                onChange={setTriggerRef}
                options={[
                  { value: 'main', label: 'main (主分支)' },
                  { value: 'develop', label: 'develop (開發分支)' },
                ]}
              />
            </div>

            <div>
              <Space>
                <Switch checked={forceRebuild} onChange={setForceRebuild} />
                <Text>強制重新建置 (不使用快取)</Text>
              </Space>
            </div>

            <div>
              <Space>
                <Switch checked={skipBackup} onChange={setSkipBackup} />
                <Text>跳過備份步驟</Text>
              </Space>
            </div>

            <Alert
              type="info"
              showIcon
              message="部署將自動執行以下步驟"
              description={
                <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                  <li>備份當前映像與資料庫</li>
                  <li>建置新版本 Docker 映像</li>
                  <li>啟動新服務</li>
                  <li>健康檢查 (後端 + 前端)</li>
                  <li>失敗時自動回滾</li>
                </ul>
              }
            />
          </Space>
        </Modal>

        {/* 日誌 Modal */}
        <Modal
          title={
            <Space>
              <FileTextOutlined />
              部署日誌
              {selectedLogs && <Tag>Run #{selectedLogs.run_id}</Tag>}
            </Space>
          }
          open={logsModalVisible}
          onCancel={() => {
            setLogsModalVisible(false);
            setSelectedLogs(null);
          }}
          footer={null}
          width={800}
        >
          <Spin spinning={logsLoading}>
            {selectedLogs && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Descriptions size="small" bordered>
                  <Descriptions.Item label="狀態">
                    <DeploymentStatusTag status={selectedLogs.status as DeploymentStatus} />
                  </Descriptions.Item>
                </Descriptions>

                <Collapse defaultActiveKey={selectedLogs.jobs.map((_, i) => i.toString())}>
                  {selectedLogs.jobs.map((job, index) => (
                    <Panel
                      key={index}
                      header={
                        <Space>
                          {job.status === 'success' ? (
                            <CheckCircleOutlined style={{ color: '#52c41a' }} />
                          ) : job.status === 'failure' ? (
                            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                          ) : (
                            <SyncOutlined spin />
                          )}
                          {job.job_name}
                        </Space>
                      }
                    >
                      <pre
                        style={{
                          background: '#f5f5f5',
                          padding: 12,
                          borderRadius: 4,
                          fontSize: 12,
                          maxHeight: 300,
                          overflow: 'auto',
                        }}
                      >
                        {job.logs}
                      </pre>
                    </Panel>
                  ))}
                </Collapse>
              </Space>
            )}
          </Spin>
        </Modal>

        {/* 配置 Modal */}
        <Modal
          title={
            <Space>
              <SettingOutlined />
              部署配置
            </Space>
          }
          open={configModalVisible}
          onCancel={() => setConfigModalVisible(false)}
          footer={null}
        >
          {deployConfig && (
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="GitHub Repository">
                <a
                  href={`https://github.com/${deployConfig.github_repo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <GithubOutlined /> {deployConfig.github_repo}
                </a>
              </Descriptions.Item>
              <Descriptions.Item label="Workflow 檔案">
                {deployConfig.workflow_file}
              </Descriptions.Item>
              <Descriptions.Item label="GitHub Token">
                {deployConfig.github_token_configured ? (
                  <Tag color="success">已配置</Tag>
                ) : (
                  <Tag color="error">未配置</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="部署路徑">
                <code>{deployConfig.deploy_path}</code>
              </Descriptions.Item>
              <Descriptions.Item label="環境">
                <Tag color="blue">{deployConfig.environment}</Tag>
              </Descriptions.Item>
            </Descriptions>
          )}
        </Modal>
      </Space>
    </div>
  );
};

export default DeploymentManagementPage;
