/**
 * 格式化工具函數
 */

/**
 * 格式化日期
 */
export function formatDate(date: string | Date, formatStr = 'yyyy-MM-dd'): string {
  if (!date) return '';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  if (isNaN(dateObj.getTime())) {
    return '無效日期';
  }
  
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, '0');
  const day = String(dateObj.getDate()).padStart(2, '0');
  
  if (formatStr === 'yyyy-MM-dd') {
    return `${year}-${month}-${day}`;
  }
  
  const hours = String(dateObj.getHours()).padStart(2, '0');
  const minutes = String(dateObj.getMinutes()).padStart(2, '0');
  const seconds = String(dateObj.getSeconds()).padStart(2, '0');
  
  if (formatStr === 'yyyy-MM-dd HH:mm:ss') {
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  }
  
  return `${year}-${month}-${day}`;
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 獲取狀態顏色
 */
export function getStatusColor(status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' {
  switch (status) {
    case 'draft': return 'default';
    case 'review': return 'warning';
    case 'published': return 'success';
    case 'archived': return 'info';
    default: return 'default';
  }
}

/**
 * 獲取優先級顏色
 */
export function getPriorityColor(priority: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' {
  switch (priority) {
    case 'low': return 'info';
    case 'normal': return 'default';
    case 'high': return 'warning';
    case 'urgent': return 'error';
    default: return 'default';
  }
}

/**
 * 獲取狀態標籤
 */
export function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    draft: '草稿',
    review: '審核中',
    published: '已發布',
    archived: '已歸檔',
  };
  return statusMap[status] || status;
}

/**
 * 獲取優先級標籤
 */
export function getPriorityLabel(priority: string): string {
  const priorityMap: Record<string, string> = {
    low: '低',
    normal: '一般',
    high: '高',
    urgent: '緊急',
  };
  return priorityMap[priority] || priority;
}