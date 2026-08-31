/**
 * 我的案件待辦
 *
 * 2026-08-17 owner：「原儀表板對應使用者案件財務通知與管理機制很好，
 * 原目標就是逐步建立個人專案通報機制」＋「目前該機制消失了」。
 *
 * ⚠️ 它消失是我造成的：同一天做了三次收窄（核准停用不報卡審核／
 * 標案類不要求成本／只推執行中），每一次個別都對，
 * 但**疊起來把 owner 的 6 項清成 0**，而「0 項不顯示」讓整張卡消失。
 *
 * 更根本的是範圍：原本只涵蓋「**填報**缺口」，而 owner 要的是
 * 「案件財務通知與管理」—— 實測 owner 負責 5 個執行中案件、金額全部有填
 * （所以不在填報缺口裡），底下卻有 2 筆未收款、4 筆未付應付沒有人通知他。
 * 那不是「沒填」，是「該收沒收、該付沒付」——對案件負責人重要得多。
 *
 * 教訓：收窄判準時要問「移除後這個人還剩什麼」。
 * 通報機制的價值在於每個人打開都看得到自己的事，不在於清單短。
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
import React, { useMemo } from 'react';
import { Card, Tree, Tag, Typography, Skeleton } from 'antd';
import type { DataNode } from 'antd/es/tree';
import { FormOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
// 型別 SSOT 在 types/erp.ts（規範 §3 同精神：同一型別只能有一份宣告）
import type { MyFilingGaps } from '../../types/erp';

const { Text } = Typography;

const KIND_COLOR: Record<string, string> = {
  // 金額相關的排前面用紅／橙 —— 它們直接影響毛利與現金流
  // 2026-08-31 owner：「是否也須增列應請款機制」。實測執行中 100 案有 95 案
  // 從未開過請款單；逾一年未開單者 43 件、222 萬 —— 金額上比未付款大一個量級，
  // 所以排在最前面用 red。
  該請款未開單: 'red',
  承攬案件缺合約金額: 'red',
  請款未收款: 'volcano',
  應付未付款: 'orange',
  報價缺總價: 'gold',
  報價缺估列成本: 'gold',
  核銷卡在審核: 'blue',
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

  // ⭐ 2026-08-31 owner：「應依案件區分樹狀結構呈現，避免視窗記錄過長」。
  //
  // 依 `case_code` 分組 —— 那是跨模組的唯一橋樑（development-rules
  // §跨模組案號規範），報價、承攬、請款、應付都掛在同一個值上。
  // **不自造 group_id**：再造一個識別碼就是第二份事實。
  //
  // 標題顯示的編號用 `project_code`（成案編號），沒有才退回 `case_code`
  // —— 在此之前一律顯示 case_code，於是 136 筆已成案的案子在畫面上
  // 帶著 `_PM_` 看起來像未成案（owner 同日回報的正是這個）。
  //
  // 預設全部收合：owner 要的是「視窗不要過長」，展開一層就失去意義。
  const treeData = useMemo<DataNode[]>(() => {
    const active = (data?.items ?? []).filter(i => i.active);
    const groups = new Map<string, typeof active>();
    for (const it of active) {
      // case_code 理論上恆存在；真的沒有就用 ref 當退路，
      // 而不是丟進一個「其他」桶 —— 那會讓兩個不同案子看起來是同一個。
      const key = it.case_code || it.ref;
      const arr = groups.get(key);
      if (arr) arr.push(it); else groups.set(key, [it]);
    }
    return [...groups.entries()].map(([key, items]) => {
      const shown = items[0]?.project_code || key;
      const name = items.find(i => i.label)?.label ?? '';
      return {
        key,
        selectable: false,
        title: (
          <span>
            <Text strong>{shown}</Text>
            {name && <Text type="secondary" style={{ marginLeft: 6 }}>{name}</Text>}
            <Tag color="orange" style={{ marginLeft: 8 }}>{items.length}</Tag>
          </span>
        ),
        children: items.map((it, n) => ({
          key: `${key}#${n}`,
          isLeaf: true,
          title: (
            <span
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(it.url)}
            >
              <Tag color={KIND_COLOR[it.kind] ?? 'default'}>{it.kind}</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>{it.detail}</Text>
            </span>
          ),
        })),
      };
    });
  }, [data, navigate]);

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
          我的案件待辦
          <Tag color="orange" style={{ marginLeft: 8 }}>{active.length}</Tag>
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
            {treeData.length} 個案件
          </Text>
        </span>
      }
    >
      {/* 預設收合：點案件才展開它的缺口，清單不會一路往下長 */}
      <Tree treeData={treeData} blockNode selectable={false} />
      {closedCount > 0 && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          （已結案案件的歷史補登 {closedCount} 項未列入，非急件）
        </Text>
      )}
    </Card>
  );
};

export default MyFilingGapsCard;
