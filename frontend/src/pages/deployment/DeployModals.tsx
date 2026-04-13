import React from 'react';
import {
  Modal, Space, Typography, Select, Switch, Alert, Spin,
  Descriptions, Collapse, Tag,
} from 'antd';
import {
  RocketOutlined,
  FileTextOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  GithubOutlined,
} from '@ant-design/icons';
import type {
  DeploymentLogsResponse,
  DeploymentStatus,
} from '../../api/deploymentApi';
import { DeploymentStatusTag } from './StatusTags';

const { Text } = Typography;

interface TriggerModalProps {
  open: boolean;
  onOk: () => void;
  onCancel: () => void;
  loading: boolean;
  triggerRef: string;
  onTriggerRefChange: (ref: string) => void;
  forceRebuild: boolean;
  onForceRebuildChange: (val: boolean) => void;
  skipBackup: boolean;
  onSkipBackupChange: (val: boolean) => void;
}

export const TriggerDeployModal: React.FC<TriggerModalProps> = ({
  open,
  onOk,
  onCancel,
  loading,
  triggerRef,
  onTriggerRefChange,
  forceRebuild,
  onForceRebuildChange,
  skipBackup,
  onSkipBackupChange,
}) => {
  return (
    <Modal
      title={
        <Space>
          <RocketOutlined />
          觸發部署
        </Space>
      }
      open={open}
      onOk={onOk}
      onCancel={onCancel}
      confirmLoading={loading}
      okText="觸發部署"
      cancelText="取消"
    >
      <Space vertical style={{ width: '100%' }} size="middle">
        <div>
          <Text strong>分支/標籤：</Text>
          <Select
            style={{ width: '100%', marginTop: 8 }}
            value={triggerRef}
            onChange={onTriggerRefChange}
            options={[
              { value: 'main', label: 'main (主分支)' },
              { value: 'develop', label: 'develop (開發分支)' },
            ]}
          />
        </div>

        <div>
          <Space>
            <Switch checked={forceRebuild} onChange={onForceRebuildChange} />
            <Text>強制重新建置 (不使用快取)</Text>
          </Space>
        </div>

        <div>
          <Space>
            <Switch checked={skipBackup} onChange={onSkipBackupChange} />
            <Text>跳過備份步驟</Text>
          </Space>
        </div>

        <Alert
          type="info"
          showIcon
          title="部署將自動執行以下步驟"
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
  );
};

interface LogsModalProps {
  open: boolean;
  onCancel: () => void;
  loading: boolean;
  logs: DeploymentLogsResponse | null;
}

export const LogsModal: React.FC<LogsModalProps> = ({
  open,
  onCancel,
  loading,
  logs,
}) => {
  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          部署日誌
          {logs && <Tag>Run #{logs.run_id}</Tag>}
        </Space>
      }
      open={open}
      onCancel={onCancel}
      footer={null}
      width={800}
    >
      <Spin spinning={loading}>
        {logs && (
          <Space vertical style={{ width: '100%' }}>
            <Descriptions size="small" bordered items={[
              { key: '狀態', label: '狀態', children: (<DeploymentStatusTag status={logs.status as DeploymentStatus} />) },
            ]} />

            <Collapse
              defaultActiveKey={logs.jobs.map((_, i) => i.toString())}
              items={logs.jobs.map((job, index) => ({
                key: index.toString(),
                label: (
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
                ),
                children: (
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
                ),
              }))}
            />
          </Space>
        )}
      </Spin>
    </Modal>
  );
};

interface ConfigModalProps {
  open: boolean;
  onCancel: () => void;
  config: {
    github_repo: string;
    workflow_file: string;
    github_token_configured: boolean;
    deploy_path: string;
    environment: string;
  } | null;
}

export const ConfigModal: React.FC<ConfigModalProps> = ({
  open,
  onCancel,
  config,
}) => {
  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          部署配置
        </Space>
      }
      open={open}
      onCancel={onCancel}
      footer={null}
    >
      {config && (
        <Descriptions bordered column={1} size="small" items={[
          {
            key: 'GitHub Repository',
            label: 'GitHub Repository',
            children: (
              <a
                href={`https://github.com/${config.github_repo}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <GithubOutlined /> {config.github_repo}
              </a>
            ),
          },
          { key: 'Workflow 檔案', label: 'Workflow 檔案', children: config.workflow_file },
          {
            key: 'GitHub Token',
            label: 'GitHub Token',
            children: config.github_token_configured
              ? (<Tag color="success">已配置</Tag>)
              : (<Tag color="error">未配置</Tag>),
          },
          { key: '部署路徑', label: '部署路徑', children: (<code>{config.deploy_path}</code>) },
          { key: '環境', label: '環境', children: (<Tag color="blue">{config.environment}</Tag>) },
        ]} />
      )}
    </Modal>
  );
};
