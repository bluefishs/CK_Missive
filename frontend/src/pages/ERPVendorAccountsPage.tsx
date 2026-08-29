/**
 * ERP 協力廠商帳款總覽頁面
 *
 * 功能：列出所有協力廠商及其跨案件應付彙總
 * - 年度篩選 + 關鍵字搜尋
 * - 總應付 / 總已付 / 總未付 統計
 * - 點擊廠商列進入明細頁
 *
 * @version 1.0.0
 */
import React, { useState, useMemo } from 'react';
import {
  Alert, Card, Typography, Row, Col, Tag, Select, Space, Input,
} from 'antd';
import { DollarOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ClickableStatCard } from '../components/common';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { useVendorAccountSummary } from '../hooks';
import type { VendorAccountSummaryItem } from '../types/erp';
import type { ResponsiveColumn } from '../components/common/EnhancedTable';
import { EnhancedTable } from '../components/common/EnhancedTable';

const { Title } = Typography;

// 2026-08-27 owner：「篩選條件**統一為西元年**，且**預設當年度**呈現統計經費與總支出」。
//
// ⚠️ 原本這裡是 `new Date().getFullYear() - 1911`（**民國年**），
// 送出去的是 115，而後端比對的是 `erp_quotations.year`（**西元 2026**）
// ⇒ **選了年度永遠是空的，這個篩選從來沒有作用過**。
// 兩邊各自用自己的紀年，而沒有任何一方會報錯。
const currentYear = new Date().getFullYear();
const yearOptions = [
  // `0` = 全部年度（後端約定：None 走預設當年、0 才是不篩）
  { value: 0, label: '全部年度' },
  ...Array.from({ length: 5 }, (_, i) => ({
    value: currentYear - i,
    label: `${currentYear - i} 年`,
  })),
];

