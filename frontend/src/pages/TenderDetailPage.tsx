/**
 * 標案詳情頁面
 *
 * 對標 ezbid.tw 風格：
 * - 生命週期時間軸（各輪公告狀態）
 * - 預算+押標金+截止倒數
 * - 機關聯絡資訊卡片
 * - 投標參數
 * - 相關標案（同機關）
 *
 * @version 2.0.0 — ezbid 風格強化
 */
import React, { useMemo } from 'react';
import {
  Descriptions, Tag, Timeline, Card, Typography, Button, Space, Select, Popconfirm,
  Row, Col, Statistic, Empty, Alert,
} from 'antd';
import {
  BankOutlined, PhoneOutlined, MailOutlined, DollarOutlined,
  CalendarOutlined, LinkOutlined, EnvironmentOutlined,
  ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined,
  StarOutlined, StarFilled, UnorderedListOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { BattleTab, PriceTab } from './tenderDetail';
import { useParams, useNavigate } from 'react-router-dom';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';
import { useTenderDetail, useTenderDetailFull, useTenderBookmarks, useCreateBookmark, useUpdateBookmark, useDeleteBookmark } from '../hooks/business/useTender';
import { tenderApi } from '../api/tenderApi';
import { App } from 'antd';

const { Text, Paragraph } = Typography;

/** 計算剩餘天數 */
function daysRemaining(deadline: string | undefined): number | null {
  if (!deadline) return null;
  // 支援 "115/04/07" (ROC) 或 "2026-04-07" 格式
  let dateStr = deadline;
  const rocMatch = deadline?.match(/^(\d{2,3})\/(\d{2})\/(\d{2})/);
  if (rocMatch) {
    const y = parseInt(rocMatch[1]!) + 1911;
    dateStr = `${y}-${rocMatch[2]}-${rocMatch[3]}`;
  }
  const target = new Date(dateStr);
  if (isNaN(target.getTime())) return null;
  const diff = Math.ceil((target.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  return diff;
}

/** 時間軸節點顏色 */
function getTimelineColor(type: string): string {
  if (type.includes('決標')) return 'green';
  if (type.includes('無法決標') || type.includes('廢標')) return 'red';
  if (type.includes('更正')) return 'orange';
  return 'blue';
}

const TenderDetailPage: React.FC = () => {
  const { unitId, jobNumber } = useParams<{ unitId: string; jobNumber: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const uid = unitId ? decodeURIComponent(unitId) : null;
  const jn = jobNumber ? decodeURIComponent(jobNumber) : null;
  const isEzbidOnly = uid && !jn;

  const { data: detail, isLoading } = useTenderDetail(uid, jn || null);
  const { data: fullData } = useTenderDetailFull(isEzbidOnly ? null : uid, isEzbidOnly ? null : jn);
  const { data: allBookmarks } = useTenderBookmarks();
  const bookmarkMutation = useCreateBookmark();
  const updateBmMutation = useUpdateBookmark();
  const deleteBmMutation = useDeleteBookmark();

  const currentBookmark = useMemo(() => {
    if (!allBookmarks || !unitId || !jobNumber) return null;
    const uid = decodeURIComponent(unitId);
    const jn = decodeURIComponent(jobNumber);
    return allBookmarks.find(b => b.unit_id === uid && b.job_number === jn) ?? null;
  }, [allBookmarks, unitId, jobNumber]);

  // Merge all event details — 決標公告 and 招標公告 have different fields
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const merged = (detail as any)?.merged_detail as Record<string, string> | undefined;
  const rawLatest = detail?.latest?.detail;
  // Use rawLatest first, fill gaps from merged (cross-event)
  const latest = rawLatest
    ? Object.fromEntries(
        Object.keys(rawLatest).map(k => [k, (rawLatest as Record<string, string>)[k] || merged?.[k] || ''])
      ) as typeof rawLatest
    : (merged as typeof rawLatest);
  const days = useMemo(() => daysRemaining(latest?.deadline), [latest?.deadline]);

  if (!detail && !isLoading) {
    return (
      <DetailPageLayout
        header={{ title: '查無此標案', backPath: '/tender/search' }}
        tabs={[createTabItem('empty', { icon: <ClockCircleOutlined />, text: '說明' },
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">PCC 開放資料中查無此標案</Text>
            {uid && (
              <div style={{ marginTop: 16 }}>
                <Button type="primary" onClick={() => window.open(`https://cf.ezbid.tw/tender/${uid}`, '_blank')}>
                  在 ezbid 查看此標案 →
                </Button>
              </div>
            )}
          </div>
        )]}
        hasData={false}
      />
    );
  }

  // ========== Tab 1: 標案總覽 ==========
  const overviewTab = createTabItem('overview', { icon: <DollarOutlined />, text: '標案總覽' },
    latest ? (
      <div>
        {/* 倒數 + 狀態 Banner */}
        {days !== null && days >= 0 && (
          <Alert
            type="warning"
            showIcon
            icon={<ClockCircleOutlined />}
            title={`截止投標倒數 ${days} 天`}
            description={`截止時間: ${latest.deadline}`}
            style={{ marginBottom: 16 }}
          />
        )}
        {days !== null && days < 0 && (
          <Alert type="info" showIcon title="投標已截止" style={{ marginBottom: 16 }} />
        )}

        {/* 關鍵數字 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          {latest.budget && (
            <Col xs={12} sm={8} lg={6}>
              <Card size="small" style={{ borderLeft: '4px solid #1890ff' }}>
                <Statistic title="預算金額" value={latest.budget.replace('元', '')} prefix={<DollarOutlined />}
                  styles={{ content: { fontSize: 22, color: '#1890ff' } }} />
              </Card>
            </Col>
          )}
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" style={{ borderLeft: '4px solid #52c41a' }}>
              <Statistic title="招標方式" value={latest.method || '-'}
                styles={{ content: { fontSize: 14 } }} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" style={{ borderLeft: '4px solid #faad14' }}>
              <Statistic title="決標方式" value={latest.award_method || '-'}
                styles={{ content: { fontSize: 14 } }} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" style={{ borderLeft: latest.status?.includes('招標中') ? '4px solid #52c41a' : '4px solid #d9d9d9' }}>
              <Statistic title="狀態" value={latest.status || '-'}
                styles={{ content: { fontSize: 14, color: latest.status?.includes('招標中') ? '#52c41a' : undefined } }} />
            </Card>
          </Col>
        </Row>

        {/* 機關聯絡 */}
        <Card title={<><BankOutlined /> 招標機關</>} size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="機關名稱"><Text strong>{latest.agency_name}</Text></Descriptions.Item>
            <Descriptions.Item label="承辦單位">{latest.agency_unit || '-'}</Descriptions.Item>
            <Descriptions.Item label={<><PhoneOutlined /> 聯絡人</>}>{latest.contact_person} {latest.contact_phone}</Descriptions.Item>
            <Descriptions.Item label={<><MailOutlined /> Email</>}>{latest.contact_email || '-'}</Descriptions.Item>
            <Descriptions.Item label={<><EnvironmentOutlined /> 地址</>} span={2}>{latest.agency_address || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 採購資訊 */}
        <Card title="採購資訊" size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="標案案號"><Text copyable>{detail?.job_number}</Text></Descriptions.Item>
            <Descriptions.Item label="標的分類">{latest.procurement_type || '-'}</Descriptions.Item>
            <Descriptions.Item label="公告日">{latest.announce_date || '-'}</Descriptions.Item>
            <Descriptions.Item label="截止投標"><Text type={days !== null && days <= 3 ? 'danger' : undefined} strong>{latest.deadline || '-'}</Text></Descriptions.Item>
            <Descriptions.Item label="開標日期">{latest.open_date || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 操作按鈕 */}
        <Space>
          {latest.pcc_url && (
            <Button type="primary" icon={<LinkOutlined />} href={latest.pcc_url} target="_blank">
              政府採購網原始頁面
            </Button>
          )}
          {currentBookmark ? (
            <Space.Compact>
              <Button icon={<StarFilled style={{ color: '#faad14' }} />} type="text">
                已收藏
              </Button>
              <Select
                size="small"
                value={currentBookmark.status}
                style={{ width: 100 }}
                onChange={async (status) => {
                  try {
                    await updateBmMutation.mutateAsync({ id: currentBookmark.id, status });
                    message.success(`狀態更新: ${status}`);
                  } catch { message.error('更新失敗'); }
                }}
                options={[
                  { value: 'tracking', label: '追蹤中' },
                  { value: 'applied', label: '已投標' },
                  { value: 'won', label: '得標' },
                  { value: 'lost', label: '未得標' },
                ]}
              />
              <Popconfirm title="取消收藏？" onConfirm={async () => {
                try { await deleteBmMutation.mutateAsync(currentBookmark.id); message.success('已取消收藏'); } catch { message.error('失敗'); }
              }}>
                <Button icon={<DeleteOutlined />} size="small" danger type="text" />
              </Popconfirm>
            </Space.Compact>
          ) : (
            <Button icon={<StarOutlined />} onClick={async () => {
              try {
                await bookmarkMutation.mutateAsync({
                  unit_id: decodeURIComponent(unitId || ''),
                  job_number: decodeURIComponent(jobNumber || ''),
                  title: detail?.title || '',
                  unit_name: detail?.unit_name || '',
                  budget: latest?.budget,
                  deadline: latest?.deadline,
                });
                message.success('已收藏');
              } catch { message.error('收藏失敗（可能已收藏）'); }
            }}>收藏此標案</Button>
          )}
          <Button onClick={async () => {
            const uid = decodeURIComponent(unitId || '');
            const jn = decodeURIComponent(jobNumber || '');
            const t = detail?.title || '';
            if (!uid || !jn || !t) { message.warning('標案資訊不完整'); return; }
            try {
              const result = await tenderApi.createCase({
                unit_id: uid,
                job_number: jn,
                title: t,
                unit_name: detail?.unit_name || '',
                budget: latest?.budget || undefined,
              });
              message.success(result.message);
            } catch { message.error('建案失敗'); }
          }}>一鍵建案</Button>
        </Space>
      </div>
    ) : <Empty />
  );

  // ========== Tab 2: 生命週期 ==========
  const lifecycleTab = createTabItem('lifecycle', { icon: <CalendarOutlined />, text: '生命週期', count: detail?.events?.length },
    <div>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        標案從公告到決標的完整歷程，每個節點代表一次公告或決標事件。
      </Paragraph>
      <Timeline
        mode="left"
        items={(detail?.events ?? []).map((evt, i) => {
          const color = getTimelineColor(evt.type);
          const icon = evt.type.includes('決標')
            ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
            : evt.type.includes('無法決標')
              ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
              : undefined;
          return {
            key: i,
            color,
            dot: icon,
            label: evt.date ? String(evt.date) : '',
            children: (
              <Card size="small" style={{ marginBottom: 4 }}>
                <Tag color={color}>{evt.type}</Tag>
                <Text>{evt.title}</Text>
                {evt.companies.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">廠商: </Text>
                    {evt.companies.map((c, j) => <Tag key={j} color="green" style={{ cursor: 'pointer' }} onClick={() => navigate(`/tender/company-profile?q=${encodeURIComponent(c)}`)}>{c}</Tag>)}
                  </div>
                )}
              </Card>
            ),
          };
        })}
      />
    </div>
  );

  // ========== Tab 3: 投標/得標 ==========
  const companiesTab = createTabItem('companies', { icon: <BankOutlined />, text: '投標/得標' },
    <div>
      {(detail?.events ?? []).filter(e => e.companies.length > 0).length === 0 ? (
        <Empty description="尚無投標/得標紀錄" />
      ) : (
        (detail?.events ?? []).filter(e => e.companies.length > 0).map((evt, i) => (
          <Card key={i} size="small" title={<><Tag color={getTimelineColor(evt.type)}>{evt.type}</Tag> {evt.date}</>} style={{ marginBottom: 8 }}>
            <Space wrap>
              {evt.companies.map((c, j) => <Tag key={j} color="blue" style={{ cursor: 'pointer' }} onClick={() => navigate(`/tender/company-profile?q=${encodeURIComponent(c)}`)}>{c}</Tag>)}
            </Space>
          </Card>
        ))
      )}
    </div>
  );

  // ========== Tab 4: 投標戰情 ==========
  const battleTab = createTabItem('battle', { icon: <UnorderedListOutlined />, text: '投標戰情' },
    <BattleTab
      battleRoom={fullData?.battle_room}
      orgEcosystem={fullData?.org_ecosystem}
      unitName={detail?.unit_name}
    />
  );

  // ========== Tab 5: 底價分析 ==========
  const priceTab = createTabItem('price', { icon: <DollarOutlined />, text: '底價分析' },
    <PriceTab
      priceAnalysis={fullData?.price_analysis}
      priceEstimate={fullData?.price_estimate}
    />
  );

  return (
    <DetailPageLayout
      header={{
        title: detail?.title ?? '載入中...',
        backPath: '/tender/search',
        subtitle: `${detail?.unit_name ?? ''} | ${detail?.job_number ?? ''}`,
      }}
      tabs={[overviewTab, lifecycleTab, companiesTab, battleTab, priceTab]}
      loading={isLoading}
      hasData={!!detail}
    />
  );
};

export default TenderDetailPage;
