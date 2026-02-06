/**
 * 通用詳情頁 Header 元件
 *
 * 提供統一的頁面標題區域設計，支援響應式佈局
 *
 * @version 1.1.0
 * @date 2026-01-22
 */

import React from 'react';
import { Card, Button, Space, Typography, Tag } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResponsive } from '../../../hooks';
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
 * - RWD 響應式支援
 */
const DetailPageHeaderInner: React.FC<DetailPageHeaderProps> = ({
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
  const { isMobile, responsiveValue } = useResponsive();

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

  const titleLevel = responsiveValue({ mobile: 4, tablet: 3, desktop: 3 }) as 3 | 4;
  const headerGap = responsiveValue({ mobile: 8, tablet: 12, desktop: 16 });

  return (
    <Card style={{ marginBottom: isMobile ? 12 : 16 }}>
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'flex-start',
          gap: isMobile ? 12 : 0,
        }}
      >
        {/* 左側：返回按鈕 + 標題 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: headerGap }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            size={isMobile ? 'small' : 'middle'}
          >
            {isMobile ? '' : backText}
          </Button>
          <div style={{ flex: 1 }}>
            <Title level={titleLevel} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              {icon}
              <span style={{ wordBreak: 'break-word' }}>{title}</span>
            </Title>
            {subtitle && (
              <div style={{ color: '#666', marginTop: 4, fontSize: isMobile ? 12 : 14 }}>
                {subtitle}
              </div>
            )}
            {tags.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
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
          <Space wrap={isMobile} style={{ justifyContent: isMobile ? 'flex-end' : undefined }}>
            {extra}
          </Space>
        )}
      </div>
    </Card>
  );
};

export const DetailPageHeader = React.memo(DetailPageHeaderInner);
export default DetailPageHeader;