const ERPVendorAccountsPage: React.FC = () => {
  const navigate = useNavigate();
  // 預設當年度 —— 不給年度時所有年度會混在一起算成一個總數，
  // 而 owner 指出那正是「管理資訊不清晰」的來源
  // （實測 vendor_id=2：2025 已付 100 萬與 2026 未付 300 萬被加成一個數字）。
  const [year, setYear] = useState<number | undefined>(currentYear);
  const [keyword, setKeyword] = useState('');
  const [statFilter, setStatFilter] = useState<string | null>(null);

  const { data, isLoading, isError } = useVendorAccountSummary({
    vendor_type: 'subcontractor',
    year,
    keyword: keyword || undefined,
  });

  const items: VendorAccountSummaryItem[] = useMemo(
    () => data?.items ?? [],
    [data?.items],
  );

  // Top-level stats
  const stats = useMemo(() => {
    let totalPayable = 0;
    let totalPaid = 0;
    let totalOutstanding = 0;
    for (const item of items) {
      totalPayable += Number(item.total_payable ?? 0);
      totalPaid += Number(item.total_paid ?? 0);
      totalOutstanding += Number(item.outstanding ?? 0);
    }
    return { totalPayable, totalPaid, totalOutstanding };
  }, [items]);

  const filteredItems = useMemo(() => {
    if (!statFilter) return items;
    if (statFilter === 'paid') return items.filter(i => Number(i.total_paid ?? 0) > 0);
    if (statFilter === 'outstanding') return items.filter(i => Number(i.outstanding ?? 0) > 0);
    return items;
  }, [items, statFilter]);

  const columns: ResponsiveColumn<VendorAccountSummaryItem>[] = [
    {
      title: '廠商名稱',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      ellipsis: true,
    },
    {
      // 2026-08-27 owner：「廠商代碼請釐清，是否唯統一編號」。
      // 實測 65 家裡 15 家有值，**全部都是 8 碼純數字（統編格式）**、
      // 零非統編、零重複 ⇒ 它實務上就是統一編號，只是欄位名沒說。
      // ⇒ 標題直接寫明，避免與其他「代碼」混淆。
      title: '統一編號', hideOnMobile: true,
      dataIndex: 'vendor_code',
      key: 'vendor_code',
      width: 140,
    },
    {
      title: '合作案件數', hideOnMobile: true,
      dataIndex: 'case_count',
      key: 'case_count',
      width: 110,
      align: 'center',
      sorter: (a, b) => (a.case_count ?? 0) - (b.case_count ?? 0),
    },
    {
      title: '應付總額',
      dataIndex: 'total_payable',
      key: 'total_payable',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_payable ?? 0) - Number(b.total_payable ?? 0),
      render: (v: number) => Number(v).toLocaleString(),
    },
    {
      title: '已付總額', hideOnMobile: true,
      dataIndex: 'total_paid',
      key: 'total_paid',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_paid ?? 0) - Number(b.total_paid ?? 0),
      render: (v: number) => (
        <span style={{ color: '#52c41a' }}>{Number(v).toLocaleString()}</span>
      ),
    },
    {
      title: '未付餘額',
      dataIndex: 'outstanding',
      key: 'outstanding',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.outstanding ?? 0) - Number(b.outstanding ?? 0),
      render: (v: number) => {
        const num = Number(v);
        return (
          <Tag color={num > 0 ? 'red' : 'green'} style={{ margin: 0 }}>
            {num.toLocaleString()}
          </Tag>
        );
      },
    },
    {
      title: '付款率', hideOnMobile: true,
      key: 'payment_rate',
      width: 100,
      align: 'center',
      sorter: (a, b) => {
        const rateA = Number(a.total_payable) > 0 ? Number(a.total_paid) / Number(a.total_payable) * 100 : 0;
        const rateB = Number(b.total_payable) > 0 ? Number(b.total_paid) / Number(b.total_payable) * 100 : 0;
        return rateA - rateB;
      },
      render: (_: unknown, record: VendorAccountSummaryItem) => {
        const pct = Number(record.total_payable) > 0
          ? Number(record.total_paid) / Number(record.total_payable) * 100
          : 0;
        const color = pct >= 100 ? '#52c41a' : pct >= 50 ? '#faad14' : '#ff4d4f';
        return <span style={{ color, fontWeight: 600 }}>{pct.toFixed(1)}%</span>;
      },
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card
        title={<Title level={3} style={{ margin: 0 }}>協力廠商帳款總覽</Title>}
        extra={
          <Space>
            <Input.Search
              placeholder="搜尋廠商名稱 / 代碼"
              allowClear
              style={{ width: 220 }}
              onSearch={(v) => setKeyword(v.trim())}
            />
            <Select
              placeholder="年度"
              value={year}
              style={{ width: 130 }}
              options={yearOptions}
              onChange={(v) => setYear(v)}
            />
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <ClickableStatCard
              title="總應付"
              value={stats.totalPayable.toLocaleString()}
              icon={<DollarOutlined />}
              color="#1890ff"
              active={statFilter === 'all'}
              onClick={() => setStatFilter(statFilter === 'all' ? null : 'all')}
            />
          </Col>
          <Col xs={24} sm={8}>
            <ClickableStatCard
              title="總已付"
              value={stats.totalPaid.toLocaleString()}
              icon={<CheckCircleOutlined />}
              color="#3f8600"
              active={statFilter === 'paid'}
              onClick={() => setStatFilter(statFilter === 'paid' ? null : 'paid')}
            />
          </Col>
          <Col xs={24} sm={8}>
            <ClickableStatCard
              title="總未付"
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

      {/* 2026-08-27 owner：「統計圖卡互動篩選機制」＋「區分年度不能混淆」。
          卡片與年度同時作用時，列表會變少而**畫面說不出為什麼** ——
          使用者只看到「共 N 廠商」，不知道那是篩過的還是全部。 */}
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message={
          <span>
            目前顯示：<b>{year === 0 ? '全部年度' : `${year} 年度`}</b>
            {statFilter === 'paid' && <>｜僅<b>有已付款</b>的廠商</>}
            {statFilter === 'outstanding' && <>｜僅<b>有未付款</b>的廠商</>}
            {statFilter === 'all' && <>｜<b>全部</b>廠商</>}
            {keyword && <>｜關鍵字「{keyword}」</>}
            ｜共 <b>{filteredItems.length}</b> 家
          </span>
        }
        action={statFilter || keyword ? (
          <a onClick={() => { setStatFilter(null); setKeyword(''); }}>清除篩選</a>
        ) : undefined}
      />

      <Card>
        <EnhancedTable<VendorAccountSummaryItem>
          columns={columns}
          dataSource={filteredItems}
          // ⚠️ 不能用 `vendor_id` 當 key —— 廠商檔裡沒有的那些（實測「勤典工程行」
          // 4 筆）`vendor_id` 是 NULL ⇒ React key 重複，渲染會出錯。
          rowKey={(r) => (r.vendor_id != null ? `id:${r.vendor_id}` : `name:${r.vendor_name}`)}
          loading={isLoading}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 廠商` }}
          size="middle"
          scroll={{ x: 900 }}
          onRow={(record) => ({
            onClick: () => navigate(`${ROUTES.ERP_VENDOR_ACCOUNTS}/${record.vendor_id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPVendorAccountsPage;
