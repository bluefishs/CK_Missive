/**
 * FilterBar —— 列表頁的篩選列，手機上可收合。
 *
 * 2026-09-05 owner：「篩選列是否模組收合的概念調整，如 /erp/quotations 查詢佔手機顯示 1/3」。
 * 桌面：與原本一樣一列排開（search + 篩選 + 操作）。
 * 手機（< 768px）：只常駐 `summary`（通常是搜尋框）＋一顆「篩選／操作」切換鈕，其餘收起；
 * 展開後篩選項與按鈕**各佔一整行**（Select／Button 撐滿），不再擠成 130px 的小格。
 * 切換鈕上顯示目前生效的篩選數（`activeCount`），收起也知道有沒有在篩。
 */
import React, { useState } from 'react';
import { Button, Space, Badge } from 'antd';
import { FilterOutlined, UpOutlined, DownOutlined } from '@ant-design/icons';
import { useResponsive } from '../../hooks';

export interface FilterBarProps {
  /** 手機上永遠看得到的那一格（搜尋框） */
  summary?: React.ReactNode;
  /** 篩選項與操作鈕；手機收合區 */
  children?: React.ReactNode;
  /** 目前生效的篩選數，顯示在切換鈕上 */
  activeCount?: number;
  /** 手機預設展開？預設收合 */
  defaultOpen?: boolean;
  style?: React.CSSProperties;
}

export const FilterBar: React.FC<FilterBarProps> = ({ summary, children, activeCount = 0, defaultOpen = false, style }) => {
  const { isMobile } = useResponsive();
  const [open, setOpen] = useState(defaultOpen);

  if (!isMobile) {
    return (
      <Space wrap style={{ marginBottom: 16, ...style }}>
        {summary}
        {children}
      </Space>
    );
  }

  return (
    <div className="ck-filterbar-mobile" style={{ marginBottom: 12, ...style }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <div style={{ flex: 1, minWidth: 0 }}>{summary}</div>
        {/* 2026-09-05 owner「手機無法進行篩選，功能遮蔽無法顯示」：切換鈕原本只有兩個小圖示，
            看不出那是篩選入口。改成有字的「篩選」鈕，有生效篩選時變主色，讓收起來的功能看得出來在哪。 */}
        <Badge count={activeCount} size="small" offset={[-2, 2]}>
          <Button
            type={activeCount > 0 ? 'primary' : 'default'}
            icon={<FilterOutlined />}
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-label={open ? '收起篩選' : '展開篩選'}
          >
            篩選{open ? <UpOutlined /> : <DownOutlined />}
          </Button>
        </Badge>
      </div>
      {open && (
        <div className="ck-filterbar-mobile-body" style={{ display: 'grid', gap: 8, marginTop: 8 }}>
          {children}
        </div>
      )}
    </div>
  );
};

export default FilterBar;
