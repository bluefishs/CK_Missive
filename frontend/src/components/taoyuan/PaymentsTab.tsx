/**
 * 桃園查估派工 - 契金管控 Tab
 *
 * 功能：
 * - 展示所有派工單的契金紀錄（類似 Excel 總表格式）
 * - 7 種作業類別分別顯示派工日期與金額
 * - 派工日期自動取第一筆機關來函日期
 * - 點擊派工單號導航至詳情頁進行維護
 * - 支援匯出 Excel 功能
 *
 * @version 3.0.0
 * @date 2026-01-22
 */

import React, { useMemo } from 'react';
import {
  Typography,
  Button,
  Space,
  Card,
  Table,
  Statistic,
  Row,
  Col,
  Tooltip,
  App,
} from 'antd';
import {
  ReloadOutlined,
  DollarOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType, ColumnGroupType, ColumnType } from 'antd/es/table';
import dayjs from 'dayjs';
import * as XLSX from 'xlsx';

import { contractPaymentsApi } from '../../api/taoyuanDispatchApi';
import type { PaymentControlItem } from '../../types/api';

const { Text, Title } = Typography;

export interface PaymentsTabProps {
  contractProjectId: number;
}

/** 作業類別定義 */
const WORK_TYPE_COLUMNS = [
  { key: '01', label: '01.地上物查估', dateField: 'work_01_date', amountField: 'work_01_amount', color: '#e6fffb' },
  { key: '02', label: '02.土地協議市價查估', dateField: 'work_02_date', amountField: 'work_02_amount', color: '#fffbe6' },
  { key: '03', label: '03.土地徵收市價查估', dateField: 'work_03_date', amountField: 'work_03_amount', color: '#fff2e8' },
  { key: '04', label: '04.相關計畫書製作', dateField: 'work_04_date', amountField: 'work_04_amount', color: '#f9f0ff' },
  { key: '05', label: '05.測量作業', dateField: 'work_05_date', amountField: 'work_05_amount', color: '#e6f7ff' },
  { key: '06', label: '06.樁位測釘作業', dateField: 'work_06_date', amountField: 'work_06_amount', color: '#f6ffed' },
  { key: '07', label: '07.辦理教育訓練', dateField: 'work_07_date', amountField: 'work_07_amount', color: '#fff0f6' },
];

/** 格式化日期 */
const formatDate = (val?: string | null) => {
  if (!val) return '-';
  const d = dayjs(val);
  // 使用民國年格式
  const rocYear = d.year() - 1911;
  return `${rocYear}.${d.format('M.D')}`;
};

/** 格式化金額（整數，無小數） */
const formatAmount = (val?: number | null) => {
  if (val === undefined || val === null || val === 0) return '-';
  return Math.round(val).toLocaleString();
};

