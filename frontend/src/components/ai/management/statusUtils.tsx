/**
 * AI 管理頁面共用工具元件
 *
 * @version 1.0.0
 * @created 2026-02-27
 */
import React from 'react';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

/** 狀態圖示：綠勾 / 紅叉 */
export const StatusIcon: React.FC<{ ok: boolean }> = ({ ok }) =>
  ok
    ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
    : <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
