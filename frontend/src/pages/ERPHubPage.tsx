import React from 'react';
import { Card, Row, Col, Typography, Space } from 'antd';
import {
  DollarOutlined,
  FileTextOutlined,
  BookOutlined,
  DashboardOutlined,
  AuditOutlined,
  CloudSyncOutlined,
  TeamOutlined,
  BankOutlined,
  ToolOutlined,
  AccountBookOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { ROUTES } from '../router/types';
import { useERPOverview } from '../hooks/business/useERPFinance';

interface ERPModule {
  key: string;
  title: string;
  desc: string;
  icon: React.ReactNode;
  path: string;
  color: string;
  statsKey?: string;
  amountKey?: string;
  amountLabel?: string;
}

// 主要模組 (5 大入口)
const mainModules: ERPModule[] = [
  {
    key: 'expenses',
    title: '費用核銷',
    desc: '發票掃描、核銷審核、收支帳本',
    icon: <FileTextOutlined />,
    path: ROUTES.ERP_EXPENSES,
    color: '#52c41a',
    statsKey: 'expenses',
    amountKey: 'expense_amount',
    amountLabel: '核銷總額',
  },
  {
    key: 'quotations',
    title: '專案財務',
    desc: '報價管理、請款開票、帳款追蹤',
    icon: <DollarOutlined />,
    path: ROUTES.ERP_QUOTATIONS,
    color: '#1890ff',
    statsKey: 'quotations',
    amountKey: 'quotation_amount',
    amountLabel: '合約總額',
  },
  {
    key: 'operational',
    title: '營運財務',
    desc: '營運帳目、預算管控、審批',
    icon: <AccountBookOutlined />,
    path: ROUTES.ERP_OPERATIONAL,
    color: '#722ed1',
    statsKey: 'operational',
  },
  {
    key: 'assets',
    title: '資產管理',
    desc: '設備儀器、盤點、折舊',
    icon: <ToolOutlined />,
    path: ROUTES.ERP_ASSETS,
    color: '#a0d911',
    statsKey: 'assets',
    amountKey: 'asset_value',
    amountLabel: '資產總值',
  },
  {
    key: 'dashboard',
    title: '財務總覽',
    desc: '全公司損益、趨勢、預算',
    icon: <DashboardOutlined />,
    path: ROUTES.ERP_FINANCIAL_DASHBOARD,
    color: '#fa8c16',
  },
];

// 進階功能
const advancedModules: ERPModule[] = [
  {
    key: 'vendor-accounts',
    title: '廠商帳款',
    desc: '跨案件應付彙總',
    icon: <TeamOutlined />,
    path: ROUTES.ERP_VENDOR_ACCOUNTS,
    color: '#eb2f96',
    statsKey: 'vendor_payables',
  },
  {
    key: 'client-accounts',
    title: '委託帳款',
    desc: '跨案件應收彙總',
    icon: <BankOutlined />,
    path: ROUTES.ERP_CLIENT_ACCOUNTS,
    color: '#faad14',
    statsKey: 'billings',
  },
  {
    key: 'invoices',
    title: '發票總覽',
    desc: '銷項/進項跨案件',
    icon: <AuditOutlined />,
    path: ROUTES.ERP_INVOICE_SUMMARY,
    color: '#13c2c2',
    statsKey: 'invoices',
  },
  {
    key: 'einvoice',
    title: '電子發票',
    desc: 'MOF 同步',
    icon: <CloudSyncOutlined />,
    path: ROUTES.ERP_EINVOICE_SYNC,
    color: '#2f54eb',
  },
  {
    key: 'ledger',
    title: '收支帳本',
    desc: '全域流水帳',
    icon: <BookOutlined />,
    path: ROUTES.ERP_LEDGER,
    color: '#8c8c8c',
    statsKey: 'ledger',
  },
];

const ERPHubPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: overview } = useERPOverview();

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space orientation="vertical" size="large" style={{ width: '100%' }}>
        <Typography.Title level={2} style={{ marginBottom: 0 }}>
          財務管理中心
        </Typography.Title>
        <Typography.Text type="secondary">
          ERP 財務模組總覽 — 點選卡片進入各子模組
        </Typography.Text>

        <Row gutter={[16, 16]}>
          {mainModules.map((m) => (
            <Col key={m.key} xs={24} sm={12} md={8}>
              <Card
                hoverable
                onClick={() => navigate(m.path)}
                style={{ borderTop: `3px solid ${m.color}`, height: '100%' }}
              >
                <Card.Meta
                  avatar={<span style={{ fontSize: 32, color: m.color }}>{m.icon}</span>}
                  title={m.title}
                  description={m.desc}
                />
                {m.statsKey && overview?.[m.statsKey] != null && (
                  <div style={{ marginTop: 12, color: '#999', fontSize: 13 }}>
                    {overview[m.statsKey]!.toLocaleString()} 筆記錄
                    {m.amountKey && overview?.[m.amountKey] != null && Number(overview[m.amountKey]) > 0 && (
                      <div style={{ marginTop: 4, color: m.color, fontWeight: 500 }}>
                        {m.amountLabel}: NT$ {Number(overview[m.amountKey]).toLocaleString()}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            </Col>
          ))}
        </Row>

        <Typography.Title level={4} style={{ marginTop: 24 }}>進階功能</Typography.Title>
        <Row gutter={[16, 16]}>
          {advancedModules.map((m) => (
            <Col key={m.key} xs={12} sm={8} md={6}>
              <Card
                hoverable size="small"
                onClick={() => navigate(m.path)}
                style={{ borderLeft: `3px solid ${m.color}` }}
              >
                <Card.Meta
                  avatar={<span style={{ fontSize: 20, color: m.color }}>{m.icon}</span>}
                  title={<span style={{ fontSize: 14 }}>{m.title}</span>}
                  description={<span style={{ fontSize: 12 }}>{m.desc}</span>}
                />
              </Card>
            </Col>
          ))}
        </Row>
      </Space>
    </ResponsiveContent>
  );
};

export default ERPHubPage;
