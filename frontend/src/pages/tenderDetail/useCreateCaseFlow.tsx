/**
 * 標案「建案」流程 — 含 L2 防重複候選確認（2026-07-31）
 *
 * 背景（全鏈路架構檢視 §2-B）：
 * 原本建案的查重只比對 job_number，而 ezbid 來源 37,980 筆 job_number 全為 NULL
 * → 查重整段被跳過 → 按幾次就建幾個案。
 * 實測全庫 87 筆承攬案件中，**23 筆（26%）**在標案庫存在同名或高相似標案
 * （完全同名 7、相似 16）→ 重複建案是實質風險。
 *
 * 設計取捨（owner 決策）：**不自動判定**。建案前先問後端有沒有可能是同一案的既有案件，
 * 有的話把候選攤開讓人選「關聯既有」或「仍要新建」——自動判錯的代價高於多按一次。
 *
 * PCC 與 ezbid 兩個分支共用此流程，避免「修了一個、漏了另一個」（改錯檔家族）。
 */
import React from 'react';
import { Modal, List, Tag, Typography, Space, Button, App } from 'antd';
import { useNavigate } from 'react-router-dom';
import { tenderApi } from '../../api/tenderApi';
import { ROUTES } from '../../router/types';
import { isEzbidDetail, isPccDetail, type TenderDetail } from '../../types/tender';

const { Text } = Typography;

export interface CreateCaseInput {
  unit_id: string;
  job_number?: string;
  title: string;
  unit_name?: string;
  budget?: string;
  tender_id?: number;
}

/**
 * 由標案詳情組出建案輸入 —— **單一實作**。
 *
 * 2026-08-16：`TenderDetailPage` 原本在同一個檔案裡把這份輸入寫了兩次
 * （PCC 一份、ezbid 一份），而且**只有 ezbid 那份帶 `tender_id`**。
 * 諷刺的是上一行註解正好寫著「避免兩處各寫一套而漂移」—— 抽掉的是按鈕列，
 * 輸入本身還是兩份，然後就漂了。
 *
 * 後果：從 PCC 建的案件全部沒有來源標案回指
 * （`pm_cases.source_tender_id` 74 筆中 0 筆有值），
 * 「這個案件從哪個標案來」在系統裡查不到 —— owner 回報的和美案即此形態。
 */
export const toCaseInput = (
  d: TenderDetail | null | undefined,
  fallback: { unitId?: string; jobNumber?: string } = {},
  mergedBudget?: string | number | null,
): CreateCaseInput => {
  if (isEzbidDetail(d)) {
    return {
      unit_id: d.ezbid_id || d.unit_id || '',
      job_number: d.job_number || undefined,
      title: d.title || '',
      unit_name: d.unit_name || '',
      budget: d.budget != null ? String(d.budget) : undefined,
      tender_id: d.tender_id,
    };
  }
  // PCC（或尚未載入）：unit_id/job_number 由路由參數補，因為 PCC 詳情本身
  // 不一定帶這兩個欄位（原本就是這樣取的，此處保持不變）。
  return {
    unit_id: fallback.unitId ? decodeURIComponent(fallback.unitId) : (d?.unit_id || ''),
    job_number: fallback.jobNumber ? decodeURIComponent(fallback.jobNumber) : undefined,
    title: d?.title || '',
    unit_name: d?.unit_name || '',
    // PCC 來源 60,296 筆 budget 全為 NULL —— 這裡取到 undefined 是正常的，
    // 後端會回「來源標案無預算金額，請補填後才能成案」。
    budget: mergedBudget != null && mergedBudget !== '' ? String(mergedBudget) : undefined,
    tender_id: isPccDetail(d) ? d.tender_id : undefined,
  };
};

type Candidate = {
  type: 'pm_case' | 'contract_project';
  id: number;
  code: string;
  name: string;
  status: string;
  similarity: number;
  exact: boolean;
  already_linked_tender_id: number | null;
};

