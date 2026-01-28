/**
 * FilterFieldWrapper 元件
 *
 * 通用的篩選欄位包裝器，提供標籤和 Tooltip
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import { Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import type { FilterFieldWrapperProps } from '../types';

const FilterFieldWrapper: React.FC<FilterFieldWrapperProps> = ({
  label,
  tooltip,
  isMobile,
  children,
}) => {
  if (isMobile) {
    return <>{children}</>;
  }

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>{label}</span>
        <Tooltip title={tooltip}>
          <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
        </Tooltip>
      </div>
      {children}
    </>
  );
};

export default FilterFieldWrapper;
