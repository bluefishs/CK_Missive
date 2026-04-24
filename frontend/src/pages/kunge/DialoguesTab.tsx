/**
 * 坤哥 — 對話精選板塊
 *
 * 展示代表性的深度對話片段，對齊 Muse「凌晨對話」風格。
 * 類別覆蓋業務 4 大面向：公文 / 案件 / 財務 / 反思。
 *
 * 未來擴充：從 agent_query_traces 中以 LLM 打分，自動挑選高品質對話。
 * 目前（v5.8.0 啟動階段）用靜態精選 + 連結到 Memory Wiki 看完整 diary。
 *
 * @version 1.0.0 — D5-B 填充
 */

import React from 'react';
import { Card, Typography, Tag, Space, Button, Row, Col } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  MessageOutlined,
  FileTextOutlined,
  ProjectOutlined,
  DollarOutlined,
  BulbOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

interface Dialogue {
  category: string;
  icon: React.ReactNode;
  color: string;
  question: string;
  answerHighlight: string;
  reflection: string;
  traceDate?: string;
}

const DIALOGUES: Dialogue[] = [
  {
    category: '公文',
    icon: <FileTextOutlined />,
    color: 'blue',
    question: '桃園市政府的來文有幾封？',
    answerHighlight:
      '搜尋 `search_documents` 配 agency=桃園市政府 → 聚合 `get_statistics` 得到該機關年度分佈；回覆引用 doc_number 讓主事者可深入查對。',
    reflection: '訊息最怕「好像很多」或「印象中有」的模糊表達 — 數字 + 清單才是信任的基礎。',
    traceDate: '2026-04-19 晨報',
  },
  {
    category: '案件',
    icon: <ProjectOutlined />,
    color: 'green',
    question: '最近的查估派工案件有哪些？',
    answerHighlight:
      '工具鏈 `[search_dispatch_orders, search_projects, get_statistics]` — 派工+案件+總量三角校對；回覆按最新更新排序。',
    reflection: '此 pattern 目前 hit=9（已進結晶候選），批准後將加速未來類似查詢路由。',
    traceDate: '2026-04-20 baseline',
  },
  {
    category: '財務',
    icon: <DollarOutlined />,
    color: 'orange',
    question: '哪些案件有未開票金額？請提供金額統計。',
    answerHighlight:
      '`get_financial_summary` 聚合未開票 + 分段清單；警示未請款超過 90 天的節點。嚴守倫理紅線「財務數字絕不杜撰」— 查不到即回查不到。',
    reflection: '財務場景的 pattern 還未累積到結晶門檻；需要更多真實使用累積。',
  },
  {
    category: '反思',
    icon: <BulbOutlined />,
    color: 'purple',
    question: 'baseline 為何 80% timeout？',
    answerHighlight:
      '追 log 發現 40-60 秒無任何 tool_start/tool_end 訊號 — silent gap。根因：工具執行無 observability 埋點。修復：加 `logger.info` 標記起訖與 elapsed。',
    reflection: '這是坤哥對自己的誠實診斷 — 異常即訊號，不是需要掩蓋的噪音。D2-A 修完後 baseline 成功率預計升到 80%+。',
    traceDate: '2026-04-20 Loop 驗證',
  },
];

export const DialoguesTab: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div>
      <Card bordered={false}>
        <Title level={3} style={{ marginTop: 0 }}>
          <MessageOutlined /> 對話精選
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 15 }}>
          代表性的深度對話片段 — 展示坤哥如何用工具鏈回答業務問題，
          以及當系統出現異常時如何誠實診斷。
        </Paragraph>
      </Card>

      <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
        {DIALOGUES.map((d, i) => (
          <Col xs={24} md={12} key={i}>
            <Card
              size="small"
              style={{ height: '100%', borderLeft: `3px solid var(--ant-color-${d.color})` }}
              title={
                <Space>
                  <span style={{ color: `var(--ant-color-${d.color})` }}>{d.icon}</span>
                  <Text strong>{d.category}</Text>
                  {d.traceDate && (
                    <Tag color={d.color} style={{ marginLeft: 4 }}>
                      {d.traceDate}
                    </Tag>
                  )}
                </Space>
              }
            >
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>Q</Text>
                  <Paragraph
                    style={{ margin: '2px 0 0 0', fontWeight: 500 }}
                  >
                    {d.question}
                  </Paragraph>
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>A 摘要</Text>
                  <Paragraph style={{ margin: '2px 0 0 0', fontSize: 13 }}>
                    {d.answerHighlight}
                  </Paragraph>
                </div>
                <div
                  style={{
                    background: '#fafafa',
                    padding: 8,
                    borderRadius: 4,
                    borderLeft: '2px solid #d9d9d9',
                  }}
                >
                  <Text type="secondary" style={{ fontSize: 12 }}>坤哥反思</Text>
                  <Paragraph
                    italic
                    style={{ margin: '2px 0 0 0', fontSize: 13, color: '#666' }}
                  >
                    {d.reflection}
                  </Paragraph>
                </div>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Card bordered={false} style={{ marginTop: 16, textAlign: 'center' }}>
        <Space direction="vertical" size={8}>
          <Paragraph italic type="secondary" style={{ margin: 0 }}>
            「不是取代思考，是幫助全觀。」
          </Paragraph>
          <Space>
            <Button type="primary" onClick={() => navigate('/kunge/chat')}>
              和坤哥對話 <ArrowRightOutlined />
            </Button>
            <Button onClick={() => navigate('/ai/memory')}>
              看完整 diary
            </Button>
          </Space>
        </Space>
      </Card>
    </div>
  );
};

export default DialoguesTab;
