/**
 * PM/ERP 專案統計面板
 *
 * 顯示 PM 案件概況與 ERP 財務概況，作為 Dashboard 的統計區塊。
 *
 * @version 1.0.0
 * @date 2026-03-17
 */
import React from 'react';
import { Card, Statistic, Row, Col, Tag, Spin, Empty, Button, Typography } from 'antd';
import {
  ProjectOutlined,
  DollarOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { usePMCaseSummary, useERPProfitSummary } from '../../hooks';

const { Text } = Typography;

export const ProjectStatsPanel: React.FC = () => {
  const navigate = useNavigate();
  // 2026-08-31：`include_converted` 明寫 true，即使那也是後端預設。
  // `/pm/cases` 列表送的是 false（已成案的 136 筆移交 /contract-cases 列管），
  // 而這張卡的標題是「總案件」—— 講的是整條管線，**刻意不跟列表的列管範圍走**。
  // 寫出來是為了讓「兩處數字不一樣」是個決定，不是一個意外。
  const { data: pmSummary, isLoading: pmLoading } = usePMCaseSummary({ include_converted: true });
  const { data: erpSummary, isLoading: erpLoading } = useERPProfitSummary();

  const isLoading = pmLoading || erpLoading;

  if (isLoading) {
    return <Spin description="載入統計..." style={{ display: 'block', margin: '20px auto' }} />;
  }

  const hasPM = pmSummary && pmSummary.total_cases > 0;
  const hasERP = erpSummary && erpSummary.case_count > 0;

  if (!hasPM && !hasERP) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Empty description="尚無 PM/ERP 資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  // 2026-08-16：這三個數字**原本全部恆為 0**。
  //   · `in_progress` —— PM 案件沒有這個狀態（74 筆中 0 筆），且邀標本就不該有「執行中」
  //   · `completed`   —— PM 的詞彙是 `closed`，讀 `completed` 永遠取不到
  //   · 而佔 51 筆的 `contracted`（已承攬）**完全沒有顯示**
  // 面板上三個 0，系統裡卻有 74 筆案件 —— 沒有人會發現，因為 0 看起來就像「還沒有」。
  const pmByStatus = pmSummary?.by_status ?? {};
  const planning = pmByStatus['planning'] ?? 0;
  const contracted = pmByStatus['contracted'] ?? 0;
  const closed = pmByStatus['closed'] ?? 0;

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      {/* PM 案件概況 */}
      {hasPM && (
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<><ProjectOutlined style={{ marginRight: 8 }} />PM 案件概況</>}
            extra={<Button type="link" size="small" onClick={() => navigate('/pm/cases')}>查看全部 <ArrowRightOutlined /></Button>}
          >
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="總案件" value={pmSummary!.total_cases} />
              </Col>
              <Col span={6}>
                <Statistic
                  title="已承攬"
                  value={contracted}
                  prefix={<SyncOutlined />}
                  styles={{ content: { color: '#1890ff' } }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="評估中"
                  value={planning}
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="已結案"
                  value={closed}
                  prefix={<CheckCircleOutlined />}
                  styles={{ content: { color: '#52c41a' } }}
                />
              </Col>
            </Row>
            {pmSummary!.total_contract_amount && (
              <div style={{ marginTop: 8, textAlign: 'right' }}>
                <Text type="secondary">
                  合約總額：<Tag color="blue">{Number(pmSummary!.total_contract_amount).toLocaleString()} 元</Tag>
                </Text>
              </div>
            )}
          </Card>
        </Col>
      )}

      {/* ERP 財務概況 */}
      {hasERP && (
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<><DollarOutlined style={{ marginRight: 8 }} />ERP 財務概況</>}
            extra={<Button type="link" size="small" onClick={() => navigate('/erp/quotations')}>查看全部 <ArrowRightOutlined /></Button>}
          >
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="案件數" value={erpSummary!.case_count} />
              </Col>
              <Col span={6}>
                <Statistic title="營收" value={Number(erpSummary!.total_revenue)} precision={0} />
              </Col>
              <Col span={6}>
                <Statistic
                  title="毛利"
                  value={Number(erpSummary!.total_gross_profit)}
                  precision={0}
                  styles={{ content: { color: Number(erpSummary!.total_gross_profit) >= 0 ? '#3f8600' : '#cf1322' } }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="毛利率"
                  value={erpSummary!.avg_gross_margin ? Number(erpSummary!.avg_gross_margin) : 0}
                  suffix="%"
                  precision={1}
                />
              </Col>
            </Row>
            {Number(erpSummary!.total_outstanding) > 0 && (
              <div style={{ marginTop: 8, textAlign: 'right' }}>
                <Text type="secondary">
                  未收款：<Tag color="orange">{Number(erpSummary!.total_outstanding).toLocaleString()} 元</Tag>
                </Text>
              </div>
            )}
          </Card>
        </Col>
      )}
    </Row>
  );
};

export default ProjectStatsPanel;
