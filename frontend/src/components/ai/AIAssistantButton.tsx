/**
 * AI 助手浮動按鈕元件
 *
 * 提供快速存取 AI 功能的浮動按鈕
 * 使用 Portal 渲染，與主版面完全隔離
 *
 * @version 2.3.0
 * @created 2026-02-04
 * @updated 2026-02-09 - 移除 AI 工具 Tab + 動態高度 + 搜尋範圍提示
 * @reference CK_lvrland_Webmap FloatingAssistant 架構
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Button,
  Card,
  Space,
  Tooltip,
  Badge,
} from 'antd';
import {
  RobotOutlined,
  CloseOutlined,
  DragOutlined,
  MinusOutlined,
  ExpandOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useResponsive } from '../../hooks';
import { syncAIConfigFromServer } from '../../config/aiConfig';
import { NaturalSearchPanel } from './NaturalSearchPanel';

interface AIAssistantButtonProps {
  /** 是否顯示 */
  visible?: boolean;
}

/**
 * AI 助手浮動按鈕
 *
 * 使用 Portal 渲染，確保與主版面 CSS 隔離
 */
export const AIAssistantButton: React.FC<AIAssistantButtonProps> = ({
  visible = true,
}) => {
  const { isMobile, responsiveValue } = useResponsive();

  // 面板狀態
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [searchResultCount, setSearchResultCount] = useState<number | null>(null);

  // 拖曳功能狀態
  const [position, setPosition] = useState({ right: 80, bottom: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef({ x: 0, y: 0, right: 80, bottom: 100 });
  const panelRef = useRef<HTMLDivElement>(null);

  // 響應式面板尺寸 - v2.3.0: 動態高度，最高佔螢幕 75%
  const panelWidth = responsiveValue({ mobile: 'calc(100vw - 32px)', desktop: '380px' }) || '380px';
  const panelMaxHeight = responsiveValue({ mobile: 'calc(100vh - 120px)', desktop: 'calc(75vh)' }) || 'calc(75vh)';
  const buttonSize = responsiveValue({ mobile: 48, desktop: 56 }) || 56;

  // S3: 元件首次掛載時同步 AI 配置（靜默失敗）
  useEffect(() => {
    syncAIConfigFromServer().catch(() => {
      // 靜默失敗，不顯示錯誤
    });
  }, []);

  // ============================================================================
  // 拖曳功能
  // ============================================================================

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    // 手機版停用拖曳
    if (isMobile) return;
    e.preventDefault();
    setIsDragging(true);
    dragStartPos.current = {
      x: e.clientX,
      y: e.clientY,
      right: position.right,
      bottom: position.bottom,
    };
  }, [position, isMobile]);

  const handleDragMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const deltaX = dragStartPos.current.x - e.clientX;
    const deltaY = dragStartPos.current.y - e.clientY;

    // 使用 panelRef 動態取得面板尺寸
    const panelEl = panelRef.current;
    const panelW = panelEl?.offsetWidth ?? 320;
    const panelH = panelEl?.offsetHeight ?? 400;

    const newRight = Math.max(0, Math.min(window.innerWidth - panelW, dragStartPos.current.right + deltaX));
    const newBottom = Math.max(0, Math.min(window.innerHeight - panelH, dragStartPos.current.bottom + deltaY));

    setPosition({ right: newRight, bottom: newBottom });
  }, [isDragging]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 註冊全域拖曳事件
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('mouseup', handleDragEnd);
      document.body.style.cursor = 'grabbing';
      document.body.style.userSelect = 'none';
    }
    return () => {
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, handleDragMove, handleDragEnd]);

  // ============================================================================
  // Portal 容器
  // ============================================================================

  const portalContainer = useMemo(() => {
    if (typeof document === 'undefined') return null;
    let container = document.getElementById('ai-assistant-portal');
    if (!container) {
      container = document.createElement('div');
      container.id = 'ai-assistant-portal';
      // 設定容器樣式，確保不影響頁面佈局
      container.style.position = 'fixed';
      container.style.top = '0';
      container.style.left = '0';
      container.style.width = '0';
      container.style.height = '0';
      container.style.overflow = 'visible';
      container.style.pointerEvents = 'none';
      container.style.zIndex = '9999';
      document.body.appendChild(container);
    }
    return container;
  }, []);

  // ============================================================================
  // 渲染內容
  // ============================================================================

  if (!visible) return null;

  const assistantContent = (
    <>
      {/* 浮動按鈕 */}
      <Tooltip title="AI 公文搜尋" placement="left">
        <Badge count={0} offset={[-5, 5]}>
          <Button
            type="primary"
            shape="circle"
            size="large"
            icon={isOpen ? <CloseOutlined /> : <RobotOutlined />}
            onClick={() => setIsOpen(!isOpen)}
            style={{
              position: 'fixed',
              right: 24,
              bottom: 24,
              width: buttonSize,
              height: buttonSize,
              zIndex: 1000,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              pointerEvents: 'auto',
              background: 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)',
              border: 'none',
              transition: 'all 0.3s ease',
            }}
          />
        </Badge>
      </Tooltip>

      {/* AI 助手面板 (卡片式，可拖曳，可縮合) */}
      {isOpen && (
        <Card
          title={
            <div
              onMouseDown={handleDragStart}
              style={{
                cursor: isMobile ? 'default' : isDragging ? 'grabbing' : 'grab',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              {!isMobile && <DragOutlined style={{ color: '#bfbfbf', fontSize: 12 }} />}
              <SearchOutlined style={{ color: '#1890ff' }} />
              <span
                style={{
                  fontSize: 14,
                  background: 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  fontWeight: 500,
                }}
              >
                AI 公文搜尋
              </span>
              {searchResultCount !== null && searchResultCount > 0 && (
                <Badge count={searchResultCount} size="small" overflowCount={999} />
              )}
            </div>
          }
          extra={
            <Space size={0}>
              <Tooltip title={isMinimized ? '展開' : '縮小'}>
                <Button
                  type="text"
                  icon={isMinimized ? <ExpandOutlined /> : <MinusOutlined />}
                  onClick={() => setIsMinimized(!isMinimized)}
                  size="small"
                />
              </Tooltip>
              <Button
                type="text"
                icon={<CloseOutlined />}
                onClick={() => setIsOpen(false)}
                size="small"
              />
            </Space>
          }
          ref={panelRef as React.Ref<HTMLDivElement>}
          style={{
            position: 'fixed',
            ...(isMobile
              ? { left: 16, right: 16, bottom: 80 }
              : { right: position.right, bottom: position.bottom }),
            width: isMobile ? undefined : panelWidth,
            height: isMinimized ? 'auto' : undefined,
            maxHeight: isMinimized ? 56 : panelMaxHeight,
            zIndex: 1000,
            borderRadius: 12,
            boxShadow: isDragging
              ? '0 12px 32px rgba(0,0,0,0.25)'
              : '0 6px 20px rgba(0,0,0,0.12)',
            overflow: 'hidden',
            pointerEvents: 'auto',
            transition: isDragging ? 'none' : 'box-shadow 0.2s ease, max-height 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
          }}
          styles={{
            header: {
              borderBottom: isMinimized ? 'none' : '1px solid #f0f0f0',
              padding: '8px 16px',
              background: 'linear-gradient(135deg, rgba(24, 144, 255, 0.02) 0%, rgba(114, 46, 209, 0.02) 100%)',
              flexShrink: 0,
            },
            body: {
              padding: '8px 10px',
              display: isMinimized ? 'none' : 'flex',
              flexDirection: 'column' as const,
              flex: 1,
              overflow: 'auto',
              minHeight: 0,
            },
          }}
        >
          <NaturalSearchPanel
            onSearchComplete={(count) => setSearchResultCount(count)}
          />
        </Card>
      )}
    </>
  );

  // 透過 Portal 渲染，與主版面完全隔離
  if (!portalContainer) return null;
  return createPortal(assistantContent, portalContainer);
};

export default AIAssistantButton;
