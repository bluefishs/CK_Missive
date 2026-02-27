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
 * @version 4.0.0 - 提取欄位定義與匯出邏輯至 payments/ 子模組
 * @date 2026-02-27
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
import { logger } from '../../services/logger';

import type { PaymentControlItem } from '../../types/api';

import { WORK_TYPE_COLUMNS, formatDate, formatAmount, usePaymentColumns } from './payments/usePaymentColumns';
import { exportPaymentExcel } from './payments/paymentExport';

const { Text, Title } = Typography;

export interface PaymentsTabProps {
  contractProjectId: number;
}

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

  // 建立表格欄位（已提取至 usePaymentColumns）
  const columns = usePaymentColumns(navigate);

  // 匯出 Excel 功能
  const handleExportExcel = async () => {
    if (items.length === 0) {
      message.warning('無資料可匯出');
      return;
    }

    try {
      message.loading({ content: '正在產生 Excel...', key: 'export' });
      await exportPaymentExcel(items, totalBudget, '契金管控總表');
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
      renderItem={(item: PaymentControlItem, index: number) => (
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
