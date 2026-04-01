/**
 * ERP 損益趨勢分析頁籤
 *
 * 以表格 + 簡易長條圖顯示多年度收入/成本/毛利趨勢
 */
import { Card, Table, Empty, Spin, Row, Col, Statistic, Progress } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useERPProfitTrend } from '../../hooks/business/useERPQuotations';
import type { ERPProfitTrendItem } from '../../types/erp';

export default function ProfitTrendTab() {
  const { data: trend, isLoading } = useERPProfitTrend();

  if (isLoading) return <Spin description="載入趨勢..." style={{ display: 'block', margin: '40px auto' }} />;
  if (!trend || trend.length === 0) {
    return <Card><Empty description="尚無多年度資料" /></Card>;
  }

  // 計算最大值以繪製簡易長條比例
  const maxRevenue = Math.max(...trend.map(t => Number(t.revenue)), 1);

  const columns: ColumnsType<ERPProfitTrendItem> = [
    {
      title: '年度',
      dataIndex: 'year',
      key: 'year',
      width: 80,
      align: 'center',
      render: (v?: number) => v ? (v < 1911 ? v + 1911 : v) : '-',
    },
    {
      title: '案件數',
      dataIndex: 'case_count',
      key: 'case_count',
      width: 80,
      align: 'center',
    },
    {
      title: '收入',
      dataIndex: 'revenue',
      key: 'revenue',
      width: 150,
      align: 'right',
      render: (val: string) => Number(val).toLocaleString(),
    },
    {
      title: '成本',
      dataIndex: 'cost',
      key: 'cost',
      width: 150,
      align: 'right',
      render: (val: string) => Number(val).toLocaleString(),
    },
    {
      title: '毛利',
      dataIndex: 'gross_profit',
      key: 'gross_profit',
      width: 150,
      align: 'right',
      render: (val: string) => {
        const num = Number(val);
        return <span style={{ color: num >= 0 ? '#3f8600' : '#cf1322' }}>{num.toLocaleString()}</span>;
      },
    },
    {
      title: '毛利率',
      dataIndex: 'gross_margin',
      key: 'gross_margin',
      width: 100,
      align: 'center',
      render: (val: string | null) => (val ? `${Number(val).toFixed(1)}%` : '-'),
    },
    {
      title: '收入占比',
      key: 'bar',
      width: 200,
      render: (_: unknown, record: ERPProfitTrendItem) => {
        const pct = Math.round((Number(record.revenue) / maxRevenue) * 100);
        return <Progress percent={pct} showInfo={false} strokeColor="#1890ff" />;
      },
    },
  ];

  // 彙總
  const totalRevenue = trend.reduce((s, t) => s + Number(t.revenue), 0);
  const totalCost = trend.reduce((s, t) => s + Number(t.cost), 0);
  const totalGross = trend.reduce((s, t) => s + Number(t.gross_profit), 0);
  const avgMargin = totalRevenue > 0 ? (totalGross / totalRevenue * 100) : 0;

  return (
    <>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="累計收入" value={totalRevenue} precision={0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="累計成本" value={totalCost} precision={0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="累計毛利"
              value={totalGross}
              precision={0}
              styles={{ content: { color: totalGross >= 0 ? '#3f8600' : '#cf1322' } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="平均毛利率" value={avgMargin} precision={1} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Card title="年度損益趨勢">
        <Table<ERPProfitTrendItem>
          rowKey="year"
          columns={columns}
          dataSource={trend}
          pagination={false}
          size="small"
        />
      </Card>
    </>
  );
}
