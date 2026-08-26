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
  Descriptions, Tag, Timeline, Card, Typography, Button, Space,
  Row, Col, Statistic, Empty, Alert,
} from 'antd';
import {
  BankOutlined, PhoneOutlined, MailOutlined, DollarOutlined,
  CalendarOutlined, LinkOutlined, EnvironmentOutlined,
  ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { BattleTab, PriceTab } from './tenderDetail';
import { toCaseInput } from './tenderDetail/useCreateCaseFlow';
import { TenderActionBar } from './tenderDetail/TenderActionBar';
import { useParams, useNavigate } from 'react-router-dom';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';
import { useTenderDetail, useTenderDetailFull, useTenderBookmarks, useCreateBookmark, useUpdateBookmark, useDeleteBookmark } from '../hooks/business/useTender';
import { isEzbidDetail, isPccDetail } from '../types/tender';

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
  // ADR-0032: 支援兩種 URL 格式
  //   /tender/pcc/:unitId/:jobNumber (PCC)
  //   /tender/ezbid/:ezbidId (ezbid)
  const { unitId, jobNumber, ezbidId } = useParams<{
    unitId?: string; jobNumber?: string; ezbidId?: string;
  }>();
  const navigate = useNavigate();
  const uid = ezbidId
    ? decodeURIComponent(ezbidId)
    : (unitId ? decodeURIComponent(unitId) : null);
  const jn = jobNumber ? decodeURIComponent(jobNumber) : null;
  const isEzbidOnly = !!ezbidId;

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

  // ADR-0032: 以 type guard 明確分派 PCC / ezbid 資料來源
  const pccDetail = isPccDetail(detail) ? detail : null;
  const ezbidData = isEzbidDetail(detail) ? detail : null;

  // PCC 決標公告 and 招標公告 have different fields — 以 merged_detail 互補
  const merged = pccDetail?.merged_detail;
  const rawLatest = pccDetail?.latest?.detail;
  const latest = rawLatest
    ? Object.fromEntries(
        Object.keys(rawLatest).map(k => [k, (rawLatest as Record<string, string>)[k] || merged?.[k] || ''])
      ) as typeof rawLatest
    : (merged as typeof rawLatest);
  const days = useMemo(() => daysRemaining(latest?.deadline), [latest?.deadline]);

  const isEzbidDbOnly = !!ezbidData;

  if (!detail && !isLoading) {
    // 2026-08-26（B4）：查不到時原本只說「PCC 開放資料中查無此標案」——
    // 兩個問題：① 這條路徑可能是 ezbid，來源就講錯了；② **沒說出真正的問題**。
    //
    // ezbid 的唯一鍵有兩種格式（實測 DB）：純數字 37,980 筆（舊）、
    // `{機關代碼}/{標案案號}` 含斜線 11,470 筆（08-02 站台改版後）。
    // 若使用者貼的是**只有機關代碼**（例如 `A.47.3`），它兩種都不是 ——
    // 而畫面給的「查無此標案」會被讀成「這筆資料不存在」，
    // 實際上是**編號少了一半**。那兩件事意思完全相反。
    const looksLikeOrgCodeOnly =
      isEzbidOnly && !!uid && !uid.includes('/') && !/^\d+$/.test(uid);
    return (
      <DetailPageLayout
        header={{
          title: looksLikeOrgCodeOnly ? '這個編號不完整' : '查無此標案',
          backPath: '/tender/search',
        }}
        tabs={[createTabItem('empty', { icon: <ClockCircleOutlined />, text: '說明' },
          <div style={{ textAlign: 'center', padding: 40 }}>
            {looksLikeOrgCodeOnly ? (
              <>
                <Alert
                  type="info"
                  showIcon
                  message={`「${uid}」看起來是機關代碼，不是標案編號`}
                  description="ezbid 的標案編號是「機關代碼／標案案號」兩段（例如 A.21.100.36/TH115144），或是一組純數字。只有機關代碼查不到單一標案 —— 請改用搜尋。"
                />
                <div style={{ marginTop: 16 }}>
                  <Button type="primary" onClick={() => navigate(`/tender/search?q=${encodeURIComponent(uid)}`)}>
                    用「{uid}」搜尋這個機關的標案 →
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Text type="secondary">
                  {isEzbidOnly ? 'ezbid 與本地資料庫中查無此標案' : 'PCC 開放資料中查無此標案'}
                </Text>
                {uid && (
                  <div style={{ marginTop: 16 }}>
                    {/* 08-02 站台改版後詳情頁是 `/detail/{機關}/{案號}`；
                        純數字是改版前的舊 id，仍走舊路徑。 */}
                    <Button type="primary" onClick={() => window.open(
                      uid.includes('/')
                        ? `https://ezbid.tw/detail/${uid}`
                        : `https://cf.ezbid.tw/tender/${uid}`,
                      '_blank')}>
                      在 ezbid 查看此標案 →
                    </Button>
                  </div>
                )}
              </>
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

        {/* 操作按鈕 — 2026-07-31 起與 ezbid 分支共用 TenderActionBar，
            避免兩處各寫一套而在順序/主次/功能上漂移（owner 以截圖指出的設計不一致）。 */}
        <TenderActionBar
          /* 2026-08-16：改用 toCaseInput 單一實作 —— 這裡原本自己寫一份而漏了
             `tender_id`，導致從 PCC 建的案件全部沒有來源標案回指。 */
          caseInput={toCaseInput(detail, { unitId, jobNumber }, latest?.budget)}
          externalUrl={latest.pcc_url}
          externalLabel="政府採購網原始頁面"
          currentBookmark={currentBookmark}
          bookmarkPayload={{
            unit_id: decodeURIComponent(unitId || ''),
            job_number: decodeURIComponent(jobNumber || ''),
            title: detail?.title || '',
            unit_name: detail?.unit_name || '',
            budget: latest?.budget,
            deadline: latest?.deadline,
          }}
          onCreateBookmark={(p) => bookmarkMutation.mutateAsync(p)}
          onUpdateBookmark={(p) => updateBmMutation.mutateAsync(p)}
          onDeleteBookmark={(id) => deleteBmMutation.mutateAsync(id)}
        />
      </div>
    ) : isEzbidDbOnly ? (
      /* 2026-04-24: ezbid-only 簡版檢視 — 無 PCC 細節（latest/events）但有基本欄位 */
      <div>
        <Alert
          type="info"
          showIcon
          message="此為 ezbid 來源標案"
          description="尚未從政府採購網 (PCC) 取得完整公告細節，以下顯示 ezbid 資料庫摘要。點擊下方按鈕可前往 ezbid 查看原始頁面。"
          style={{ marginBottom: 16 }}
        />
        {/* L51 (2026-05-28) ADR-0046 Phase 3 對應 PCC link 區塊 */}
        {ezbidData?.pcc_match && (
          <Alert
            type="success"
            showIcon
            message={
              <Space>
                <Text strong>已對應政府採購網 (PCC) 完整紀錄</Text>
                <Tag color="green">
                  信心 {ezbidData.pcc_match.confidence !== null
                    ? `${(ezbidData.pcc_match.confidence * 100).toFixed(0)}%`
                    : '—'}
                </Tag>
              </Space>
            }
            description={
              <Space direction="vertical" style={{ width: '100%' }} size={4}>
                <Text type="secondary">
                  此 ezbid 標案經 enrichment HIGH-confidence 自動 link
                  {ezbidData.pcc_match.matched_at
                    ? `（於 ${ezbidData.pcc_match.matched_at.slice(0, 10)} 對應）`
                    : ''}
                </Text>
                <Space>
                  <Button
                    type="primary"
                    icon={<LinkOutlined />}
                    onClick={() =>
                      navigate(
                        `/tender/pcc/${encodeURIComponent(ezbidData.pcc_match!.unit_id)}/${encodeURIComponent(ezbidData.pcc_match!.job_number)}`,
                      )
                    }
                  >
                    查看 PCC 完整詳情
                  </Button>
                  <Text type="secondary">
                    {ezbidData.pcc_match.unit_id} / {ezbidData.pcc_match.job_number}
                  </Text>
                </Space>
              </Space>
            }
            style={{ marginBottom: 16 }}
          />
        )}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          {ezbidData?.budget && (
            <Col xs={12} sm={8} lg={6}>
              <Card size="small" style={{ borderLeft: '4px solid #1890ff' }}>
                <Statistic title="預算金額" value={String(ezbidData.budget)} prefix={<DollarOutlined />}
                  styles={{ content: { fontSize: 22, color: '#1890ff' } }} />
              </Card>
            </Col>
          )}
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" style={{ borderLeft: '4px solid #52c41a' }}>
              <Statistic title="狀態" value={ezbidData?.status || '-'} styles={{ content: { fontSize: 14 } }} />
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={6}>
            <Card size="small" style={{ borderLeft: '4px solid #faad14' }}>
              <Statistic title="公告日" value={ezbidData?.announce_date || '-'} styles={{ content: { fontSize: 14 } }} />
            </Card>
          </Col>
        </Row>
        <Card title={<><BankOutlined /> 招標機關</>} size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="機關名稱" span={2}><Text strong>{ezbidData?.unit_name || '-'}</Text></Descriptions.Item>
            <Descriptions.Item label="ezbid ID"><Text copyable>{ezbidData?.unit_id}</Text></Descriptions.Item>
          </Descriptions>
        </Card>
        <TenderActionBar
          caseInput={toCaseInput(detail, { unitId, jobNumber })}
          externalUrl={ezbidData?.ezbid_url}
          externalLabel="在 ezbid 查看此標案"
          currentBookmark={currentBookmark}
          bookmarkPayload={{
            unit_id: ezbidData?.ezbid_id || '',
            job_number: ezbidData?.job_number || `ezbid:${ezbidData?.ezbid_id || ''}`,
            title: ezbidData?.title || '',
            unit_name: ezbidData?.unit_name || '',
            budget: ezbidData?.budget != null ? String(ezbidData.budget) : undefined,
          }}
          onCreateBookmark={(p) => bookmarkMutation.mutateAsync(p)}
          onUpdateBookmark={(p) => updateBmMutation.mutateAsync(p)}
          onDeleteBookmark={(id) => deleteBmMutation.mutateAsync(id)}
        />
      </div>
    ) : <Empty />
  );

  // ========== Tab 2: 生命週期 ==========
  const lifecycleTab = createTabItem('lifecycle', { icon: <CalendarOutlined />, text: '生命週期', count: pccDetail?.events?.length },
    <div>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        標案從公告到決標的完整歷程，每個節點代表一次公告或決標事件。
      </Paragraph>
      <Timeline
        mode="left"
        items={(pccDetail?.events ?? []).map((evt, i) => {
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
      {(pccDetail?.events ?? []).filter(e => e.companies.length > 0).length === 0 ? (
        <Empty description="尚無投標/得標紀錄" />
      ) : (
        (pccDetail?.events ?? []).filter(e => e.companies.length > 0).map((evt, i) => (
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
