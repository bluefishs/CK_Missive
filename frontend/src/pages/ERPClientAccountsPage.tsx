/**
 * ERP 委託單位帳款總覽頁面
 *
 * 功能：列出所有委託單位及其跨案件應收彙總
 * - 年度篩選 + 關鍵字搜尋
 * - 合約總額 / 已請款 / 已收款 / 未收款 統計
 * - 點擊委託單位列進入明細頁
 *
 * @version 1.0.0
 */
import React, { useState, useMemo } from 'react';
import {
  Alert, Card, Typography, Row, Col, Tag, Select, Space, Input,
} from 'antd';
import {
  DollarOutlined, CheckCircleOutlined, ExclamationCircleOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { ClickableStatCard } from '../components/common';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { useClientAccountSummary } from '../hooks';
import type { ClientAccountSummaryItem } from '../types/erp';
import { EnhancedTable } from '../components/common/EnhancedTable';
import type { ResponsiveColumn } from '../components/common/EnhancedTable';

const { Title } = Typography;

// 2026-08-27 owner：「`/erp/client-accounts` **相同架構問題**」。
//
// ⚠️ 與應付端完全一樣的 bug：這裡原本是 `getFullYear() - 1911`（**民國年**），
// 送出去的是 115，而後端比對的是 `pm_cases.year`（**西元 2026**）
// ⇒ **選了年度永遠是空的，這個篩選從來沒有作用過**。
// 兩邊各自用自己的紀年，而沒有任何一方會報錯 —— 同一個缺陷在兩頁各有一份。
const currentYear = new Date().getFullYear();
const yearOptions = Array.from({ length: 5 }, (_, i) => ({
  value: currentYear - i,
  label: `${currentYear - i} 年`,
}));

const ERPClientAccountsPage: React.FC = () => {
  const navigate = useNavigate();
  // 預設當年度 —— 不篩年度時所有年度會混在一起算成一個總數
  const [year, setYear] = useState<number | undefined>(currentYear);
  const [keyword, setKeyword] = useState('');
  const [statFilter, setStatFilter] = useState<string | null>(null);

  const { data, isLoading, isError } = useClientAccountSummary({
    vendor_type: 'client',
    year,
    keyword: keyword || undefined,
  });

  const items: ClientAccountSummaryItem[] = useMemo(
    () => data?.items ?? [],
    [data?.items],
  );

  // Top-level stats
  const stats = useMemo(() => {
    let totalContract = 0;
    let totalBilled = 0;
    let totalReceived = 0;
    let totalOutstanding = 0;
    for (const item of items) {
      totalContract += Number(item.total_contract ?? 0);
      totalBilled += Number(item.total_billed ?? 0);
      totalReceived += Number(item.total_received ?? 0);
      totalOutstanding += Number(item.outstanding ?? 0);
    }
    return { totalContract, totalBilled, totalReceived, totalOutstanding };
  }, [items]);

  const filteredItems = useMemo(() => {
    if (!statFilter) return items;
    if (statFilter === 'billed') return items.filter(i => Number(i.total_billed ?? 0) > 0);
    if (statFilter === 'received') return items.filter(i => Number(i.total_received ?? 0) > 0);
    if (statFilter === 'outstanding') return items.filter(i => Number(i.outstanding ?? 0) > 0);
    return items;
  }, [items, statFilter]);

  const columns: ResponsiveColumn<ClientAccountSummaryItem>[] = [
    {
      title: '委託單位',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      ellipsis: true,
    },
    {
      title: '代碼',
      hideOnMobile: true, dataIndex: 'vendor_code',
      key: 'vendor_code',
      width: 140,
    },
    {
      title: '合作案件數',
      hideOnMobile: true, dataIndex: 'case_count',
      key: 'case_count',
      width: 110,
      align: 'center',
      sorter: (a, b) => (a.case_count ?? 0) - (b.case_count ?? 0),
    },
    {
      title: '合約總額',
      dataIndex: 'total_contract',
      key: 'total_contract',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_contract ?? 0) - Number(b.total_contract ?? 0),
      render: (v: number) => Number(v).toLocaleString(),
    },
    {
      title: '已請款',
      hideOnMobile: true, dataIndex: 'total_billed',
      key: 'total_billed',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_billed ?? 0) - Number(b.total_billed ?? 0),
      render: (v: number) => Number(v).toLocaleString(),
    },
    {
      title: '已收款',
      hideOnMobile: true, dataIndex: 'total_received',
      key: 'total_received',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_received ?? 0) - Number(b.total_received ?? 0),
      render: (v: number) => (
        <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span>
      ),
    },
    {
      title: '未收餘額',
      dataIndex: 'outstanding',
      key: 'outstanding',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.outstanding ?? 0) - Number(b.outstanding ?? 0),
      render: (v: number) => {
        const num = Number(v);
        return (
          <Tag color={num > 0 ? 'orange' : 'green'} style={{ margin: 0 }}>
            {num.toLocaleString()}
          </Tag>
        );
      },
    },
    {
      title: '收款率',
      key: 'collection_rate',
      width: 100,
      align: 'right' as const,
      sorter: (a, b) => {
        const rateA = Number(a.total_billed) > 0 ? Number(a.total_received) / Number(a.total_billed) * 100 : 0;
        const rateB = Number(b.total_billed) > 0 ? Number(b.total_received) / Number(b.total_billed) * 100 : 0;
        return rateA - rateB;
      },
      render: (_: unknown, record: ClientAccountSummaryItem) => {
        const rate = Number(record.total_billed) > 0
          ? (Number(record.total_received) / Number(record.total_billed) * 100)
          : 0;
        const color = rate >= 100 ? '#52c41a' : rate >= 50 ? '#faad14' : '#ff4d4f';
        return <span style={{ color, fontWeight: 600 }}>{rate.toFixed(1)}%</span>;
      },
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card
        title={<Title level={3} style={{ margin: 0 }}>委託單位帳款總覽</Title>}
        extra={
          <Space>
            <Input.Search
              placeholder="搜尋單位名稱 / 代碼"
              allowClear
              style={{ width: 220 }}
              onSearch={(v) => setKeyword(v.trim())}
            />
            <Select
              placeholder="年度"
              style={{ width: 120 }}
              value={year}
              options={[{ value: 0, label: '全部年度' }, ...yearOptions]}
              onChange={(v) => setYear(v)}
            />
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={6}>
            <ClickableStatCard
              title="合約總額"
              value={stats.totalContract.toLocaleString()}
              icon={<FileTextOutlined />}
              color="#1890ff"
              active={statFilter === 'all'}
              onClick={() => setStatFilter(statFilter === 'all' ? null : 'all')}
            />
          </Col>
          <Col xs={24} sm={6}>
            <ClickableStatCard
              title="已請款"
              value={stats.totalBilled.toLocaleString()}
              icon={<DollarOutlined />}
              color="#faad14"
              active={statFilter === 'billed'}
              onClick={() => setStatFilter(statFilter === 'billed' ? null : 'billed')}
            />
          </Col>
          <Col xs={24} sm={6}>
            <ClickableStatCard
              title="已收款"
              value={stats.totalReceived.toLocaleString()}
              icon={<CheckCircleOutlined />}
              color="#3f8600"
              active={statFilter === 'received'}
              onClick={() => setStatFilter(statFilter === 'received' ? null : 'received')}
            />
          </Col>
          <Col xs={24} sm={6}>
            <ClickableStatCard
              title="未收款"
              value={stats.totalOutstanding.toLocaleString()}
              icon={<ExclamationCircleOutlined />}
              color={stats.totalOutstanding > 0 ? '#cf1322' : '#3f8600'}
              active={statFilter === 'outstanding'}
              onClick={() => setStatFilter(statFilter === 'outstanding' ? null : 'outstanding')}
            />
          </Col>
        </Row>
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <EnhancedTable<ClientAccountSummaryItem>
          columns={columns}
          dataSource={filteredItems}
          rowKey={(r) => r.vendor_id != null ? String(r.vendor_id) : `name:${r.vendor_name}`}
          loading={isLoading}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 單位` }}
          size="middle"
          scroll={{ x: 960 }}
          onRow={(record) => ({
            // 2026-08-28：客戶只存在於承攬案件文字欄（尚無 partner_vendor 主檔）時
            // vendor_id 為 null —— 沒有明細頁可去，點了導到 /null 只會 404
            onClick: record.vendor_id != null
              ? () => navigate(`${ROUTES.ERP_CLIENT_ACCOUNTS}/${record.vendor_id}`)
              : undefined,
            style: record.vendor_id != null ? { cursor: 'pointer' } : undefined,
          })}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPClientAccountsPage;
