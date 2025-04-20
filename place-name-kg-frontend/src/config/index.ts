/**
 * 全局配置文件
 */

// 动态获取后端API地址
const getBaseUrl = () => {
  // 获取当前窗口的主机名（IP地址或域名）
  const hostname = window.location.hostname;
  
  // 后端API服务的端口
  const apiPort = '5000';
  
  // 如果是localhost或127.0.0.1，使用相同的主机名
  // 否则使用当前访问的主机名（适用于局域网访问）
  return `http://${hostname}:${apiPort}`;
};

export default {
  // API基础URL
  baseURL: getBaseUrl(),
  
  // API请求超时时间（毫秒）
  timeout: 1000 * 60 * 10,
}; 