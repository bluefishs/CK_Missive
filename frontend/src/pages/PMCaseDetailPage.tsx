/**
 * PM 案件詳情頁面 — 與 contract-cases 共用模板
 *
 * 1. case_code 有對應 contract_project → 渲染完整共用模板（含 CRUD）
 * 2. 無對應 contract_project → 用 PM 資料渲染同樣版面（唯讀）
 *
 * @version 5.0.0
 */
import React, { Suspense, lazy } from 'react';
import {
  Button,
  Card,
  Spin,
  Result,
  Space,
  Tabs,
  Descriptions,
  Tag,
  Progress,
  Typography,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  InfoCircleOutlined,
  TeamOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { usePMCase, useCrossModuleLookup, useAuthGuard } from '../hooks';
import { projectsApi } from '../api/projectsApi';
import { PM_CASE_STATUS_LABELS, PM_CASE_STATUS_COLORS, PM_CATEGORY_LABELS } from '../types/api';
import type { PMCaseStatus } from '../types/api';
import { ROUTES } from '../router/types';

// Shared template (when contract_project exists)
import { ContractCaseDetailContent } from './ContractCaseDetailPage';

// PM-specific tabs (always available)
const MilestonesTab = lazy(() => import('./pmCase/MilestonesTab'));
const GanttTab = lazy(() => import('./pmCase/GanttTab'));
const PMStaffTab = lazy(() => import('./pmCase/StaffTab'));

export const PMCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const pmCaseId = id ? parseInt(id, 10) : null;

  const { data: pmCase, isLoading: pmLoading } = usePMCase(pmCaseId);

  // Find matching contract_project by case_code = project_code
  const { data: matchedProject, isLoading: matchLoading } = useQuery({
    queryKey: ['contract-project-by-code', pmCase?.case_code],
    queryFn: async () => {
      const result = await projectsApi.getProjects({ search: pmCase!.case_code, limit: 5 });
      return result.items?.find(p => p.project_code === pmCase!.case_code) ?? null;
    },
    enabled: !!pmCase?.case_code,
  });

  // ERP cross-module
  const { data: crossData } = useCrossModuleLookup(pmCase?.case_code ?? null);
  const erpLink = crossData?.erp;

  if (pmLoading || matchLoading) {
    return (
      <ResponsiveContent>
        <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
      </ResponsiveContent>
    );
  }

  if (!pmCase) {
    return (
      <ResponsiveContent>
        <Result status="404" title="案件不存在"
          extra={<Button onClick={() => navigate(ROUTES.PM_CASES)}>返回列表</Button>}
        />
      </ResponsiveContent>
    );
  }

  // ── Route A: Has matching contract_project → full shared template ──
  if (matchedProject?.id) {
    return (
      <ContractCaseDetailContent
        projectId={matchedProject.id}
        backRoute={ROUTES.PM_CASES}
      />
    );
  }

  // ── Route B: No contract_project → PM-only view with same layout ──
  const statusColor = PM_CASE_STATUS_COLORS[pmCase.status as PMCaseStatus] ?? 'default';
  const statusLabel = PM_CASE_STATUS_LABELS[pmCase.status as PMCaseStatus] ?? pmCase.status;

  const tabItems = [
    {
      key: 'info',
      label: <span><InfoCircleOutlined /> 案件資訊</span>,
      children: (
        <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="案號">{pmCase.case_code}</Descriptions.Item>
          <Descriptions.Item label="案名">{pmCase.case_name}</Descriptions.Item>
          <Descriptions.Item label="年度">{pmCase.year ? `${pmCase.year} 年` : '-'}</Descriptions.Item>
          <Descriptions.Item label="類別">{pmCase.category ? (PM_CATEGORY_LABELS[pmCase.category] ?? pmCase.category) : '-'}</Descriptions.Item>
          <Descriptions.Item label="委託單位">{pmCase.client_name ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="合約金額">{pmCase.contract_amount ? `NT$${pmCase.contract_amount.toLocaleString()}` : '-'}</Descriptions.Item>
          <Descriptions.Item label="狀態"><Tag color={statusColor}>{statusLabel}</Tag></Descriptions.Item>
          <Descriptions.Item label="進度"><Progress percent={pmCase.progress} size="small" style={{ width: 150 }} /></Descriptions.Item>
          <Descriptions.Item label="開始日期">{pmCase.start_date ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="結束日期">{pmCase.end_date ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="地點" span={2}>{pmCase.location ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="說明" span={2}>{pmCase.description ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="備註" span={2}>{pmCase.notes ?? '-'}</Descriptions.Item>
        </Descriptions>
      ),
    },
    {
      key: 'staff',
      label: <span><TeamOutlined /> 承辦同仁</span>,
      children: (
        <Suspense fallback={<Spin />}>
          <PMStaffTab pmCaseId={pmCase.id} />
        </Suspense>
      ),
    },
    {
      key: 'milestones',
      label: '里程碑',
      children: (
        <Suspense fallback={<Spin />}>
          <MilestonesTab pmCaseId={pmCase.id} />
        </Suspense>
      ),
    },
    {
      key: 'gantt',
      label: '甘特圖',
      children: (
        <Suspense fallback={<Spin />}>
          <GanttTab pmCaseId={pmCase.id} />
        </Suspense>
      ),
    },
    {
      key: 'erp',
      label: <span><DollarOutlined /> ERP 財務</span>,
      children: erpLink ? (
        <Card size="small" title="關聯報價"
          extra={<Button size="small" onClick={() => navigate(`/erp/quotations/${erpLink.id}`)}>查看詳情</Button>}
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}><Statistic title="總價" value={Number(erpLink.total_price) || 0} prefix="NT$" /></Col>
            <Col xs={12} sm={6}><Statistic title="毛利" value={Number(erpLink.gross_profit) || 0} prefix="NT$" /></Col>
            <Col xs={12} sm={6}><Statistic title="狀態" value={erpLink.status === 'confirmed' ? '已確認' : erpLink.status === 'draft' ? '草稿' : '已結案'} /></Col>
            <Col xs={12} sm={6}><Statistic title="案件名稱" value={erpLink.case_name} /></Col>
          </Row>
        </Card>
      ) : (
        <Result status="info" title="尚無 ERP 關聯" subTitle={`案號 ${pmCase.case_code} 在 ERP 模組中沒有對應的報價記錄`} />
      ),
    },
  ];

  return (
    <ResponsiveContent>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.PM_CASES)}>返回</Button>
              <Typography.Title level={4} style={{ margin: 0 }}>{pmCase.case_name}</Typography.Title>
              <Tag color={statusColor}>{statusLabel}</Tag>
            </Space>
          </Col>
          <Col>
            {hasPermission('projects:write') && (
              <Button type="primary" icon={<EditOutlined />}
                onClick={() => navigate(ROUTES.PM_CASE_EDIT.replace(':id', String(pmCase.id)))}
              >編輯</Button>
            )}
          </Col>
        </Row>
        <Card>
          <Tabs items={tabItems} size="large" />
        </Card>
      </Space>
    </ResponsiveContent>
  );
};

export default PMCaseDetailPage;
