/**
 * 前端模拟流式响应处理工具
 * 不再使用后端流式API，而是使用普通API请求获取完整回答，然后在前端模拟流式显示效果
 */

// 导入配置的后端基础URL和用户存储
import Http from '../../api/http';

// 创建连接并处理响应（现在使用普通API请求而非流式API）
export function createStreamConnection(url: string, data: any, callbacks: {
  onStart?: (context: string) => void,
  onChunk?: (chunk: string) => void,
  onEnd?: (model: string) => void,
  onError?: (error: string) => void,
  onThinking?: (thinking: string) => void, // 添加思考过程回调
  onComplete?: (fullResponse: {content: string, thinking: string[], context: string}) => void // 完整响应回调
}) {
  console.log('使用普通API请求替代流式API');
  
  // 使用普通API接口替代流式接口
  // 将stream接口路径改为普通接口路径
  const apiUrl = url.replace('/stream', '');
  
  // 发起普通POST请求
  Http.post(apiUrl, data)
    .then(response => {
      if (response.code !== 200) {
        throw new Error(response.msg || '请求失败');
      }
      
      const responseData = response.data;
      console.log('收到API响应:', responseData);
      
      // 提取回答内容、思考过程和上下文
      const content = responseData.answer || '';
      const thinking = responseData.thinking || [];
      const context = responseData.context || '';
      
      // 调用onStart回调，传递上下文信息
      callbacks.onStart && callbacks.onStart(context);
      
      // 调用onComplete回调，提供完整的响应内容
      if (callbacks.onComplete) {
        callbacks.onComplete({
          content: content,
          thinking: thinking,
          context: context
        });
      }
      
      // 调用onEnd回调
      callbacks.onEnd && callbacks.onEnd('default');
    })
    .catch(error => {
      console.error('请求出错:', error);
      callbacks.onError && callbacks.onError(error.message || '请求出错');
    });
  
  // 返回空函数作为取消函数（普通API请求不支持取消）
  return () => {
    console.log('普通API请求不支持取消');
  };
}