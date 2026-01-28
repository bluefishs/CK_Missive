/**
 * 經費分析 Tab
 *
 * 純 UI 元件，所有資料與邏輯由 useBudgetAnalysis Hook 提供。
 * 功能：案件類別圓餅圖、執行狀態長條圖、委託單位經費表。
 * 支援三維篩選互動（案件類別/執行狀態/委託單位聯動）。
 */

import React from 'react';
import {
  Card,
  Typography,
  Row,
  Col,
  Statistic,
  Select,
  Space,
  Table,
  Spin,
  Empty,
  Button,
} from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import {
  DollarOutlined,
  ProjectOutlined,
  TeamOutlined,
  FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useBudgetAnalysis } from './hooks/useBudgetAnalysis';
import { formatCurrency, getCategoryDisplayName, getStatusDisplayName, COLORS } from './constants';

const { Text } = Typography;

interface BudgetAnalysisTabProps {
  isMobile: boolean;
}

const BudgetAnalysisTab: React.FC<BudgetAnalysisTabProps> = ({ isMobile }) => {
  const {
    loading,
    selectedYear,
    setSelectedYear,
    yearOptions,
    projects,
    stats,
    allStats,
    filterCategory,
    setFilterCategory,
    filterStatus,
    setFilterStatus,
    filterAgency,
    setFilterAgency,
    hasFilter,
    clearAllFilters,
    handleCategoryClick,
    handleStatusClick,
    handleAgencyClick,
  } = useBudgetAnalysis();

  // 委託單位表格欄位
  const agencyColumns = [
    {
      title: '委託單位',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '案件數',
      dataIndex: 'count',
      key: 'count',
      width: 80,
      sorter: (a: { count: number }, b: { count: number }) => a.count - b.count,
    },
    {
      title: '經費總額',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      sorter: (a: { amount: number }, b: { amount: number }) => a.amount - b.amount,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: '占比',
      key: 'percentage',
      width: 80,
      render: (_: unknown, record: { amount: number }) => {
        const pct = stats.totalAmount > 0 ? (record.amount / stats.totalAmount) * 100 : 0;
        return `${pct.toFixed(1)}%`;
      },
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      {/* 年度選擇與篩選狀態 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle" gutter={[8, 8]}>
          <Col>
            <Space wrap>
              <Text strong>分析年度：</Text>
              <Select
                value={selectedYear}
                onChange={setSelectedYear}
                style={{ width: 120 }}
                placeholder="選擇年度"
              >
                <Select.Option value="all">全部年度</Select.Option>
                {yearOptions.map((year) => (
                  <Select.Option key={year} value={year}>
                    {year} 年
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col>
            {hasFilter && (
              <Space wrap size="small">
                <FilterOutlined style={{ color: '#1890ff' }} />
                {filterCategory && (
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    onClick={() => setFilterCategory(null)}
                  >
                    類別: {filterCategory} ×
                  </Button>
                )}
                {filterStatus && (
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    onClick={() => setFilterStatus(null)}
                  >
                    狀態: {filterStatus} ×
                  </Button>
                )}
                {filterAgency && (
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    onClick={() => setFilterAgency(null)}
                  >
                    單位: {filterAgency.substring(0, 8)}... ×
                  </Button>
                )}
                <Button
                  size="small"
                  icon={<ClearOutlined />}
                  onClick={clearAllFilters}
                >
                  清除全部
                </Button>
              </Space>
            )}
          </Col>
        </Row>
      </Card>

      {/* 統計說明 */}
      <div style={{ marginBottom: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          ※ 經費統計以「得標金額」計算，不含待執行及未得標案件
        </Text>
      </div>

      {/* 統計卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={hasFilter ? '篩選後案件數' : '有效案件數'}
              value={stats.totalProjects}
              prefix={<ProjectOutlined />}
              suffix={hasFilter ? `/ ${allStats.totalCount} 件` : '件'}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={hasFilter ? '篩選後得標金額' : '得標金額總計'}
              value={stats.totalAmount}
              prefix={<DollarOutlined />}
              formatter={(value) => formatCurrency(Number(value))}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="委託單位數"
              value={stats.uniqueAgencyCount}
              prefix={<TeamOutlined />}
              suffix="個"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {projects.length === 0 ? (
        <Card>
          <Empty description="暫無資料" />
        </Card>
      ) : (
        <>
          {/* 圖表區域：案件類別 + 執行狀態 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <span>案件類別分布</span>
                    {!filterCategory && (
                      <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                        (點擊篩選)
                      </Text>
                    )}
                  </Space>
                }
                size="small"
                extra={
                  filterCategory && (
                    <Button type="link" size="small" onClick={() => setFilterCategory(null)}>
                      取消篩選
                    </Button>
                  )
                }
              >
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie
                      data={stats.byCategory}
                      cx="50%"
                      cy="45%"
                      labelLine={false}
                      label={
                        isMobile
                          ? undefined
                          : (entry: any) => entry.name.replace(/^0\d/, '').substring(0, 4)
                      }
                      outerRadius={isMobile ? 70 : 80}
                      fill="#8884d8"
                      dataKey="amount"
                      onClick={(data) => handleCategoryClick(data.name)}
                      style={{ cursor: 'pointer' }}
                    >
                      {stats.byCategory.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                          opacity={filterCategory && filterCategory !== entry.name ? 0.3 : 1}
                          stroke={filterCategory === entry.name ? '#000' : undefined}
                          strokeWidth={filterCategory === entry.name ? 2 : 0}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div
                              style={{
                                background: '#fff',
                                padding: '8px 12px',
                                border: '1px solid #ccc',
                                borderRadius: 4,
                              }}
                            >
                              <div style={{ fontWeight: 'bold' }}>{data.name}</div>
                              <div>案件數: {data.count} 件</div>
                              <div>經費: {formatCurrency(data.amount)}</div>
                              <div style={{ fontSize: 12, color: '#1890ff', marginTop: 4 }}>
                                {filterCategory === data.name ? '點擊取消篩選' : '點擊篩選此類別'}
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Legend
                      layout="horizontal"
                      verticalAlign="bottom"
                      align="center"
                      wrapperStyle={{ paddingTop: 16 }}
                      formatter={(value: string, entry: any) => {
                        const data = entry.payload;
                        return `${value}: ${data.count}件 ${formatCurrency(data.amount)}`;
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <span>執行狀態分布</span>
                    {!filterStatus && (
                      <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                        (點擊篩選)
                      </Text>
                    )}
                  </Space>
                }
                size="small"
                extra={
                  filterStatus && (
                    <Button type="link" size="small" onClick={() => setFilterStatus(null)}>
                      取消篩選
                    </Button>
                  )
                }
              >
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={stats.byStatus}
                    layout="vertical"
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={80} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div
                              style={{
                                background: '#fff',
                                padding: '8px 12px',
                                border: '1px solid #ccc',
                                borderRadius: 4,
                              }}
                            >
                              <div style={{ fontWeight: 'bold' }}>{data.name}</div>
                              <div>案件數: {data.count} 件</div>
                              <div>經費: {formatCurrency(data.amount)}</div>
                              <div style={{ fontSize: 12, color: '#1890ff', marginTop: 4 }}>
                                {filterStatus === data.name ? '點擊取消篩選' : '點擊篩選此狀態'}
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar
                      dataKey="count"
                      name="案件數"
                      onClick={(data: any) => handleStatusClick(data.name)}
                      style={{ cursor: 'pointer' }}
                    >
                      {stats.byStatus.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                          opacity={filterStatus && filterStatus !== entry.name ? 0.3 : 1}
                          stroke={filterStatus === entry.name ? '#000' : undefined}
                          strokeWidth={filterStatus === entry.name ? 2 : 0}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>

          {/* 委託單位經費分析表 */}
          <Card
            title={
              <Space>
                <span>委託單位經費分析</span>
                {!filterAgency && (
                  <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                    (點擊查看明細)
                  </Text>
                )}
              </Space>
            }
            size="small"
            extra={
              filterAgency && (
                <Button type="link" size="small" onClick={() => setFilterAgency(null)}>
                  返回列表
                </Button>
              )
            }
          >
            {filterAgency ? (
              <div>
                <div style={{ marginBottom: 12, padding: '8px 12px', background: '#f5f5f5', borderRadius: 4 }}>
                  <Text strong>委託單位：</Text>
                  <Text>{filterAgency}</Text>
                  <Text type="secondary" style={{ marginLeft: 16 }}>
                    共 {stats.byAgency.find((a) => a.name === filterAgency)?.count || 0} 件，
                    經費 {formatCurrency(stats.byAgency.find((a) => a.name === filterAgency)?.amount || 0)}
                  </Text>
                </div>
                <Table
                  dataSource={stats.byAgency.find((a) => a.name === filterAgency)?.projects || []}
                  size="small"
                  rowKey="id"
                  pagination={{ pageSize: 10, size: 'small' }}
                  scroll={{ x: isMobile ? 500 : undefined }}
                  columns={[
                    {
                      title: '案件名稱',
                      dataIndex: 'project_name',
                      key: 'project_name',
                      ellipsis: true,
                    },
                    {
                      title: '類別',
                      dataIndex: 'category',
                      key: 'category',
                      width: 120,
                      render: (value: string) => getCategoryDisplayName(value || '未分類'),
                    },
                    {
                      title: '得標金額',
                      dataIndex: 'contract_amount',
                      key: 'contract_amount',
                      width: 120,
                      render: (value: number) => (value ? formatCurrency(value) : '-'),
                    },
                    {
                      title: '狀態',
                      dataIndex: 'status',
                      key: 'status',
                      width: 100,
                      render: (value: string) => getStatusDisplayName(value || '未設定'),
                    },
                  ]}
                />
              </div>
            ) : (
              <>
                <Table
                  dataSource={stats.byAgency.slice(0, 15)}
                  columns={agencyColumns}
                  pagination={false}
                  size="small"
                  rowKey="name"
                  scroll={{ x: isMobile ? 400 : undefined }}
                  onRow={(record) => ({
                    onClick: () => handleAgencyClick(record.name),
                    style: { cursor: 'pointer' },
                  })}
                />
                {stats.byAgency.length > 15 && (
                  <div style={{ textAlign: 'center', marginTop: 8 }}>
                    <Text type="secondary">僅顯示前 15 筆，共 {stats.byAgency.length} 個單位</Text>
                  </div>
                )}
              </>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

export default BudgetAnalysisTab;
