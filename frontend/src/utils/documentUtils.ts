// 格式化日期
export const formatDate = (dateString: string): string => {
  return new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateString));
};

// 獲取狀態顏色
export const getStatusColor = (status: string) => {
  switch (status) {
    case 'draft':
      return 'default' as const;
    case 'pending':
      return 'warning' as const;
    case 'approved':
      return 'success' as const;
    case 'rejected':
      return 'error' as const;
    default:
      return 'default' as const;
  }
};

// 獲取狀態標籤
export const getStatusLabel = (status: string): string => {
  switch (status) {
    case 'draft':
      return '草稿';
    case 'pending':
      return '待審核';
    case 'approved':
      return '已核准';
    case 'rejected':
      return '已拒絕';
    default:
      return '未知';
  }
};

// 獲取優先級顏色
export const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'urgent':
      return 'error' as const;
    case 'high':
      return 'warning' as const;
    case 'medium':
      return 'info' as const;
    case 'low':
      return 'default' as const;
    default:
      return 'default' as const;
  }
};

// 獲取優先級標籤
export const getPriorityLabel = (priority: string): string => {
  switch (priority) {
    case 'urgent':
      return '緊急';
    case 'high':
      return '高';
    case 'medium':
      return '中';
    case 'low':
      return '低';
    default:
      return '一般';
  }
};

// 格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 截斷文字
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};
