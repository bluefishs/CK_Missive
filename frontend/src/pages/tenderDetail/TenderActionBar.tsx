/**
 * 標案詳情「操作按鈕列」— PCC 與 ezbid 共用單一實作（2026-07-31）
 *
 * 事故：owner 對照兩頁截圖指出設計不一致 ——
 *   PCC 頁：[政府採購網原始頁面(主要藍)] [收藏/狀態/刪除] [一鍵建案(次要)]
 *   ezbid 頁：[一鍵建案(主要藍)] [在 ezbid 查看(次要)]，且**完全沒有收藏**
 * 同一個動作在兩頁的視覺權重相反、順序相反、功能不對等。
 *
 * 根因與當日其他缺陷同型：**同一功能在兩個分支各寫一套**（改錯檔／漏改一邊家族）。
 * 治法不是把第二套調成跟第一套一樣（下次仍會漂移），而是**只留一套**。
 *
 * 統一後的設計規則：
 *   1. 主要動作 = 「一鍵建案」（這是系統要人做的事；外部連結只是參考資料）
 *   2. 次要 = 收藏群組 → 外部原始頁面（標籤依來源不同，行為一致）
 *   3. 兩個來源的按鈕**順序與型別完全相同**，只有標籤與資料來源不同
 */
import React from 'react';
import { Button, Space, Select, Popconfirm, App } from 'antd';
import {
  LinkOutlined, StarOutlined, StarFilled, DeleteOutlined, PlusOutlined,
} from '@ant-design/icons';
import { useCreateCaseFlow, type CreateCaseInput } from './useCreateCaseFlow';

const BOOKMARK_STATUS_OPTIONS = [
  { value: 'tracking', label: '追蹤中' },
  { value: 'applied', label: '已投標' },
  { value: 'won', label: '得標' },
  { value: 'lost', label: '未得標' },
];

export interface TenderBookmarkLike {
  id: number;
  status?: string;
}

export interface TenderActionBarProps {
  /** 建案所需資訊（兩個來源各自組好後傳入） */
  caseInput: CreateCaseInput;
  /** 外部原始頁面 */
  externalUrl?: string | null;
  externalLabel: string;
  /** 收藏 */
  currentBookmark?: TenderBookmarkLike | null;
  bookmarkPayload: {
    unit_id: string; job_number: string; title: string;
    unit_name?: string; budget?: string; deadline?: string;
  };
  onCreateBookmark: (payload: TenderActionBarProps['bookmarkPayload']) => Promise<unknown>;
  onUpdateBookmark: (params: { id: number; status: string }) => Promise<unknown>;
  onDeleteBookmark: (id: number) => Promise<unknown>;
}

export const TenderActionBar: React.FC<TenderActionBarProps> = ({
  caseInput, externalUrl, externalLabel,
  currentBookmark, bookmarkPayload,
  onCreateBookmark, onUpdateBookmark, onDeleteBookmark,
}) => {
  const { message } = App.useApp();
  const { startCreateCase } = useCreateCaseFlow();

  return (
    <Space wrap>
      {/* 1. 主要業務動作 */}
      <Button type="primary" icon={<PlusOutlined />} onClick={() => startCreateCase(caseInput)}>
        一鍵建案
      </Button>

      {/* 2. 收藏（兩個來源都提供；ezbid 無 job_number 時以 ezbid:{id} 為識別碼，
             與建案查重同一套慣例，故 DB 的 NOT NULL 限制不需變更） */}
      {currentBookmark ? (
        <Space.Compact>
          <Button icon={<StarFilled style={{ color: '#faad14' }} />} type="text">已收藏</Button>
          <Select
            size="small"
            value={currentBookmark.status}
            style={{ width: 100 }}
            onChange={async (status) => {
              try {
                await onUpdateBookmark({ id: currentBookmark.id, status });
                message.success(`狀態更新: ${status}`);
              } catch { message.error('更新失敗'); }
            }}
            options={BOOKMARK_STATUS_OPTIONS}
          />
          <Popconfirm
            title="取消收藏？"
            onConfirm={async () => {
              try { await onDeleteBookmark(currentBookmark.id); message.success('已取消收藏'); }
              catch { message.error('失敗'); }
            }}
          >
            <Button icon={<DeleteOutlined />} size="small" danger type="text" />
          </Popconfirm>
        </Space.Compact>
      ) : (
        <Button
          icon={<StarOutlined />}
          onClick={async () => {
            try { await onCreateBookmark(bookmarkPayload); message.success('已收藏'); }
            catch { message.error('收藏失敗（可能已收藏）'); }
          }}
        >
          收藏此標案
        </Button>
      )}

      {/* 3. 外部參考 */}
      {externalUrl && (
        <Button icon={<LinkOutlined />} href={externalUrl} target="_blank">
          {externalLabel}
        </Button>
      )}
    </Space>
  );
};

export default TenderActionBar;
