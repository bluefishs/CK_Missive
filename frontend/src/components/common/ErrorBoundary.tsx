import { Component, ErrorInfo, ReactNode } from 'react';
import { Card, Button, Typography, Space } from 'antd';
import { ExclamationCircleOutlined, ReloadOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(_: Error): State {
    return { hasError: true };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  public override render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          minHeight: '50vh',
          padding: '32px'
        }}>
          <Card style={{ maxWidth: 600, width: '100%', textAlign: 'center' }}>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <ExclamationCircleOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />
              
              <Title level={2}>出現了一些問題</Title>
              
              <Text type="secondary">
                很抱歉，應用程式出現了錯誤。請嘗試重新載入頁面。
              </Text>

              {process.env['NODE_ENV'] === 'development' && this.state.error && (
                <Card 
                  size="small" 
                  style={{ 
                    backgroundColor: '#f5f5f5',
                    textAlign: 'left',
                    marginTop: 16
                  }}
                >
                  <Text code style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                    {this.state.error.toString()}
                    {this.state.errorInfo && this.state.errorInfo.componentStack}
                  </Text>
                </Card>
              )}

              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={() => window.location.reload()}
                size="large"
              >
                重新載入
              </Button>
            </Space>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}