/**
 * AccountInfoCard - Account status, role, auth provider, and login statistics
 *
 * @version 1.0.0
 */

import {
  Card,
  Row,
  Col,
  Tag,
  Typography,
} from 'antd';
import {
  GoogleOutlined,
  MailOutlined,
} from '@ant-design/icons';
import type { AccountInfoCardProps } from './types';

const { Text } = Typography;

/** Render a colored Tag based on user role */
const getRoleTag = (role: string | undefined, isAdmin: boolean) => {
  if (isAdmin) {
    return <Tag color="red">管理員</Tag>;
  }
  switch (role) {
    case 'superuser':
      return <Tag color="purple">超級管理員</Tag>;
    case 'admin':
      return <Tag color="red">管理員</Tag>;
    case 'staff':
      return <Tag color="geekblue">承辦同仁</Tag>;
    case 'user':
      return <Tag color="blue">一般用戶</Tag>;
    case 'unverified':
      return <Tag color="orange">未驗證</Tag>;
    default:
      return <Tag>{role || '未設定'}</Tag>;
  }
};

export const AccountInfoCard = ({ profile, isMobile }: AccountInfoCardProps) => {
  const fontSize = isMobile ? 12 : 14;

  return (
    <Card title="帳戶資訊" size={isMobile ? 'small' : 'medium'}>
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>帳戶狀態：</Text>
          <br />
          {profile.is_active ?
            <Tag color="green">已啟用</Tag> :
            <Tag color="red">已停用</Tag>
          }
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>用戶角色：</Text>
          <br />
          {getRoleTag(profile.role, profile.is_admin)}
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>驗證方式：</Text>
          <br />
          {profile.auth_provider === 'google' ? (
            <Tag icon={<GoogleOutlined />} color="blue">Google</Tag>
          ) : (
            <Tag icon={<MailOutlined />} color="green">郵箱</Tag>
          )}
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>郵箱驗證：</Text>
          <br />
          {profile.email_verified ?
            <Tag color="green">已驗證</Tag> :
            <Tag color="orange">未驗證</Tag>
          }
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>登入次數：</Text>
          <br />
          <Text style={{ fontSize }}>{profile.login_count ?? 0} 次</Text>
        </Col>
        <Col xs={12} sm={8}>
          <Text strong style={{ fontSize }}>最後登入：</Text>
          <br />
          <Text style={{ fontSize }}>
            {profile.last_login
              ? new Date(profile.last_login).toLocaleString()
              : '從未登入'
            }
          </Text>
        </Col>
        <Col xs={24} sm={8}>
          <Text strong style={{ fontSize }}>註冊時間：</Text>
          <br />
          <Text style={{ fontSize }}>
            {new Date(profile.created_at).toLocaleString()}
          </Text>
        </Col>
      </Row>
    </Card>
  );
};
