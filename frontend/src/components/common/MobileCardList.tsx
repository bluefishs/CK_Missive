/**
 * MobileCardList —— 手機（< 768px）上把「一列」畫成「一張卡」。
 *
 * 2026-09-05 owner：「優先處理 RWD，現在多數都直接透過手機檢視」。
 * 表格在 390px 寬的手機上，9 欄擠成每欄 40px，金額被折成三行、案名剩兩個字——
 * 「窄了就藏欄位」只是讓它少壞一點。正解是換版面：手機不畫表格，畫卡片。
 *
 * 用法：`EnhancedTable` / `ResponsiveTable` 加 `mobileCard={(r) => <MobileCard … />}`，
 * 在 isMobile 時包裝元件會用本清單取代 <Table>，分頁與點列進詳情都保留。
 * 桌面與平板（≥ 768px）仍是表格，一份資料兩種版面，不另做手機版頁面。
 *
 * 卡片結構固定四段：標題列（主鍵＋標籤）／副標（案名、對象）／資料列（label:value，2 欄）／金額列（右對齊、大字）。
 * 金額永遠在卡上，不會因為窄而消失（RWD_REVIEW 原則 1）。
 */
import React from 'react';
import { List, Typography, Space, Tag } from 'antd';
import type { PaginationProps } from 'antd';

const { Text } = Typography;

export interface MobileCardRow {
  label: string;
  value: React.ReactNode;
}

export interface MobileCardProps {
  /** 主鍵（案號、報價單編號、廠商名） */
  title: React.ReactNode;
  /** 案名、對象等第二行 */
  subtitle?: React.ReactNode;
  /** 右上角標籤（狀態、類別） */
  tags?: { text: React.ReactNode; color?: string }[];
  /** label:value 對，兩欄排 */
  rows?: MobileCardRow[];
  /** 金額列：label + 大字數值（右對齊） */
  amounts?: { label: string; value: React.ReactNode; tone?: 'default' | 'good' | 'warn' | 'bad' }[];
  onClick?: () => void;
}

export const MobileCard: React.FC<MobileCardProps> = ({ title, subtitle, tags, rows, amounts, onClick }) => (
  <div
    className={`ck-mcard${onClick ? ' ck-mcard-clickable' : ''}`}
    onClick={onClick}
    role={onClick ? 'button' : undefined}
    tabIndex={onClick ? 0 : undefined}
    onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
  >
    <div className="ck-mcard-head">
      <div className="ck-mcard-heading">
        <div className="ck-mcard-title">{title}</div>
        {subtitle && <div className="ck-mcard-subtitle">{subtitle}</div>}
      </div>
      {tags && tags.length > 0 && (
        <Space size={4} wrap className="ck-mcard-tags">
          {tags.map((t, i) => <Tag key={i} color={t.color} style={{ margin: 0 }}>{t.text}</Tag>)}
        </Space>
      )}
    </div>
    {rows && rows.length > 0 && (
      <div className="ck-mcard-rows">
        {rows.map((r, i) => (
          <div key={i} className="ck-mcard-row">
            <Text type="secondary" className="ck-mcard-label">{r.label}</Text>
            <div className="ck-mcard-value">{r.value ?? '—'}</div>
          </div>
        ))}
      </div>
    )}
    {amounts && amounts.length > 0 && (
      <div className="ck-mcard-amounts">
        {amounts.map((a, i) => (
          <div key={i} className={`ck-mcard-amount ck-mcard-amount-${a.tone ?? 'default'}`}>
            <Text type="secondary" className="ck-mcard-label">{a.label}</Text>
            <div className="ck-mcard-amount-value">{a.value ?? '—'}</div>
          </div>
        ))}
      </div>
    )}
  </div>
);

export interface MobileCardListProps<T> {
  dataSource?: readonly T[];
  rowKey?: string | ((r: T) => React.Key);
  renderCard: (record: T, index: number) => React.ReactNode;
  pagination?: false | PaginationProps;
  loading?: boolean;
  emptyText?: React.ReactNode;
}

/** 手機清單：與 Table 同一份 dataSource／pagination（伺服器分頁的 onChange 照舊生效） */
export function MobileCardList<T>({ dataSource, rowKey = 'id', renderCard, pagination, loading, emptyText }: MobileCardListProps<T>) {
  const keyOf = (r: T): React.Key =>
    typeof rowKey === 'function' ? rowKey(r) : ((r as Record<string, unknown>)[rowKey] as React.Key) ?? JSON.stringify(r);
  return (
    <List<T>
      dataSource={dataSource as T[]}
      loading={loading}
      rowKey={keyOf}
      locale={{ emptyText: emptyText ?? '沒有資料' }}
      pagination={pagination === false ? false : { size: 'small', showSizeChanger: false, simple: true, ...(pagination ?? {}) }}
      renderItem={(item, index) => <div>{renderCard(item, index)}</div>}
      split={false}
    />
  );
}
