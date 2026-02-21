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
 * @version 3.1.0 - RWD 響應式改造
 * @date 2026-01-23
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
  List,
  Collapse,
  Tag,
} from 'antd';
import {
  ReloadOutlined,
  DollarOutlined,
  DownloadOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useResponsive, useTaoyuanPaymentControl } from '../../hooks';
import { useNavigate } from 'react-router-dom';
import type { ColumnGroupType, ColumnType } from 'antd/es/table';
import dayjs from 'dayjs';
import * as XLSX from 'xlsx';
import { logger } from '../../services/logger';

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

  // RWD 響應式
  const { isMobile } = useResponsive();

  // 使用集中的 Hook 查詢契金管控資料
  const {
    items,
    totalBudget,
    totalDispatched,
    isLoading,
    refetch,
  } = useTaoyuanPaymentControl(contractProjectId);

  const totalRemaining = (totalBudget || 9630000) - totalDispatched;

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
        title: '派工單號',
        dataIndex: 'dispatch_no',
        width: 120,
        fixed: 'left',
        render: (val: string, record) => (
          <Button
            type="link"
            size="small"
            style={{ padding: 0, color: '#1890ff' }}
            onClick={() => navigate(`/taoyuan/dispatch/${record.dispatch_order_id}`)}
          >
            {val}
          </Button>
        ),
      },
      {
        title: '工程名稱/派工事項',
        dataIndex: 'project_name',
        width: 280,
        fixed: 'left',
        ellipsis: { showTitle: false },
        render: (val: string) => (
          <Tooltip title={val}>
            <span style={{ whiteSpace: 'normal', lineHeight: 1.3 }}>
              {val || '-'}
            </span>
          </Tooltip>
        ),
      },
    ];

    // 7 種作業類別欄位群組
    const workTypeColumnGroups: ColumnGroupType<PaymentControlItem>[] = WORK_TYPE_COLUMNS.map(
      (workType) => ({
        title: <span style={{ fontWeight: 600, color: '#262626' }}>{workType.label}</span>,
        key: workType.key,
        align: 'center' as const,
        onHeaderCell: () => ({
          style: {
            background: workType.color,
            textAlign: 'center',
            fontWeight: 600,
            padding: '8px 4px',
          },
        }),
        children: [
          {
            title: '派工日期',
            dataIndex: workType.dateField,
            key: `${workType.key}_date`,
            width: 76,
            align: 'center' as const,
            onCell: () => ({
              style: {
                background: workType.color,
                fontSize: 12,
                padding: '6px 4px',
                textAlign: 'center',
              },
            }),
            onHeaderCell: () => ({
              style: {
                background: workType.color,
                fontSize: 11,
                padding: '6px 4px',
                textAlign: 'center',
                fontWeight: 500,
              },
            }),
            render: (val: string | null) => (
              <span style={{ color: val ? '#595959' : '#bfbfbf' }}>
                {formatDate(val)}
              </span>
            ),
          },
          {
            title: '派工金額',
            dataIndex: workType.amountField,
            key: `${workType.key}_amount`,
            width: 82,
            align: 'right' as const,
            onCell: () => ({
              style: {
                background: workType.color,
                fontSize: 12,
                padding: '6px 6px',
              },
            }),
            onHeaderCell: () => ({
              style: {
                background: workType.color,
                fontSize: 11,
                padding: '6px 4px',
                textAlign: 'center',
                fontWeight: 500,
              },
            }),
            render: (val: number | null) => (
              <span style={{ color: val ? '#1890ff' : '#bfbfbf', fontWeight: val ? 500 : 400 }}>
                {formatAmount(val)}
              </span>
            ),
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
      logger.error('匯出 Excel 失敗:', error);
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

  // 手機版摺疊卡片
  const MobilePaymentList = () => (
    <List
      dataSource={items}
      loading={isLoading}
      pagination={{
        size: 'small',
        pageSize: 10,
        showTotal: (total) => `共 ${total} 筆`,
      }}
      renderItem={(item, index) => (
        <Card
          size="small"
          style={{ marginBottom: 8, cursor: 'pointer' }}
          onClick={() => navigate(`/taoyuan/dispatch/${item.dispatch_order_id}`)}
          hoverable
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Text strong style={{ color: '#1890ff', fontSize: 13 }}>
                #{index + 1} {item.dispatch_no}
              </Text>
              <div style={{ fontSize: 12, marginTop: 2, color: '#666' }}>
                {item.project_name}
              </div>
              <div style={{ marginTop: 8 }}>
                <Row gutter={[8, 4]}>
                  <Col span={12}>
                    <Text type="secondary" style={{ fontSize: 11 }}>本次派工：</Text>
                    <Text strong style={{ color: '#1890ff', fontSize: 12 }}>
                      ${formatAmount(item.current_amount ? Math.round(item.current_amount) : undefined)}
                    </Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary" style={{ fontSize: 11 }}>累進金額：</Text>
                    <Text style={{ fontSize: 12 }}>
                      ${formatAmount(item.cumulative_amount ? Math.round(item.cumulative_amount) : undefined)}
                    </Text>
                  </Col>
                </Row>
              </div>
              <Collapse
                ghost
                size="small"
                style={{ marginTop: 4 }}
                items={[{
                  key: '1',
                  label: <Text type="secondary" style={{ fontSize: 11 }}>展開作業類別明細</Text>,
                  children: (
                    <div style={{ fontSize: 11 }}>
                      {WORK_TYPE_COLUMNS.map((wt) => {
                        const amount = Number((item as unknown as Record<string, unknown>)[wt.amountField]) || 0;
                        if (amount === 0) return null;
                        return (
                          <Row key={wt.key} style={{ marginBottom: 4 }}>
                            <Col span={14}>
                              <Tag color="blue" style={{ fontSize: 10 }}>{wt.label.slice(0, 8)}</Tag>
                            </Col>
                            <Col span={10} style={{ textAlign: 'right' }}>
                              ${formatAmount(Math.round(amount))}
                            </Col>
                          </Row>
                        );
                      })}
                    </div>
                  ),
                }]}
              />
            </div>
            <RightOutlined style={{ color: '#ccc', marginTop: 4 }} />
          </div>
        </Card>
      )}
    />
  );

  return (
    <div>
      {/* 標題與契約金額 - RWD 響應式 */}
      <Card size="small" style={{ marginBottom: isMobile ? 12 : 16, background: '#fafafa' }}>
        <Row justify="space-between" align={isMobile ? 'top' : 'middle'} gutter={[0, 8]}>
          <Col xs={24} md={18}>
            <Title level={5} style={{ margin: 0, fontSize: isMobile ? 13 : 16 }}>
              {isMobile
                ? '112-113年桃園查估測量委託專業服務'
                : '112至113年度桃園市轄內興辦公共設施工程用地取得所需土地市價及地上物查估、測量作業暨相關計畫書製作委託專業服務(開口契約)'}
            </Title>
          </Col>
          <Col xs={24} md={6} style={{ textAlign: isMobile ? 'left' : 'right' }}>
            <Space>
              <Text type="secondary" style={{ fontSize: isMobile ? 12 : 14 }}>契約金額：</Text>
              <Text strong style={{ fontSize: isMobile ? 14 : 18, color: '#1890ff' }}>
                ${totalBudget.toLocaleString()}
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 統計卡片 - RWD 響應式 */}
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={12} sm={8} md={5}>
          <Card size="small">
            <Statistic
              title={isMobile ? '總預算' : '總預算金額'}
              value={totalBudget}
              prefix={<DollarOutlined />}
              precision={0}
              valueStyle={{ color: '#262626', fontSize: isMobile ? 16 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={5}>
          <Card size="small">
            <Statistic
              title={isMobile ? '累計派工' : '累計派工金額'}
              value={totalDispatched}
              precision={0}
              valueStyle={{ color: '#1890ff', fontSize: isMobile ? 16 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={5}>
          <Card size="small">
            <Statistic
              title={isMobile ? '剩餘' : '剩餘金額'}
              value={totalRemaining}
              precision={0}
              valueStyle={{ color: totalRemaining < 1000000 ? '#faad14' : '#52c41a', fontSize: isMobile ? 16 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={5}>
          <Card size="small">
            <Statistic
              title="派工單數"
              value={items.length}
              suffix="筆"
              valueStyle={{ fontSize: isMobile ? 16 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small">
            <Statistic
              title="執行率"
              value={totalBudget > 0 ? ((totalDispatched / totalBudget) * 100).toFixed(1) : 0}
              suffix="%"
              valueStyle={{ color: '#722ed1', fontSize: isMobile ? 16 : 24 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 各作業類別金額統計 - RWD 響應式 */}
      {!isMobile && (
        <Card size="small" title="作業類別派工金額統計" style={{ marginBottom: 16 }}>
          <Row gutter={[8, 8]}>
            {WORK_TYPE_COLUMNS.map((wt) => (
              <Col key={wt.key} xs={12} sm={6} md={3}>
                <Card
                  size="small"
                  style={{ background: wt.color, textAlign: 'center' }}
                  styles={{ body: { padding: '8px 12px' } }}
                >
                  <div style={{ fontSize: 11, color: '#595959', marginBottom: 4 }}>
                    {wt.label}
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: '#262626' }}>
                    {formatAmount(workTypeTotals[wt.key]) || '0'}
                  </div>
                </Card>
              </Col>
            ))}
            <Col xs={12} sm={6} md={3}>
              <Card
                size="small"
                style={{ background: '#fffbe6', textAlign: 'center', borderColor: '#faad14' }}
                styles={{ body: { padding: '8px 12px' } }}
              >
                <div style={{ fontSize: 11, color: '#595959', marginBottom: 4 }}>
                  合計
                </div>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#1890ff' }}>
                  {formatAmount(Object.values(workTypeTotals).reduce((a, b) => a + b, 0))}
                </div>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* 工具列 - RWD 響應式 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={24} style={{ textAlign: isMobile ? 'left' : 'left' }}>
          <Space wrap size={isMobile ? 'small' : 'middle'}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetch()}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '重新整理'}
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExportExcel}
              type="primary"
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '匯出' : '匯出 Excel'}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 契金紀錄 - RWD: 手機用卡片清單，桌面用表格 */}
      {isMobile ? (
        <MobilePaymentList />
      ) : (
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
              <Table.Summary.Cell index={0} colSpan={3}>
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
      )}
    </div>
  );
};

export default PaymentsTab;