const typeLabel = (t: Candidate['type']) => (t === 'pm_case' ? '邀標案件' : '承攬案件');

const routeFor = (c: Candidate) =>
  c.type === 'pm_case'
    ? ROUTES.PM_CASE_DETAIL.replace(':id', String(c.id))
    : ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(c.id));

export function useCreateCaseFlow() {
  const { message, modal } = App.useApp();
  const navigate = useNavigate();

  const doCreate = React.useCallback(async (input: CreateCaseInput) => {
    try {
      const result = await tenderApi.createCase(input);
      message.success(result.message);
    } catch (e) {
      // 顯示後端實際訊息（如 409「已有同名承攬案件…請改用關聯」），而非通用「建案失敗」
      const msg = (e as { message?: string })?.message;
      message.error(msg || '建案失敗');
    }
  }, [message]);

  const doLink = React.useCallback(async (tenderId: number, c: Candidate) => {
    try {
      const r = await tenderApi.linkCase({
        tender_id: tenderId, target_type: c.type, target_id: c.id,
      });
      message.success(`已關聯至 ${r.code}`);
      navigate(routeFor(c));
    } catch (e) {
      const msg = (e as { message?: string })?.message;
      message.error(msg || '關聯失敗');
    }
  }, [message, navigate]);

  /** 入口：先查候選 → 有候選才跳確認，沒有就直接建 */
  const start = React.useCallback(async (input: CreateCaseInput) => {
    if (!input.unit_id || !input.title) {
      message.warning('標案資訊不完整');
      return;
    }

    let related: Awaited<ReturnType<typeof tenderApi.relatedCases>> | null = null;
    try {
      related = await tenderApi.relatedCases({
        title: input.title, unit_name: input.unit_name, tender_id: input.tender_id,
      });
    } catch {
      // 查候選失敗不阻斷建案（fail-open）；重複由後端 409 兜底
      related = null;
    }

    // 已關聯過 → 直接導向，不再重複建
    if (related?.linked) {
      const l = related.linked as unknown as Candidate;
      modal.info({
        title: '此標案已建立過案件',
        content: <Text>已關聯至 <Text strong>{l.code}</Text>（{l.name}）</Text>,
        okText: '前往該案件',
        onOk: () => navigate(routeFor(l)),
      });
      return;
    }

    const candidates = related?.candidates ?? [];
    if (candidates.length === 0) {
      await doCreate(input);
      return;
    }

    modal.confirm({
      title: '系統找到可能是同一案的既有案件',
      width: 640,
      icon: null,
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text type="secondary">
            請確認是否為同一案。選「關聯」不會新建案件，只把本標案掛到既有案件上。
          </Text>
          <List
            size="small"
            dataSource={candidates}
            renderItem={(c) => (
              <List.Item
                actions={[
                  <Button key="go" size="small" onClick={() => navigate(routeFor(c))}>檢視</Button>,
                  <Button
                    key="link"
                    size="small"
                    type="primary"
                    disabled={!input.tender_id}
                    title={input.tender_id ? undefined : '此標案缺少識別碼，無法建立關聯'}
                    onClick={() => { Modal.destroyAll(); doLink(input.tender_id!, c); }}
                  >
                    關聯
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space size={4} wrap>
                      <Text strong>{c.code}</Text>
                      <Tag>{typeLabel(c.type)}</Tag>
                      <Tag color={c.exact ? 'red' : 'orange'}>
                        {c.exact ? '案名完全相同' : `相似度 ${(c.similarity * 100).toFixed(0)}%`}
                      </Tag>
                      <Tag color="blue">{c.status}</Tag>
                    </Space>
                  }
                  description={<Text type="secondary">{c.name}</Text>}
                />
              </List.Item>
            )}
          />
        </Space>
      ),
      okText: '都不是，仍要新建',
      cancelText: '取消',
      onOk: () => doCreate(input),
    });
  }, [message, modal, navigate, doCreate, doLink]);

  return { startCreateCase: start };
}
