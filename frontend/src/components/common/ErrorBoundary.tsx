/**
 * 前端錯誤邊界組件 - 捕獲並處理 React 組件錯誤
 *
 * @version 2.0.0
 * @date 2026-01-21
 * @description 整合完整錯誤追蹤功能，支援自訂 fallback 和錯誤回調
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button, Typography, Collapse, Card } from 'antd';
import { ReloadOutlined, BugOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Props {
  children: ReactNode;
  /** 自訂錯誤顯示 UI */
  fallback?: ReactNode;
  /** 錯誤發生時的回調函數 */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
}

/**
 * ErrorBoundary - React 錯誤邊界組件
 *
 * 用於捕獲子組件樹中的 JavaScript 錯誤，防止整個應用崩潰。
 *
 * @example
 * ```tsx
 * <ErrorBoundary onError={(error) => logError(error)}>
 *   <App />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: ''
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    return {
      hasError: true,
      error,
      errorId
    };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // 調用父組件的錯誤處理函數
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // 記錄錯誤到控制台
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // 記錄錯誤報告
    this.logErrorToService(error, errorInfo);
  }

  private logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    const errorReport = {
      timestamp: new Date().toISOString(),
      errorId: this.state.errorId,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // 開發環境輸出錯誤報告
    // eslint-disable-next-line no-console
    console.log('Error Report:', errorReport);

    // 可以發送到後端 API 進行錯誤追蹤
    // fetch('/api/monitoring/error-report', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(errorReport)
    // }).catch(() => console.log('Failed to log error to server'));
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: ''
    });
  };

  override render() {
    if (this.state.hasError) {
      // 如果提供了自定義的 fallback UI，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默認錯誤 UI
      return (
        <div style={{ padding: '24px', minHeight: '400px' }}>
          <Result
            status="error"
            title="頁面載入失敗"
            subTitle={`很抱歉，系統遇到了未預期的錯誤。錯誤編號：${this.state.errorId}`}
            extra={[
              <Button type="primary" onClick={this.handleReload} icon={<ReloadOutlined />} key="reload">
                重新載入頁面
              </Button>,
              <Button onClick={this.handleReset} key="reset">
                重試
              </Button>
            ]}
          >
            <div style={{ textAlign: 'left', maxWidth: '600px', margin: '0 auto' }}>
              <Paragraph>
                <Text strong>建議的解決方法：</Text>
              </Paragraph>
              <ul>
                <li>重新載入頁面</li>
                <li>檢查網路連線是否正常</li>
                <li>清除瀏覽器快取後重試</li>
                <li>如果問題持續發生，請聯繫系統管理員</li>
              </ul>

              {/* 開發環境顯示詳細錯誤信息 */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <Card style={{ marginTop: '16px' }}>
                  <Collapse ghost>
                    <Panel header={<Text type="danger"><BugOutlined /> 開發者錯誤詳情</Text>} key="error-details">
                      <div style={{ marginBottom: '16px' }}>
                        <Text strong>錯誤訊息：</Text>
                        <pre style={{
                          background: '#f5f5f5',
                          padding: '8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          overflow: 'auto'
                        }}>
                          {this.state.error.message}
                        </pre>
                      </div>

                      {this.state.error.stack && (
                        <div style={{ marginBottom: '16px' }}>
                          <Text strong>錯誤堆疊：</Text>
                          <pre style={{
                            background: '#f5f5f5',
                            padding: '8px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            overflow: 'auto',
                            maxHeight: '200px'
                          }}>
                            {this.state.error.stack}
                          </pre>
                        </div>
                      )}

                      {this.state.errorInfo && this.state.errorInfo.componentStack && (
                        <div>
                          <Text strong>組件堆疊：</Text>
                          <pre style={{
                            background: '#f5f5f5',
                            padding: '8px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            overflow: 'auto',
                            maxHeight: '200px'
                          }}>
                            {this.state.errorInfo.componentStack}
                          </pre>
                        </div>
                      )}
                    </Panel>
                  </Collapse>
                </Card>
              )}
            </div>
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
