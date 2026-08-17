/**
 * 我的待填報
 *
 * 2026-08-16 owner：「承攬報價案件對應填報人員通報管控」。
 *
 * 實測缺口：承攬案件 32 筆沒有合約金額、報價 23 筆沒有總價、
 * 核銷 7 筆卡在審核（其中 4 筆 16 天沒動）——
 * **毛利算得出來的只有 40/78**。
 *
 * 這些不是系統故障，是沒有人知道自己該去填。缺的欄位在畫面上只是一個空格，
 * 看起來像「還沒到」而不是「該做沒做」。這張卡就是要把它變成待辦。
 *
 * 刻意的取捨：
 *  · **0 項時整張不顯示** —— 沒事還占一塊版面，久了就會被略過
 *  · 每一項都可以直接點過去填，不是只告訴你有問題
 *  · 不顯示別人的缺口（那在 ERP 管理者頁），這裡只講「我的」
 */
import React from 'react';
import { Card, List, Tag, Typography, Skeleton } from 'antd';
import { FormOutlined, RightOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
// 型別 SSOT 在 types/erp.ts（規範 §3 同精神：同一型別只能有一份宣告）
import type { MyFilingGaps } from '../../types/erp';

const { Text } = Typography;

const KIND_COLOR: Record<string, string> = {
  承攬案件缺合約金額: 'red',
  報價缺總價: 'orange',
  核銷卡在審核: 'gold',
};

export const MyFilingGapsCard: React.FC = () => {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery<MyFilingGaps>({
    queryKey: ['my-filing-gaps'],
    queryFn: async () => {
      // apiClient.post<T> 回的就是 T（它已經取過 response.data），
      // 而後端外層還包著 SuccessResponse → 泛型要寫成 { data: ... }
      const res = await apiClient.post<{ data: MyFilingGaps }>(
        ERP_ENDPOINTS.FILING_GAPS_MINE, {},
      );
      return res?.data ?? { total: 0, active_total: 0, items: [] };
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return <Card size="small" style={{ marginBottom: 16 }}><Skeleton active paragraph={{ rows: 2 }} /></Card>;
  }
  // 只顯示執行中的 —— 2026-08-17：62 項缺口裡 44 項是已結案案件的歷史補登。
  // 卡片上掛一個「62」會讓人以為有 62 件急事，看兩天就不看了。
  const active = (data?.items ?? []).filter(i => i.active);
  const closedCount = (data?.total ?? 0) - active.length;
  if (!data || active.length === 0) return null;

  return (
    <Card
      size="small"
      style={{ marginBottom: 16, borderLeft: '4px solid #fa8c16' }}
      title={
        <span>
          <FormOutlined style={{ marginRight: 8 }} />
          我的待填報
          <Tag color="orange" style={{ marginLeft: 8 }}>{active.length}</Tag>
        </span>
      }
    >
      <List
        size="small"
        dataSource={active.slice(0, 8)}
        renderItem={(item) => (
          <List.Item
            style={{ cursor: 'pointer' }}
            onClick={() => navigate(item.url)}
            actions={[<RightOutlined key="go" style={{ color: '#bfbfbf' }} />]}
          >
            <List.Item.Meta
              title={
                <span>
                  <Tag color={KIND_COLOR[item.kind] ?? 'default'}>{item.kind}</Tag>
                  <Text strong>{item.ref}</Text>
                  {item.label && <Text type="secondary"> {item.label}</Text>}
                </span>
              }
              description={<Text type="secondary" style={{ fontSize: 12 }}>{item.detail}</Text>}
            />
          </List.Item>
        )}
      />
      {active.length > 8 && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          另有 {active.length - 8} 項
        </Text>
      )}
      {closedCount > 0 && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          （已結案案件的歷史補登 {closedCount} 項未列入，非急件）
        </Text>
      )}
    </Card>
  );
};

export default MyFilingGapsCard;
