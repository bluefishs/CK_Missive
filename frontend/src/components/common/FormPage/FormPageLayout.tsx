/**
 * 通用表單頁佈局元件
 *
 * 提供統一的新增/編輯表單頁面結構：
 * - Header（標題、返回按鈕、保存按鈕）
 * - 表單內容區
 * - Loading 狀態
 *
 * @version 1.0.0
 * @date 2026-01-22
 */

import React from 'react';
import { Card, Button, Space, Typography, Spin } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

export interface FormPageLayoutProps {
  /** 頁面標題 */
  title: string;
  /** 返回路徑 */
  backPath: string;
  /** 保存按鈕點擊事件 */
  onSave: () => void;
  /** 是否正在載入資料 */
  loading?: boolean;
  /** 是否正在保存 */
  saving?: boolean;
  /** 返回按鈕文字 */
  backText?: string;
  /** 保存按鈕文字 */
  saveText?: string;
  /** 是否顯示取消按鈕 */
  showCancel?: boolean;
  /** 最大寬度 */
  maxWidth?: number;
  /** 表單內容 */
  children: React.ReactNode;
}

/**
 * FormPageLayout - 通用表單頁佈局元件
 *
 * 使用範例：
 * ```tsx
 * <FormPageLayout
 *   title="新增機關"
 *   backPath="/agencies"
 *   onSave={handleSubmit}
 *   saving={isSubmitting}
 * >
 *   <Form form={form} layout="vertical">
 *     ...
 *   </Form>
 * </FormPageLayout>
 * ```
 */
export const FormPageLayout: React.FC<FormPageLayoutProps> = ({
  title,
  backPath,
  onSave,
  loading = false,
  saving = false,
  backText = '返回列表',
  saveText = '保存',
  showCancel = true,
  maxWidth = 800,
  children,
}) => {
  const navigate = useNavigate();

  const handleBack = () => {
    navigate(backPath);
  };

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          {/* 左側：返回按鈕 + 標題 */}
          <Space size="middle">
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleBack}
            >
              {backText}
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              {title}
            </Title>
          </Space>

          {/* 右側：操作按鈕 */}
          <Space>
            {showCancel && (
              <Button onClick={handleBack}>
                取消
              </Button>
            )}
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={onSave}
              loading={saving}
            >
              {saveText}
            </Button>
          </Space>
        </div>
      </Card>

      {/* 表單內容 */}
      <Card>
        <Spin spinning={loading} tip="載入中...">
          <div style={{ minHeight: loading ? 200 : 'auto' }}>
            {!loading && children}
          </div>
        </Spin>
      </Card>
    </div>
  );
};

export default FormPageLayout;
