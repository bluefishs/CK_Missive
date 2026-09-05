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
import { MobileCard } from '../components/common/MobileCardList';
import { fmtMoney } from '../utils/money';
import { termTitle } from '../constants/financeTerms';
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
    // 2026-09-04：後端預設 50 而委託單位 186 家 ⇒ 此前頁面只列 50 家、其餘查不到（表格分頁與排序都在這 50 筆上做）
    limit: 1000,
  });

  const items: ClientAccountSummaryItem[] = useMemo(
    () => data?.items ?? [],
    [data?.items],
  );

  // Top-level stats
  const stats = useMemo(() => {
    // 2026-08-29：優先用後端「分頁前」的全體合計 —— 前端只加總取回的
    // 那一頁，資料超過 limit 時統計卡會**靜默少算而不報錯**（CK_Website
    // 指出的計時炸彈，現況 25 列沒炸只是還沒到 50）。
    const t = data?.totals;
    if (t) {
      return {
        totalContract: Number(t.total_contract ?? 0),
        totalBilled: Number(t.total_billed ?? 0),
        totalReceived: Number(t.total_received ?? 0),
        totalOutstanding: Number(t.outstanding ?? 0),
      };
    }
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
  }, [items, data?.totals]);

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
      title: '統一編號',
      hideOnMobile: true, dataIndex: 'tax_id',
      key: 'tax_id',
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
      title: termTitle('contract_amount_sum'),
      dataIndex: 'total_contract',
      key: 'total_contract',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_contract ?? 0) - Number(b.total_contract ?? 0),
      render: (v: number) => Number(v).toLocaleString(),
    },
    {
      title: termTitle('billed'),
      hideOnMobile: true, dataIndex: 'total_billed',
      key: 'total_billed',
      width: 130,
      align: 'right',
      sorter: (a, b) => Number(a.total_billed ?? 0) - Number(b.total_billed ?? 0),
      render: (v: number) => Number(v).toLocaleString(),
    },
    {
      title: termTitle('received'),
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
      title: termTitle('outstanding', '未收餘額'),
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
      title: termTitle('receipt_rate'),
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
          <Space wrap>  {/* 2026-09-05 RWD：390px 探針量到 7–17px 溢出，來源是這排不換行 */}
            <Input.Search
              placeholder="搜尋單位名稱／統一編號"
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
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title={termTitle('contract_amount_sum')}
              value={stats.totalContract.toLocaleString()}
              icon={<FileTextOutlined />}
              color="#1890ff"
              active={statFilter === 'all'}
              onClick={() => setStatFilter(statFilter === 'all' ? null : 'all')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title={termTitle('billed')}
              value={stats.totalBilled.toLocaleString()}
              icon={<DollarOutlined />}
              color="#faad14"
              active={statFilter === 'billed'}
              onClick={() => setStatFilter(statFilter === 'billed' ? null : 'billed')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title={termTitle('received')}
              value={stats.totalReceived.toLocaleString()}
              icon={<CheckCircleOutlined />}
              color="#3f8600"
              active={statFilter === 'received'}
              onClick={() => setStatFilter(statFilter === 'received' ? null : 'received')}
            />
          </Col>
          <Col xs={12} sm={6}>
            <ClickableStatCard
              title={termTitle('outstanding')}
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

      {data && data.total > items.length && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message={`列表只取到 ${items.length}／${data.total} 筆——超過單次上限，請用關鍵字縮小範圍`} />
      )}
      <Card>
        <EnhancedTable<ClientAccountSummaryItem>
          columns={columns}
          // 2026-09-05 RWD：手機改卡片
          mobileCard={(r) => {
            const billed = Number(r.total_billed ?? 0); const received = Number(r.total_received ?? 0);
            return (
              <MobileCard
                title={r.tax_id ? `統編 ${r.tax_id}` : '—'}
                subtitle={r.vendor_name}
                tags={[{ text: `${r.case_count ?? 0} 案`, color: 'blue' }]}
                amounts={[
                  { label: '承攬金額', value: fmtMoney(r.total_contract) },
                  { label: '已請款', value: fmtMoney(billed) },
                  { label: '未收', value: fmtMoney(billed - received), tone: billed - received > 0 ? 'warn' : 'good' },
                ]}
                onClick={r.vendor_id != null ? () => navigate(`${ROUTES.ERP_CLIENT_ACCOUNTS}/${r.vendor_id}`) : undefined}
              />
            );
          }}
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
