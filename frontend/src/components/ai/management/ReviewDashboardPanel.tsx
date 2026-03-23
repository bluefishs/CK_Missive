/**
 * ReviewDashboardPanel - 系統覆盤儀表板
 *
 * 彙總 6 子系統狀態: Knowledge Graph / Code Graph / DB Graph /
 * Knowledge Base / Skill Evolution / 排程器
 *
 * @version 1.0.0
 * @created 2026-03-23
 */
import React from 'react';
import {
  Card,
  Row,
  Col,
  Tag,
  Typography,
  Descriptions,
  Button,
  Spin,
  Alert,
  Space,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  DeploymentUnitOutlined,
  CodeOutlined,
  DatabaseOutlined,
  BookOutlined,
  ThunderboltOutlined,
  ScheduleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../api/client';
import { SYSTEM_ENDPOINTS } from '../../../api/endpoints';

const { Text, Title } = Typography;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SubsystemStatus {
  status: 'healthy' | 'degraded' | 'pending' | 'active' | 'empty' | 'error';
  error?: string;
  [key: string]: unknown;
}

interface SchedulerJob {
  id: string;
  name: string;
  next_run_time: string | null;
  trigger: string;
}

interface ReviewDashboardData {
  timestamp: string;
  subsystems: Record<string, SubsystemStatus>;
  scheduler: {
    running: boolean;
    jobs: SchedulerJob[];
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<
  string,
  { color: string; icon: React.ReactNode }
> = {
  healthy: { color: 'success', icon: <CheckCircleOutlined /> },
  active: { color: 'processing', icon: <ThunderboltOutlined /> },
  pending: { color: 'warning', icon: <ClockCircleOutlined /> },
  degraded: { color: 'warning', icon: <WarningOutlined /> },
  empty: { color: 'default', icon: <ClockCircleOutlined /> },
  error: { color: 'error', icon: <CloseCircleOutlined /> },
};

const SUBSYSTEM_META: Record<string, { label: string; icon: React.ReactNode }> =
  {
    knowledge_graph: { label: '知識圖譜', icon: <DeploymentUnitOutlined /> },
    code_graph: { label: 'Code Graph', icon: <CodeOutlined /> },
    db_graph: { label: 'DB Graph', icon: <DatabaseOutlined /> },
    knowledge_base: { label: '知識庫 (KB)', icon: <BookOutlined /> },
    skill_evolution: { label: '技能演化', icon: <ThunderboltOutlined /> },
  };

function renderStatusTag(status: string) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG['error'];
  return (
    <Tag color={cfg!.color} icon={cfg!.icon}>
      {status.toUpperCase()}
    </Tag>
  );
}

// ---------------------------------------------------------------------------
// SubsystemCard
// ---------------------------------------------------------------------------

const SubsystemCard: React.FC<{
  name: string;
  data: SubsystemStatus;
}> = ({ name, data }) => {
  const meta = SUBSYSTEM_META[name] || { label: name, icon: <DatabaseOutlined /> };
  const { status, error, ...rest } = data;

  // Build description items from remaining fields
  const items = Object.entries(rest).map(([key, value]) => ({
    key,
    label: key,
    children: String(value),
  }));

  return (
    <Card
      size="small"
      title={
        <Space>
          {meta.icon}
          <Text strong>{meta.label}</Text>
          {renderStatusTag(status)}
        </Space>
      }
      style={{ height: '100%' }}
    >
      {error ? (
        <Alert type="error" description={error} showIcon style={{ marginBottom: 8 }} />
      ) : null}
      {items.length > 0 && (
        <Descriptions size="small" column={1} bordered>
          {items.map((item) => (
            <Descriptions.Item key={item.key} label={item.label}>
              {item.children}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
    </Card>
  );
};

// ---------------------------------------------------------------------------
// SchedulerPanel
// ---------------------------------------------------------------------------

const SchedulerPanel: React.FC<{
  scheduler: ReviewDashboardData['scheduler'];
}> = ({ scheduler }) => (
  <Card
    size="small"
    title={
      <Space>
        <ScheduleOutlined />
        <Text strong>排程器</Text>
        <Tag color={scheduler.running ? 'success' : 'error'}>
          {scheduler.running ? 'RUNNING' : 'STOPPED'}
        </Tag>
      </Space>
    }
  >
    <Descriptions size="small" column={1} bordered>
      {scheduler.jobs.map((job) => (
        <Descriptions.Item key={job.id} label={job.name}>
          <Tooltip title={`Trigger: ${job.trigger}`}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {job.next_run_time
                ? new Date(job.next_run_time).toLocaleString('zh-TW')
                : '未排程'}
            </Text>
          </Tooltip>
        </Descriptions.Item>
      ))}
    </Descriptions>
  </Card>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const ReviewDashboardPanel: React.FC = () => {
  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery<ReviewDashboardData>({
    queryKey: ['system', 'review-dashboard'],
    queryFn: () =>
      apiClient.post<ReviewDashboardData>(SYSTEM_ENDPOINTS.REVIEW_DASHBOARD),
    staleTime: 5 * 60 * 1000, // 5 min
    retry: 1,
  });

  if (isLoading) return <Spin>{/* 載入覆盤資料 */}</Spin>;

  if (error) {
    return (
      <Alert
        type="error"
        description={`無法載入覆盤儀表板: ${String(error)}`}
        showIcon
      />
    );
  }

  if (!data) return null;

  const subsystemEntries = Object.entries(data.subsystems);

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Title level={5} style={{ margin: 0 }}>
          <DeploymentUnitOutlined /> 系統覆盤儀表板
        </Title>
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {new Date(data.timestamp).toLocaleString('zh-TW')}
          </Text>
          <Button
            size="small"
            icon={<ReloadOutlined spin={isFetching} />}
            onClick={() => refetch()}
            loading={isFetching}
          >
            重新整理
          </Button>
        </Space>
      </div>

      <Row gutter={[12, 12]}>
        {subsystemEntries.map(([name, status]) => (
          <Col xs={24} sm={12} lg={8} key={name}>
            <SubsystemCard name={name} data={status} />
          </Col>
        ))}
      </Row>

      <div style={{ marginTop: 16 }}>
        <SchedulerPanel scheduler={data.scheduler} />
      </div>
    </div>
  );
};
