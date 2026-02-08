/**
 * 響應式表單行元件
 *
 * 在大螢幕 (md+, >=768px) 將多個表單欄位平均分配到多欄，
 * 在小螢幕 (xs/sm) 每個欄位佔滿一整行。
 *
 * 使用 Ant Design Row/Col 搭配專案已有的 useResponsive hook。
 *
 * @version 1.0.0
 * @date 2026-02-08
 *
 * @example
 * ```tsx
 * <ResponsiveFormRow>
 *   <Form.Item label="發文機關" name="sender">
 *     <Input />
 *   </Form.Item>
 *   <Form.Item label="受文者" name="receiver">
 *     <Input />
 *   </Form.Item>
 * </ResponsiveFormRow>
 * ```
 */

import React from 'react';
import { Row, Col } from 'antd';

interface ResponsiveFormRowProps {
  /** 每個 child 佔一欄 */
  children: React.ReactNode;
  /** 欄位間距 (水平 gutter)，預設 16 */
  gutter?: number;
}

/**
 * 響應式表單行
 *
 * - md+ 螢幕 (>=768px): children 平均分配到多欄
 * - xs/sm 螢幕 (<768px): 每個 child 佔一整行 (24 格)
 */
export const ResponsiveFormRow: React.FC<ResponsiveFormRowProps> = ({
  children,
  gutter = 16,
}) => {
  const childArray = React.Children.toArray(children).filter(Boolean);
  const count = childArray.length;

  if (count === 0) return null;

  const mdSpan = Math.floor(24 / count);

  return (
    <Row gutter={gutter}>
      {childArray.map((child, index) => (
        <Col key={index} xs={24} md={mdSpan}>
          {child}
        </Col>
      ))}
    </Row>
  );
};

export default ResponsiveFormRow;
