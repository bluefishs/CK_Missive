/**
 * 標案詳情頁面
 *
 * 顯示標案完整資訊（機關/採購/招標/決標），含歷次公告時間軸。
 *
 * @version 1.0.0
 */
import React from 'react';
import {
  Descriptions, Tag, Timeline, Card, Typography, Button, Space, Spin, Empty, Row, Col,
} from 'antd';
import {
  BankOutlined, PhoneOutlined, MailOutlined, DollarOutlined,
  CalendarOutlined, LinkOutlined, EnvironmentOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';
import { useTenderDetail } from '../hooks/business/useTender';

const { Text } = Typography;

const TenderDetailPage: React.FC = () => {
  const { unitId, jobNumber } = useParams<{ unitId: string; jobNumber: string }>();
  const { data: detail, isLoading } = useTenderDetail(
    unitId ? decodeURIComponent(unitId) : null,
    jobNumber ? decodeURIComponent(jobNumber) : null,
  );

  if (!detail && !isLoading) {
    return (
      <DetailPageLayout
        header={{ title: '查無此標案', backPath: '/tender/search' }}
        tabs={[]}
        hasData={false}
      />
    );
  }

  const latest = detail?.latest?.detail;

  // Tab 1: 基本資訊
  const infoTab = createTabItem('info', { icon: <BankOutlined />, text: '基本資訊' },
    latest ? (
      <div>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          {latest.budget && (
            <Col xs={12} sm={8} lg={6}>
              <Card size="small">
                <div style={{ color: '#8c8c8c', fontSize: 12 }}>預算金額</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: '#1890ff' }}>
                  <DollarOutlined /> {latest.budget}
                </div>
              </Card>
            </Col>
          )}
          <Col xs={12} sm={8} lg={6}>
            <Card size="small">
              <div style={{ color: '#8c8c8c', fontSize: 12 }}>招標方式</div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>{latest.method || '-'}</div>
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small">
              <div style={{ color: '#8c8c8c', fontSize: 12 }}>決標方式</div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>{latest.award_method || '-'}</div>
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small">
              <div style={{ color: '#8c8c8c', fontSize: 12 }}>狀態</div>
              <Tag color="blue">{latest.status || '-'}</Tag>
            </Card>
          </Col>
        </Row>

        <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
          <Descriptions.Item label="標案案號">{detail?.job_number}</Descriptions.Item>
          <Descriptions.Item label="標的分類">{latest.procurement_type || '-'}</Descriptions.Item>
          <Descriptions.Item label={<><BankOutlined /> 招標機關</>}>{latest.agency_name}</Descriptions.Item>
          <Descriptions.Item label="承辦單位">{latest.agency_unit || '-'}</Descriptions.Item>
          <Descriptions.Item label={<><EnvironmentOutlined /> 地址</>} span={2}>{latest.agency_address || '-'}</Descriptions.Item>
          <Descriptions.Item label={<><PhoneOutlined /> 聯絡人</>}>{latest.contact_person || '-'} {latest.contact_phone || ''}</Descriptions.Item>
          <Descriptions.Item label={<><MailOutlined /> Email</>}>{latest.contact_email || '-'}</Descriptions.Item>
          <Descriptions.Item label={<><CalendarOutlined /> 公告日</>}>{latest.announce_date || '-'}</Descriptions.Item>
          <Descriptions.Item label="截止投標">{latest.deadline || '-'}</Descriptions.Item>
        </Descriptions>

        {latest.pcc_url && (
          <div style={{ marginTop: 16 }}>
            <Button type="primary" icon={<LinkOutlined />} href={latest.pcc_url} target="_blank">
              前往政府採購網原始頁面
            </Button>
          </div>
        )}
      </div>
    ) : <Spin />
  );

  // Tab 2: 歷次公告
  const timelineTab = createTabItem('timeline', { icon: <CalendarOutlined />, text: '公告歷程', count: detail?.events?.length },
    <Timeline
      mode="left"
      items={(detail?.events ?? []).map((evt, i) => ({
        key: i,
        color: i === 0 ? 'blue' : 'gray',
        label: evt.date ? String(evt.date) : '',
        children: (
          <div>
            <Tag color={i === 0 ? 'blue' : 'default'}>{evt.type}</Tag>
            <Text>{evt.title}</Text>
            {evt.companies.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {evt.companies.map((c, j) => <Tag key={j} color="green">{c}</Tag>)}
              </div>
            )}
          </div>
        ),
      }))}
    />
  );

  // Tab 3: 得標廠商
  const companiesTab = createTabItem('companies', { icon: <BankOutlined />, text: '投標/得標' },
    <div>
      {(detail?.events ?? []).filter(e => e.companies.length > 0).length === 0 ? (
        <Empty description="尚無投標/得標紀錄" />
      ) : (
        (detail?.events ?? []).filter(e => e.companies.length > 0).map((evt, i) => (
          <Card key={i} size="small" title={evt.type} style={{ marginBottom: 8 }}>
            <Space wrap>
              {evt.companies.map((c, j) => <Tag key={j} color="blue">{c}</Tag>)}
            </Space>
          </Card>
        ))
      )}
    </div>
  );

  return (
    <DetailPageLayout
      header={{
        title: detail?.title ?? '載入中...',
        backPath: '/tender/search',
        subtitle: detail?.unit_name,
      }}
      tabs={[infoTab, timelineTab, companiesTab]}
      loading={isLoading}
      hasData={!!detail}
    />
  );
};

export default TenderDetailPage;
