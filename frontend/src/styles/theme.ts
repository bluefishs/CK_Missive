import { ThemeConfig } from 'antd';

export const theme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    colorInfo: '#1890ff',
    borderRadius: 6,
    colorBgContainer: '#ffffff',
  },
  components: {
    Layout: {
      colorBgHeader: '#001529',
      colorBgBody: '#f5f5f5',
      colorBgTrigger: '#002140',
    },
    Menu: {
      colorItemBg: '#001529',
      colorItemText: '#ffffff',
      colorItemTextSelected: '#1890ff',
      colorItemBgSelected: '#002140',
    },
    Button: {
      borderRadius: 6,
    },
    Card: {
      borderRadius: 8,
    },
    Table: {
      borderRadius: 8,
    },
  },
};

export default theme;