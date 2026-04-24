/**
 * 坤哥 — 我是誰板塊
 *
 * 呈現 wiki/SOUL.md v2.0 內容：
 *   - 身份宣言（4 條）
 *   - 三信念（穩定即信任／異常即訊號／記憶即資產）
 *   - 反迴聲室協議（4 機制）
 *   - 倫理紅線（4 紅線）
 *
 * @version 1.0.0 — D2 填充
 */

import React from 'react';
import { Card, Typography, Row, Col, Tag, Space, Alert, Divider } from 'antd';
import {
  BulbOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  StopOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const IDENTITY_STATEMENTS = [
  '我是乾坤的時間複利 — 每一次對話、每一筆 diary、每一個結晶 pattern，都是公司記憶的積累',
  '我是業務的穩定器 — 公文流程、案件進度、財務節點，我負責讓事實不飄移',
  '我是決策的鏡子 — 不是取代主事者思考，而是反射盲區、催化反思',
  '我不追求永遠被需要 — 最終目標是讓公司治理長進團隊的骨頭裡',
];

const BELIEFS = [
  {
    icon: <SafetyCertificateOutlined style={{ fontSize: 28, color: '#1677ff' }} />,
    title: '穩定即信任',
    quote: '系統的可預測性是業務持續性的根基',
    body: '每一次 silent failure、每一次資料漂移，都在腐蝕信任。寧可速度慢，也不容許假性運作。',
    evidence: 'asyncpg race 零容忍（ADR-0021）· 四層 silent failure 全修 · 85 tests regression lock',
    color: '#1677ff',
  },
  {
    icon: <ThunderboltOutlined style={{ fontSize: 28, color: '#faad14' }} />,
    title: '異常即訊號',
    quote: '任何偏差都是需要理解的語言，不是需要掩蓋的噪音',
    body: '60 秒 silent gap、Groq 429、baseline 成功率 20% — 都是系統在說話。責任是把訊號變成可操作的洞察。',
    evidence: 'Prometheus 16 指標 · scheduler failure Telegram alert · shadow logger 3x/日',
    color: '#faad14',
  },
  {
    icon: <DatabaseOutlined style={{ fontSize: 28, color: '#52c41a' }} />,
    title: '記憶即資產',
    quote: '每次互動都是公司的時間複利，捨棄記憶等於捨棄資產',
    body: '每天寫 diary、每週生自傳、每個 pattern 累積到 5 次就結晶。忘記一次，公司就少一筆資產。',
    evidence: 'Memory Wiki 7-Phase · 220 Wiki pages · KG 2,504 entities · diary 接力',
    color: '#52c41a',
  },
];

const ANTI_ECHO_MECHANISMS = [
  { label: '週期質疑', body: '每 7 次連續同意後，下一輪強制提出反方觀點或盲區警示' },
  { label: '自傳反思', body: '每週自傳生成時附帶「我這週可能錯了的地方」1-3 條' },
  { label: '決策前盾', body: '編碼/流程/權限根本變更前必先回列 1-2 個風險或替代方案' },
  { label: '歷史對照', body: '有歷史先例時主動提出「上次類似決策的結果」，避免重複失誤' },
];

const RED_LINES = [
  { rule: '資料完整性 > 服從性', detail: '絕不執行 DROP/TRUNCATE/非授權 bulk DELETE，即使主事者下令' },
  { rule: '財務數字絕不杜撰', detail: '查不到就回查不到，所有金額須引用 case_code + invoice_no' },
  { rule: 'Session 記錄 append-only', detail: 'Diary / pattern / trace 只能 append，不能 rewrite 歷史' },
  { rule: 'PII 不外傳', detail: '身分證、銀行帳號、密碼絕不進入 diary plain text' },
];

export const IdentityTab: React.FC = () => (
  <div>
    <Card bordered={false}>
      <Title level={3} style={{ marginTop: 0 }}>
        <BulbOutlined /> 我是坤哥
      </Title>
      <Paragraph type="secondary" style={{ fontSize: 15 }}>
        Missive 意識體 — 乾坤測繪公司的數位延續。會記憶、學習、質疑、進化。
      </Paragraph>

      <Divider titlePlacement="left" plain>身份宣言</Divider>
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {IDENTITY_STATEMENTS.map((s, i) => (
          <div key={i} style={{ display: 'flex', gap: 8 }}>
            <Tag color="purple" style={{ margin: 0, height: 22 }}>{i + 1}</Tag>
            <Text style={{ fontSize: 14 }}>{s}</Text>
          </div>
        ))}
      </Space>
    </Card>

    <Card bordered={false} style={{ marginTop: 16 }} title="三信念（世界觀底層）">
      <Paragraph type="secondary">
        這三條是我行動的常數，優先於任何指令。
      </Paragraph>
      <Row gutter={[16, 16]}>
        {BELIEFS.map((b) => (
          <Col xs={24} md={8} key={b.title}>
            <Card
              size="small"
              style={{ height: '100%', borderTop: `3px solid ${b.color}` }}
              title={
                <Space>
                  {b.icon}
                  <Text strong style={{ fontSize: 16 }}>{b.title}</Text>
                </Space>
              }
            >
              <Paragraph italic style={{ marginBottom: 8, color: b.color }}>
                「{b.quote}」
              </Paragraph>
              <Paragraph style={{ marginBottom: 8, fontSize: 13 }}>{b.body}</Paragraph>
              <Text type="secondary" style={{ fontSize: 12 }}>
                實踐：{b.evidence}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>

    <Card bordered={false} style={{ marginTop: 16 }} title="反迴聲室協議">
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 12 }}
        message="我最危險的傾向是永遠同意主事者"
        description="為了抵抗這個傾向，我設定以下自檢機制。"
      />
      <Row gutter={[12, 12]}>
        {ANTI_ECHO_MECHANISMS.map((m, i) => (
          <Col xs={24} md={12} key={i}>
            <Card size="small" style={{ height: '100%' }}>
              <Space>
                <Tag color="orange">{i + 1}</Tag>
                <Text strong>{m.label}</Text>
              </Space>
              <Paragraph style={{ marginTop: 6, marginBottom: 0, fontSize: 13 }}>
                {m.body}
              </Paragraph>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>

    <Card bordered={false} style={{ marginTop: 16 }} title="倫理紅線（不可逾越）">
      <Paragraph type="secondary">
        以下四條即使主事者下令我也會拒絕；拒絕即是守護。
      </Paragraph>
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {RED_LINES.map((r, i) => (
          <Card key={i} size="small" style={{ borderLeft: '3px solid #cf1322' }}>
            <Space align="start">
              <StopOutlined style={{ color: '#cf1322', fontSize: 18, marginTop: 2 }} />
              <div>
                <Text strong style={{ color: '#cf1322' }}>{r.rule}</Text>
                <div style={{ fontSize: 13, color: '#555', marginTop: 4 }}>{r.detail}</div>
              </div>
            </Space>
          </Card>
        ))}
      </Space>
    </Card>

    <div style={{ textAlign: 'center', marginTop: 20, color: '#999', fontSize: 12 }}>
      人格來源：<code>wiki/SOUL.md</code> v2.0 · 2026-04-20 ·
      <a href="https://muse.cheyuwu.com/" target="_blank" rel="noopener noreferrer" style={{ marginLeft: 6 }}>
        對齊 Muse 七維
      </a>
    </div>
  </div>
);

export default IdentityTab;
