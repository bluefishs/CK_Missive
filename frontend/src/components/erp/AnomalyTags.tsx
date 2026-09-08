/**
 * 金流異常標籤 ＋ 判讀（解除待辦）
 *
 * ⭐ 2026-09-08 owner：「5 筆的『已收 17,850』已付清、發票多開 ——
 * 是否異常案件標註機制並增列篩選查詢，以利解除或處理異常費用之案件機制」。
 * ⭐ 2026-09-09 owner：「問題錯誤如何標注與顯示，以利明確檢視解除或處理異常紀錄案件」
 *   —— 首版把「為什麼異常／差多少」藏在滑鼠懸停的提示裡，手機上根本點不出來，
 *   詳情頁也沒有任何異常區塊。這版：列表標籤下方直接印差額、手機卡片帶標籤、
 *   詳情頁分頁上方有一塊 AnomalyPanel 把每一條異常攤開（原因、差額、判讀／退回按鈕）。
 *
 * ⚠️ 這裡**不判斷什麼算異常** —— 判準的唯一定義在後端
 * `app/services/erp/finance_anomaly.py`。前端抄一份就是第二份宣告，
 * 而那正是本 repo 反覆出事的形狀（L145 家族）。
 *
 * ⚠️ 「判讀」解除的是**待辦**不是事實：判讀後標籤仍在（轉灰、標「已判讀」），
 * 因為數字還是那樣。若判讀會讓標籤消失，這個機制就變成
 * 「一鍵讓問題從畫面上消失」—— 比沒有這個機制更糟。
 */
import React, { useState } from 'react';
import { Tag, Tooltip, Space, Modal, Input, App, Typography, Alert, Button } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { extractApiMessage } from '../../utils/apiMessage';
import type { FinanceAnomaly } from '../../types/erp';
import { anomalyTagColor, anomalyTagText } from './anomalyTag';

const { Text } = Typography;

/** 判讀／退回的共用邏輯 —— 列表標籤與詳情面板都用它，不各寫一份 */
function useAnomalyAck(quotationId: number) {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [target, setTarget] = useState<FinanceAnomaly | null>(null);
  const [reason, setReason] = useState('');
  const invalidate = () => {
    // 列表（erp-quotations）與詳情（erp-quotation…）都要重抓：判讀在哪一頁做，另一頁也要跟著變
    qc.invalidateQueries({ predicate: (q) => String(q.queryKey[0] ?? '').startsWith('erp-quotation') });
    qc.invalidateQueries({ queryKey: ['erp-anomalies'] });
  };
  const ack = useMutation({
    mutationFn: (v: { code: string; reason: string }) =>
      apiClient.post('/erp/anomalies/ack', {
        quotation_id: quotationId, anomaly_type: v.code, reason: v.reason,
      }),
    onSuccess: () => { message.success('已記錄判讀'); setTarget(null); setReason(''); invalidate(); },
    onError: (e) => message.error(extractApiMessage(e, '記錄判讀失敗')),
  });
  const unack = useMutation({
    mutationFn: (code: string) =>
      apiClient.post('/erp/anomalies/unack', { quotation_id: quotationId, anomaly_type: code }),
    onSuccess: () => { message.success('已退回待處理'); invalidate(); },
    onError: (e) => message.error(extractApiMessage(e, '退回失敗')),
  });
  const modal = (
    <Modal
      title={`判讀：${target?.label ?? ''}`}
      open={!!target}
      onCancel={() => setTarget(null)}
      okText="記錄判讀"
      confirmLoading={ack.isPending}
      okButtonProps={{ disabled: reason.trim().length < 2 }}
      onOk={() => target && ack.mutate({ code: target.code, reason: reason.trim() })}
    >
      <p style={{ marginTop: 0 }}>{target?.detail}</p>
      <p><Text type="secondary">{target?.explain}</Text></p>
      {/* 原因必填：沒有原因的判讀等於把問題藏起來，下一個人看到「已判讀」
          卻不知道當初判了什麼，只能再判一次。 */}
      <Input.TextArea
        rows={3}
        maxLength={500}
        showCount
        placeholder="判讀原因（必填）——例：已付清，發票多開 840 元屬追加項目，客戶同意不另補請款"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <p style={{ marginBottom: 0, marginTop: 8 }}>
        <Text type="secondary">
          判讀不會更動任何金額 —— 數字仍然是現在這樣，只是這一筆從「待處理」移到「已判讀」。
        </Text>
      </p>
    </Modal>
  );
  return { ack, unack, setTarget, setReason, modal };
}