export const PaymentsTab: React.FC<PaymentsTabProps> = ({ contractProjectId }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  const {
    data: controlData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['payment-control', contractProjectId],
    queryFn: () => contractPaymentsApi.getControlList(contractProjectId),
  });

  const items = controlData?.items ?? [];
  const totalBudget = controlData?.total_budget ?? 9630000;
  const totalDispatched = controlData?.total_dispatched ?? 0;
  const totalRemaining = totalBudget - totalDispatched;

  // 建立表格欄位
  const columns: (ColumnGroupType<PaymentControlItem> | ColumnType<PaymentControlItem>)[] = useMemo(() => {
    // 基本欄位
    const baseColumns: ColumnType<PaymentControlItem>[] = [
      {
        title: '序',
        key: 'index',
        width: 40,
        fixed: 'left',
        align: 'center',
        render: (_, __, index) => index + 1,
      },
      {
        title: '分案名稱',
        dataIndex: 'project_name',
        width: 280,
        fixed: 'left',
        ellipsis: { showTitle: false },
        render: (val: string, record) => (
          <Tooltip title={val}>
            <Button
              type="link"
              size="small"
              style={{ padding: 0, textAlign: 'left', whiteSpace: 'normal', height: 'auto', lineHeight: 1.3 }}
              onClick={() => navigate(`/taoyuan/dispatch/${record.dispatch_order_id}`)}
            >
              {val || record.dispatch_no}
            </Button>
          </Tooltip>
        ),
      },
    ];

    // 7 種作業類別欄位群組
    const workTypeColumnGroups: ColumnGroupType<PaymentControlItem>[] = WORK_TYPE_COLUMNS.map(
      (workType) => ({
        title: workType.label,
        key: workType.key,
        children: [
          {
            title: '派工日期',
            dataIndex: workType.dateField,
            key: `${workType.key}_date`,
            width: 72,
            align: 'center' as const,
            onCell: () => ({ style: { background: workType.color, fontSize: 11, padding: '4px 2px' } }),
            onHeaderCell: () => ({ style: { background: workType.color, fontSize: 10, padding: '4px 2px' } }),
            render: (val: string | null) => formatDate(val),
          },
          {
            title: '派工金額',
            dataIndex: workType.amountField,
            key: `${workType.key}_amount`,
            width: 78,
            align: 'right' as const,
            onCell: () => ({ style: { background: workType.color, fontSize: 11, padding: '4px 4px' } }),
            onHeaderCell: () => ({ style: { background: workType.color, fontSize: 10, padding: '4px 2px' } }),
            render: (val: number | null) => formatAmount(val),
          },
        ],
      })
    );

    // 彙總欄位（移除履約期限、驗收日期、備註）
    const summaryColumns: ColumnType<PaymentControlItem>[] = [
      {
        title: '本次派工總金額',
        dataIndex: 'current_amount',
        key: 'current_amount',
        width: 110,
        align: 'right',
        onCell: () => ({ style: { background: '#fffbe6' } }),
        onHeaderCell: () => ({ style: { background: '#fffbe6' } }),
        render: (val?: number) => (
          <Text strong style={{ color: '#1890ff' }}>
            {formatAmount(val ? Math.round(val) : undefined)}
          </Text>
        ),
      },
      {
        title: '累進派工金額',
        dataIndex: 'cumulative_amount',
        key: 'cumulative_amount',
        width: 110,
        align: 'right',
        onCell: () => ({ style: { background: '#e6f7ff' } }),
        onHeaderCell: () => ({ style: { background: '#e6f7ff' } }),
        render: (val?: number) => formatAmount(val ? Math.round(val) : undefined),
      },
      {
        title: '剩餘金額',
        dataIndex: 'remaining_amount',
        key: 'remaining_amount',
        width: 110,
        align: 'right',
        onCell: (record) => ({
          style: {
            background: (record.remaining_amount ?? 0) < 1000000 ? '#fff2e8' : '#f6ffed',
          },
        }),
        onHeaderCell: () => ({ style: { background: '#f6ffed' } }),
        render: (val?: number) => (
          <Text type={(val ?? 0) < 1000000 ? 'warning' : undefined}>
            {formatAmount(val ? Math.round(val) : undefined)}
          </Text>
        ),
      },
    ];

    return [...baseColumns, ...workTypeColumnGroups, ...summaryColumns];
  }, [navigate]);

  // 匯出 Excel 功能 (使用 xlsx 庫生成真正的 .xlsx 檔案)
  const handleExportExcel = async () => {
    if (items.length === 0) {
      message.warning('無資料可匯出');
      return;
    }

    try {
      message.loading({ content: '正在產生 Excel...', key: 'export' });

      // 第一行：主標題 (對應 Excel 工作表 4 的欄位結構)
      const headers1 = [
        '序', '派工單號', '工程名稱/派工事項', '作業類別', '分案名稱/派工備註',
        '案件承辦', '查估單位', '雲端資料夾', '專案資料夾',
        '機關函文歷程', '乾坤函文紀錄',
        '01.地上物查估作業', '', '02.土地協議市價查估作業', '',
        '03.土地徵收市價查估作業', '', '04.相關計畫書製作', '',
        '05.測量作業', '', '06.樁位測釘作業', '', '07.辦理教育訓練', '',
        '本次派工總金額', '累進派工金額', '剩餘金額',
      ];

      // 第二行：子標題
      const headers2 = [
        '', '', '', '', '', '', '', '', '', '', '',
        '派工日期', '派工金額', '派工日期', '派工金額',
        '派工日期', '派工金額', '派工日期', '派工金額',
        '派工日期', '派工金額', '派工日期', '派工金額', '派工日期', '派工金額',
        '', '', '',
      ];

      const rows = items.map((item, index) => [
        index + 1,
        item.dispatch_no || '',
        item.project_name || '',
        item.work_type || '',
        item.sub_case_name || '',
        item.case_handler || '',
        item.survey_unit || '',
        item.cloud_folder || '',
        item.project_folder || '',
        item.agency_doc_history || '',
        item.company_doc_history || '',
        formatDate(item.work_01_date), item.work_01_amount ? Math.round(item.work_01_amount) : '',
        formatDate(item.work_02_date), item.work_02_amount ? Math.round(item.work_02_amount) : '',
        formatDate(item.work_03_date), item.work_03_amount ? Math.round(item.work_03_amount) : '',
        formatDate(item.work_04_date), item.work_04_amount ? Math.round(item.work_04_amount) : '',
        formatDate(item.work_05_date), item.work_05_amount ? Math.round(item.work_05_amount) : '',
        formatDate(item.work_06_date), item.work_06_amount ? Math.round(item.work_06_amount) : '',
        formatDate(item.work_07_date), item.work_07_amount ? Math.round(item.work_07_amount) : '',
        item.current_amount ? Math.round(item.current_amount) : '',
        item.cumulative_amount ? Math.round(item.cumulative_amount) : '',
        item.remaining_amount ? Math.round(item.remaining_amount) : '',
      ]);

      // 建立工作表數據
      const wsData = [headers1, headers2, ...rows];

      // 建立工作表
      const ws = XLSX.utils.aoa_to_sheet(wsData);

      // 設定欄寬
      ws['!cols'] = [
        { wch: 4 },   // 序
        { wch: 12 },  // 派工單號
        { wch: 25 },  // 工程名稱
        { wch: 20 },  // 作業類別
        { wch: 15 },  // 分案名稱
        { wch: 10 },  // 案件承辦
        { wch: 10 },  // 查估單位
        { wch: 30 },  // 雲端資料夾
        { wch: 30 },  // 專案資料夾
        { wch: 20 },  // 機關函文歷程
        { wch: 20 },  // 乾坤函文紀錄
        { wch: 10 }, { wch: 12 },  // 01
        { wch: 10 }, { wch: 12 },  // 02
        { wch: 10 }, { wch: 12 },  // 03
        { wch: 10 }, { wch: 12 },  // 04
        { wch: 10 }, { wch: 12 },  // 05
        { wch: 10 }, { wch: 12 },  // 06
        { wch: 10 }, { wch: 12 },  // 07
        { wch: 14 },  // 本次派工總金額
        { wch: 14 },  // 累進派工金額
        { wch: 14 },  // 剩餘金額
      ];

      // 建立工作簿
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, '契金管控總表');

      // 下載檔案
      const filename = `契金管控總表_${dayjs().format('YYYYMMDD')}.xlsx`;
      XLSX.writeFile(wb, filename);

      message.success({ content: '匯出完成', key: 'export' });
    } catch (error) {
      console.error('匯出 Excel 失敗:', error);
      message.error({ content: '匯出失敗', key: 'export' });
    }
  };

  // 計算各作業類別總金額
  const workTypeTotals = useMemo(() => {
    const totals: Record<string, number> = {};
    WORK_TYPE_COLUMNS.forEach((wt) => {
      totals[wt.key] = items.reduce(
        (sum, item) => sum + (Number((item as unknown as Record<string, unknown>)[wt.amountField]) || 0),
        0
      );
    });
    return totals;
  }, [items]);

  return (
    <div>
      {/* 標題與契約金額 */}
      <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={5} style={{ margin: 0 }}>
              112至113年度桃園市轄內興辦公共設施工程用地取得所需土地市價及地上物查估、測量作業暨相關計畫書製作委託專業服務(開口契約)
            </Title>
          </Col>
          <Col>
            <Space>
              <Text type="secondary">契約金額：</Text>
              <Text strong style={{ fontSize: 18, color: '#1890ff' }}>
                ${totalBudget.toLocaleString()}
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={5}>
          <Card size="small">
            <Statistic
              title="總預算金額"
              value={totalBudget}
              prefix={<DollarOutlined />}
              precision={0}
              valueStyle={{ color: '#262626' }}
            />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic
              title="累計派工金額"
              value={totalDispatched}
              precision={0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic
              title="剩餘金額"
              value={totalRemaining}
              precision={0}
              valueStyle={{ color: totalRemaining < 1000000 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={5}>
          <Card size="small">
            <Statistic title="派工單數" value={items.length} suffix="筆" />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="執行率"
              value={totalBudget > 0 ? ((totalDispatched / totalBudget) * 100).toFixed(1) : 0}
              suffix="%"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 各作業類別金額統計 */}
      <Card size="small" title="作業類別派工金額統計" style={{ marginBottom: 16 }}>
        <Row gutter={[8, 8]}>
          {WORK_TYPE_COLUMNS.map((wt) => (
            <Col key={wt.key} span={3}>
              <Card size="small" style={{ background: wt.color }}>
                <Statistic
                  title={<Text style={{ fontSize: 11 }}>{wt.label}</Text>}
                  value={workTypeTotals[wt.key] || 0}
                  precision={0}
                  valueStyle={{ fontSize: 14 }}
                />
              </Card>
            </Col>
          ))}
          <Col span={3}>
            <Card size="small" style={{ background: '#fffbe6' }}>
              <Statistic
                title={<Text style={{ fontSize: 11 }}>合計</Text>}
                value={Object.values(workTypeTotals).reduce((a, b) => a + b, 0)}
                precision={0}
                valueStyle={{ fontSize: 14, color: '#1890ff' }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 工具列 */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          重新整理
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExportExcel} type="primary">
          匯出 Excel
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={items}
        rowKey="dispatch_order_id"
        loading={isLoading}
        scroll={{ x: 2200 }}
        pagination={{
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 筆`,
          defaultPageSize: 50,
          pageSizeOptions: ['20', '50', '100'],
        }}
        size="small"
        bordered
        summary={() => (
          <Table.Summary fixed>
            <Table.Summary.Row style={{ background: '#fafafa', fontWeight: 'bold' }}>
              <Table.Summary.Cell index={0} colSpan={2}>
                合計
              </Table.Summary.Cell>
              {/* 7 種作業類別的合計 */}
              {WORK_TYPE_COLUMNS.map((wt, idx) => (
                <React.Fragment key={wt.key}>
                  <Table.Summary.Cell index={2 + idx * 2}>-</Table.Summary.Cell>
                  <Table.Summary.Cell index={3 + idx * 2} align="right">
                    {formatAmount(workTypeTotals[wt.key])}
                  </Table.Summary.Cell>
                </React.Fragment>
              ))}
              {/* 金額合計 - 本次派工總金額欄位留空（個別金額已在各列顯示） */}
              <Table.Summary.Cell index={16} align="right">
                <Text strong style={{ color: '#1890ff' }}>
                  {formatAmount(Object.values(workTypeTotals).reduce((a, b) => a + b, 0))}
                </Text>
              </Table.Summary.Cell>
              {/* 累進派工金額 - 顯示累計總金額 */}
              <Table.Summary.Cell index={17} align="right">
                <Text strong style={{ color: '#1890ff' }}>
                  {formatAmount(totalDispatched)}
                </Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={18} align="right">
                <Text type={totalRemaining < 1000000 ? 'warning' : undefined}>
                  {formatAmount(totalRemaining)}
                </Text>
              </Table.Summary.Cell>
            </Table.Summary.Row>
          </Table.Summary>
        )}
      />
    </div>
  );
};

export default PaymentsTab;
