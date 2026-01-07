/**
 * 通用詳情頁 Header 元件
 *
 * 提供統一的頁面標題區域設計
 *
 * @version 1.0.0
 * @date 2026-01-07
 */

import React from 'react';
import { Card, Button, Space, Typography, Tag } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { DetailPageHeaderProps } from './types';

const { Title } = Typography;

/**
 * DetailPageHeader - 通用詳情頁標題元件
 *
 * 提供統一的頁面標題區域，包含：
 * - 返回按鈕
 * - 主標題（可帶圖示）
 * - 標籤列表
 * - 右側操作區域
 */
export const DetailPageHeader: React.FC<DetailPageHeaderProps> = ({
  title,
  subtitle,
  tags = [],
  backText = '返回',
  backPath,
  extra,
  icon,
  onBack,
}) => {
  const navigate = useNavigate();

  /** 處理返回 */
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else if (backPath) {
      navigate(backPath);
    } else {
      navigate(-1);
    }
  };

  return (
    <Card style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        {/* 左側：返回按鈕 + 標題 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
          >
            {backText}
          </Button>
          <div>
            <Title level={3} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              {icon}
              {title}
            </Title>
            {subtitle && (
              <div style={{ color: '#666', marginTop: 4, fontSize: 14 }}>
                {subtitle}
              </div>
            )}
            {tags.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {tags.map((tag, index) => (
                  <Tag key={index} color={tag.color}>
                    {tag.text}
                  </Tag>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 右側：操作按鈕 */}
        {extra && (
          <Space>
            {extra}
          </Space>
        )}
      </div>
    </Card>
  );
};

export default DetailPageHeader;
