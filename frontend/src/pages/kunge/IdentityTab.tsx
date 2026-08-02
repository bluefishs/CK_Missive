/**
 * 坤哥 — 我是誰板塊
 *
 * ⚠️ 2026-08-02 改為讀 SSOT：
 * 本檔原本把「身份宣言／三信念／反迴聲室協議／倫理紅線」**硬編成前端靜態複本**，
 * 而 `wiki/SOUL.md` 才是 SSOT。複本必然隨時間脫節——實際已經發生：
 * evidence 欄位寫死「Prometheus 16 指標」「85 tests regression lock」，
 * 而現況分別是 9 類 metric 與不同的測試數；頁尾還標著「v2.0 · 2026-04-20」，
 * 但 SOUL.md 至今仍在被 weekly_autobiography_job 更新。
 *
 * 現在段落由 `MEMORY_ENDPOINTS.SOUL` 供應（後端用既有 SoulLoader 解析、含 mtime 快取），
 * 前端只負責渲染。SOUL.md 改了，這一頁就跟著改。
 *
 * @version 2.0.0 — 改讀 SSOT
 */

import React from 'react';
import { Card, Typography, Alert, Space, Skeleton, Result, Button } from 'antd';
import { HeartOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import { MEMORY_ENDPOINTS } from '../../api/endpoints';
import { MarkdownRenderer } from '../../components/common/MarkdownRenderer';

const { Title, Paragraph, Text } = Typography;

interface SoulSection {
  title: string;
  body: string;
}

interface SoulResp {
  success: boolean;
  error?: string;
  data?: {
    version: string;
    last_modified_by?: string;
    last_modified_at?: string;
    sections: SoulSection[];
    section_count: number;
  } | null;
}

/** 依段落標題給一點視覺區辨（純樣式，不影響內容來源） */
const SECTION_ACCENT: Record<string, string> = {
  身份宣言: '#1677ff',
  三信念: '#faad14',
  反迴聲室協議: '#722ed1',
  倫理紅線: '#cf1322',
};

const accentOf = (title: string): string => {
  const hit = Object.keys(SECTION_ACCENT).find((k) => title.startsWith(k));
  return (hit && SECTION_ACCENT[hit]) || '#d9d9d9';
};

export const IdentityTab: React.FC = () => {
  const { data, isLoading, isError, refetch, isFetching } = useQuery<SoulResp>({
    queryKey: ['kunge-soul'],
    queryFn: () => apiClient.post<SoulResp>(MEMORY_ENDPOINTS.SOUL, {}),
    staleTime: 10 * 60_000,
  });

  if (isLoading) {
    return (
      <Card bordered={false}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    );
  }

  // 讀不到 SOUL.md 時明講「讀不到」，不要渲染成空白——
  // 空白會被看成「這個人沒有信念」，與「檔案讀取失敗」是兩件完全不同的事。
  if (isError || !data?.success || !data.data) {
    return (
      <Result
        status="warning"
        title="讀不到人格定義"
        subTitle={data?.error ?? 'wiki/SOUL.md 無法載入。這不代表人格不存在，只代表這一頁取不到內容。'}
        extra={<Button icon={<ReloadOutlined />} onClick={() => refetch()} loading={isFetching}>重試</Button>}
      />
    );
  }

  const { version, last_modified_by, last_modified_at, sections } = data.data;

  return (
    <div>
      <Card bordered={false} style={{ marginBottom: 8 }}>
        <Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
          <HeartOutlined /> 我是誰
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 0 }}>
          以下內容直接來自 <code>wiki/SOUL.md</code>（人格的單一事實來源），
          不是這一頁自己存的複本——SOUL.md 改了，這裡就跟著改。
        </Paragraph>
      </Card>

      {sections.length === 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="SOUL.md 讀到了，但沒有找到預期的人格段落"
          description="可能是段落標題改過。請確認 wiki/SOUL.md 仍有「身份宣言／三信念／反迴聲室協議／倫理紅線」四段。"
        />
      )}

      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {sections.map((s) => (
          <Card
            key={s.title}
            title={s.title}
            size="small"
            style={{ borderLeft: `3px solid ${accentOf(s.title)}` }}
          >
            <MarkdownRenderer content={s.body} />
          </Card>
        ))}
      </Space>

      <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 16 }}>
        人格來源：<code>wiki/SOUL.md</code> v{version}
        {last_modified_at ? ` · 最後更新 ${last_modified_at}` : ''}
        {last_modified_by ? ` · by ${last_modified_by}` : ''}
        <br />
        <Text type="secondary">
          「我的成長」段落由 weekly_autobiography_job 自動追加，屬 agent-writable 區域。
        </Text>
      </Paragraph>
    </div>
  );
};

export default IdentityTab;
