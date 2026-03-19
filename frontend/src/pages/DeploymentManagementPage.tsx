import React, { useState } from 'react';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Row, Col, Typography, Space, Button, Alert, Popconfirm, message,
} from 'antd';
import {
  RocketOutlined,
  RollbackOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-tw';

import deploymentApi, {
  type TriggerDeploymentResponse,
  type RollbackResponse,
  type DeploymentLogsResponse,
} from '../api/deploymentApi';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { logger } from '../utils/logger';

import {
  SystemStatusCard,
  DeployHistoryCard,
  TriggerDeployModal,
  LogsModal,
  ConfigModal,
} from './deployment';

dayjs.extend(relativeTime);
dayjs.locale('zh-tw');

const { Title, Text } = Typography;

const DeploymentManagementPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [selectedLogs, setSelectedLogs] = useState<DeploymentLogsResponse | null>(null);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);

  const [triggerModalVisible, setTriggerModalVisible] = useState(false);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [configModalVisible, setConfigModalVisible] = useState(false);

  const [triggerRef, setTriggerRef] = useState('main');
  const [forceRebuild, setForceRebuild] = useState(false);
  const [skipBackup, setSkipBackup] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const { data: systemStatus = null, isLoading: loading } = useQuery({
    queryKey: ['deployment-system-status'],
    queryFn: () => deploymentApi.getSystemStatus(),
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });

  const { data: deployHistory = null, isLoading: historyLoading } = useQuery({
    queryKey: ['deployment-history', currentPage, pageSize],
    queryFn: () => deploymentApi.getDeploymentHistory({ page: currentPage, page_size: pageSize }),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const { data: deployConfig = null } = useQuery({
    queryKey: ['deployment-config'],
    queryFn: () => deploymentApi.getDeploymentConfig(),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const loadSystemStatus = () => queryClient.invalidateQueries({ queryKey: ['deployment-system-status'] });
  const loadDeployHistory = () => queryClient.invalidateQueries({ queryKey: ['deployment-history'] });

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

  const handlePageChange = (page: number, size: number) => {
    setCurrentPage(page);
    setPageSize(size);
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space vertical size="large" style={{ width: '100%' }}>
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

        {deployConfig && !deployConfig.github_token_configured && (
          <Alert
            type="warning"
            showIcon
            title="GitHub Token 未配置"
            description="部分功能（部署歷史、觸發部署）需要配置 GITHUB_TOKEN 環境變數才能使用。"
          />
        )}

        <SystemStatusCard systemStatus={systemStatus} loading={loading} />

        <DeployHistoryCard
          deployHistory={deployHistory}
          historyLoading={historyLoading}
          currentPage={currentPage}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onRefresh={loadDeployHistory}
          onViewLogs={handleViewLogs}
        />

        <TriggerDeployModal
          visible={triggerModalVisible}
          onOk={handleTriggerDeploy}
          onCancel={() => setTriggerModalVisible(false)}
          loading={triggerLoading}
          triggerRef={triggerRef}
          onTriggerRefChange={setTriggerRef}
          forceRebuild={forceRebuild}
          onForceRebuildChange={setForceRebuild}
          skipBackup={skipBackup}
          onSkipBackupChange={setSkipBackup}
        />

        <LogsModal
          visible={logsModalVisible}
          onCancel={() => {
            setLogsModalVisible(false);
            setSelectedLogs(null);
          }}
          loading={logsLoading}
          logs={selectedLogs}
        />

        <ConfigModal
          visible={configModalVisible}
          onCancel={() => setConfigModalVisible(false)}
          config={deployConfig}
        />
      </Space>
    </ResponsiveContent>
  );
};

export default DeploymentManagementPage;