interface Props {
  quotationId: number;
  anomalies?: FinanceAnomaly[];
  /** 唯讀（例如列表只想顯示不想給操作） */
  readOnly?: boolean;
  /** 標籤下方直接印差額說明（列表用；手機沒有 hover，藏在 Tooltip 裡等於沒有） */
  showDetail?: boolean;
}

export const AnomalyTags: React.FC<Props> = ({ quotationId, anomalies, readOnly, showDetail }) => {
  const { unack, setTarget, setReason, modal } = useAnomalyAck(quotationId);

  if (!anomalies?.length) return <Text type="secondary">—</Text>;

  return (
    <>
      <Space size={[4, 4]} wrap onClick={(e) => e.stopPropagation()}>
        {anomalies.map((a) => (
          <Tooltip
            key={a.code}
            title={
              <div>
                <div>{a.explain}</div>
                <div style={{ marginTop: 4 }}>{a.detail}</div>
                {a.acknowledged && a.ack && (
                  <div style={{ marginTop: 4 }}>
                    已判讀：{a.ack.reason}
                    {a.ack.acked_by ? `（${a.ack.acked_by}）` : ''}
                  </div>
                )}
                {!readOnly && <div style={{ marginTop: 4 }}>點擊{a.acknowledged ? '退回待處理' : '記錄判讀'}</div>}
              </div>
            }
          >
            <span style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start' }}>
              <Tag
                color={anomalyTagColor(a)}
                style={{ margin: 0, cursor: readOnly ? 'default' : 'pointer' }}
                onClick={readOnly ? undefined : () => {
                  if (a.acknowledged) unack.mutate(a.code);
                  else { setTarget(a); setReason(''); }
                }}
              >
                {anomalyTagText(a)}
              </Tag>
              {showDetail && (
                <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.3, marginTop: 2 }}>{a.detail}</Text>
              )}
            </span>
          </Tooltip>
        ))}
      </Space>
      {!readOnly && modal}
    </>
  );
};

const ackSuffix = (ack: NonNullable<FinanceAnomaly['ack']>): string => {
  const who = ack.acked_by ?? '';
  const when = ack.acked_at ? String(ack.acked_at).slice(0, 10) : '';
  const parts = [who, when].filter(Boolean);
  return parts.length ? `（${parts.join('，')}）` : '';
};

/**
 * 詳情頁的異常面板：每一條異常一張 Alert，把「哪裡不對／差多少／為什麼算異常／誰判讀過、理由」
 * 全部攤開，並給「記錄判讀」／「退回待處理」按鈕。沒有異常時不渲染（詳情頁不需要「—」）。
 */
export const AnomalyPanel: React.FC<{ quotationId: number; anomalies?: FinanceAnomaly[] }> = ({ quotationId, anomalies }) => {
  const { unack, setTarget, setReason, modal } = useAnomalyAck(quotationId);
  if (!anomalies?.length) return null;
  const open = anomalies.filter((a) => !a.acknowledged).length;
  return (
    <div style={{ marginBottom: 12 }}>
      <Alert
        type={open ? 'error' : 'info'}
        showIcon
        style={{ marginBottom: 8 }}
        message={open ? `金流異常 ${open} 項待處理（共 ${anomalies.length} 項）` : `金流異常 ${anomalies.length} 項，皆已判讀`}
        description="異常由目前的請款、收款、發票、合約金額推導，不是人工旗標；補開發票或修正請款後會自動消失。判讀只把它移出待處理，不改任何金額。"
      />
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {anomalies.map((a) => (
          <Alert
            key={a.code}
            type={a.acknowledged ? 'info' : a.severity === 'red' ? 'error' : 'warning'}
            showIcon
            message={<span><b>{a.label}</b><span style={{ marginInlineStart: 8 }}>{a.detail}</span></span>}
            description={
              <div>
                <div>{a.explain}</div>
                {a.acknowledged && a.ack && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">已判讀：{a.ack.reason}{ackSuffix(a.ack)}</Text>
                  </div>
                )}
              </div>
            }
            action={
              a.acknowledged
                ? <Button size="small" onClick={() => unack.mutate(a.code)} loading={unack.isPending}>退回待處理</Button>
                : <Button size="small" type="primary" danger={a.severity === 'red'} onClick={() => { setTarget(a); setReason(''); }}>記錄判讀</Button>
            }
          />
        ))}
      </Space>
      {modal}
    </div>
  );
};

export default AnomalyTags;
