<template>
  <div class="inference-container">
    <!-- 左侧聊天列表 -->
    <div class="chat-sidebar" :class="{ 'sidebar-collapsed': !showSidebar }">
      <div class="sidebar-header">
        <lay-button type="primary" @click="createNewChat" long>新建聊天</lay-button>
      </div>
      <div class="chat-history">
        <div 
          v-for="(chat, index) in chatHistory" 
          :key="index" 
          class="chat-item"
          :class="{ 'active': currentChatIndex === index }"
        >
          <div class="chat-item-content" @click="switchChat(index)">
            <div class="chat-title">{{ chat.title || '新对话' }}</div>
            <div class="chat-time">{{ formatTime(chat.lastTime) }}</div>
          </div>
          <div class="chat-actions">
            <lay-icon 
              type="layui-icon-delete" 
              color="#ff5722" 
              @click.stop="deleteChat(index)"
              class="delete-icon"
            ></lay-icon>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 右侧聊天内容 -->
    <div class="chat-content">
      <!-- 添加覆盖层，用于移动设备上阻止事件传播 -->
      <div class="sidebar-overlay" v-if="isMobileView && showSidebar" @click="toggleSidebar"></div>
      
      <!-- 移除lay-card，使用flex布局替代 -->
      <div class="chat-header">
        <div class="header-left">
          <div class="fold-button" @click="toggleSidebar">
            <lay-icon :type="showSidebar ? 'layui-icon-spread-left' : 'layui-icon-shrink-right'" color="#009688" size="16px"></lay-icon>
          </div>
          <div class="header-title">{{ currentChat.title || '新对话' }}</div>
        </div>
        <div class="header-actions">
          <!-- 添加导出按钮 -->
          <lay-icon 
            type="layui-icon-export" 
            color="#009688" 
            size="20px" 
            class="export-button"
            title="导出对话到Markdown"
            @click="exportToMarkdown"
          ></lay-icon>
        </div>
      </div>
      
      <!-- 聊天区域包装器 -->
      <div class="message-wrapper">
        <!-- 消息列表 -->
        <div class="message-container" ref="messageContainer">
          <div v-if="isFirstLoad && currentChat.messages.length === 0" class="empty-chat">
            <div class="empty-icon">
              <lay-icon type="layui-icon-loading" size="60px" color="#dcdcdc"></lay-icon>
            </div>
            <div class="empty-text">正在加载聊天记录...</div>
          </div>
          <div v-else-if="currentChat.messages.length === 0" class="empty-chat">
            <div class="empty-icon">
              <lay-icon type="layui-icon-dialogue" size="60px" color="#dcdcdc"></lay-icon>
            </div>
            <div class="empty-text">开始新的对话</div>
            <!-- 添加快捷提示 -->
            <div class="quick-prompts">
              <div class="prompt-title">常用提示：</div>
              <div class="prompt-items">
                <div class="prompt-item" v-for="(prompt, idx) in quickPrompts" :key="idx" @click="useQuickPrompt(prompt)">
                  {{ prompt }}
                </div>
              </div>
            </div>
          </div>
          <template v-else>
            <div 
              v-for="(message, msgIndex) in currentChat.messages" 
              :key="msgIndex"
              class="message-item"
              :class="message.role === 'user' ? 'user-message' : 'ai-message'"
            >
              <div class="message-avatar">
                <lay-avatar v-if="message.role === 'user'" size="40px">用户</lay-avatar>
                <lay-avatar v-else size="40px" bg-color="#009688">AI</lay-avatar>
              </div>
              <div class="message-content">
                <!-- 用户消息 -->
                <div class="message-text" v-if="message.role === 'user'">{{ message.content }}</div>
                
                <!-- AI消息部分 -->
                <template v-else>
                  <!-- 思考过程显示 - 移到答案上面 -->
                  <div
                    v-if="message.thinking && message.thinking.length > 0"
                    class="thinking-section"
                  >
                    <div class="thinking-header">
                      <div class="thinking-header-left">
                        <span class="iconfont icon-thinking"></span>
                        <span>思考过程</span>
                      </div>
                      <div class="thinking-header-right">
                        <div class="thinking-tag">模型思考推理</div>
                      </div>
                    </div>
                    <div class="thinking-content">
                      <div v-for="(item, index) in message.thinking" :key="index" v-html="renderThinkingContent(item)"></div>
                    </div>
                  </div>
                  
                  <!-- AI消息使用Markdown渲染 -->
                  <div class="message-text markdown-body" v-html="renderMarkdown(message.content)"></div>
                  
                  <!-- 知识图谱可视化 -->
                  <div v-if="message.role === 'assistant' && message.kgContext" class="kg-visualization" @click.stop>
                    <div class="kg-header" @click.stop="toggleKgVisualization(msgIndex, $event)">
                      <lay-icon :type="showKgVisualization[msgIndex] ? 'layui-icon-up' : 'layui-icon-down'" color="#009688"></lay-icon>
                      <span>{{ showKgVisualization[msgIndex] ? '隐藏知识图谱' : '显示知识图谱' }}</span>
                    </div>
                    
                    <div v-if="showKgVisualization[msgIndex]" class="kg-graph-wrapper" @click.stop @mousedown.stop @touchstart.stop>
                      <div class="kg-graph-container" @click.stop @mousedown.stop @touchstart.stop>
                        <!-- 知识图谱视图，可以通过引入外部图谱库如ECharts完善 -->
                        <div class="kg-graph-placeholder" @click.stop @mousedown.stop @touchstart.stop>
                          <div v-if="getKgData(message).nodes.length === 0" class="kg-empty" @click.stop>
                            <lay-icon type="layui-icon-about" color="#FF9800"></lay-icon>
                            <span>没有检索到相关的知识图谱数据</span>
                          </div>
                          <kg-graph v-else :data="getKgData(message)" class="kg-graph"></kg-graph>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 添加知识图谱未找到信息的提示 -->
                  <div v-if="message.role === 'assistant' && message.fromKg === false" class="no-kg-info-notice">
                    <lay-icon type="layui-icon-tips" color="#FF9800"></lay-icon>
                    <span>知识图谱中未找到相关信息，此为大模型基于通用知识的回答</span>
                  </div>
                </template>
                
                <div class="message-footer">
                  <div class="message-actions">
                    <lay-icon 
                      type="layui-icon-file" 
                      size="14px" 
                      color="#888" 
                      class="action-icon" 
                      title="复制消息"
                      @click="copyMessage(message.content)"
                    ></lay-icon>
                  </div>
                  <div class="message-time">{{ formatTime(message.time) }}</div>
                  
                  <!-- 知识图谱引用信息 -->
                  <div v-if="message.role === 'assistant' && message.kgContext" class="kg-reference">
                    <lay-button 
                      type="text" 
                      size="sm" 
                      @click="toggleKgInfo(msgIndex)"
                    >
                      {{ showKgInfo[msgIndex] ? '隐藏知识图谱信息' : '查看引用图谱信息' }}
                    </lay-button>
                    
                    <div v-if="showKgInfo[msgIndex]" class="kg-context">
                      <lay-line theme="green">知识图谱参考信息</lay-line>
                      <div class="ai-notice">
                        <lay-icon type="layui-icon-about" color="#FF9800"></lay-icon>
                        <span>{{ message.fromKg === false ? '知识图谱中未找到相关信息，内容由AI基于通用知识生成' : '内容由AI基于下方知识图谱信息生成，请注意辨别信息的准确性' }}</span>
                      </div>
                      <div class="kg-content-formatted markdown-body" v-html="renderKgContextMarkdown(message.kgContext)"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
          <div v-if="loading" class="ai-message">
            <div class="message-avatar">
              <lay-avatar size="40px" bg-color="#009688">AI</lay-avatar>
            </div>
            <div class="message-content thinking-bubble">
              <div class="message-text thinking-animation">思考中<span class="dot-animation"></span></div>
            </div>
          </div>
        </div>
        
        <!-- 实体卡片 - 当识别到实体且当前消息是AI回复时显示 -->
        <div v-if="currentChat.messages.length > 0 && 
                    currentChat.messages[currentChat.messages.length-1].role === 'assistant' && 
                    currentChat.messages[currentChat.messages.length-1].entities && 
                    currentChat.messages[currentChat.messages.length-1].entities.length > 0 &&
                    showEntityCard" 
             class="entity-card">
          <div class="entity-card-header">
            <div class="entity-card-title">
              <lay-icon type="layui-icon-location" color="#009688" size="14px"></lay-icon>
              <span>识别到的地名实体</span>
            </div>
            <div class="entity-card-close" @click="hideEntityCard">
              <lay-icon type="layui-icon-close" color="#999" size="12px"></lay-icon>
            </div>
          </div>
          <div class="entity-list">
            <lay-tag 
              v-for="(entity, idx) in currentChat.messages[currentChat.messages.length-1].entities" 
              :key="idx"
              size="sm"
              theme="primary"
              class="entity-tag"
              @click="askAboutEntity(entity)"
            >{{ entity }}</lay-tag>
          </div>
        </div>
      </div>
      
      <!-- 输入框和按钮 - 重新样式化为底部固定样式 -->
      <div class="input-container">
        <div class="input-textarea-wrapper">
          <lay-textarea 
            v-model="currentQuery" 
            placeholder="请输入您的问题，系统将结合知识图谱内容进行回答..." 
            :autosize="{minRows: 1, maxRows: 2}"
            @keydown.enter="handleEnterKey"
            class="compact-textarea"
            ref="textareaRef"
          ></lay-textarea>
          <div class="send-button" @click="handleQuery" :class="{ 'disabled': loading || !currentQuery.trim() }">
            <lay-icon type="layui-icon-up" size="16px" :color="loading || !currentQuery.trim() ? '#ccc' : '#009688'"></lay-icon>
          </div>
        </div>
        <div class="button-group">
          <div class="input-actions">
            <div class="hint">Enter 发送 / Shift + Enter 换行</div>
            <lay-icon 
              type="layui-icon-refresh" 
              color="#888" 
              class="clear-button" 
              title="清空输入"
              @click="clearInput"
            ></lay-icon>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 消息提示 -->
    <div v-if="showCopySuccess" class="copy-success-tip">
      复制成功!
    </div>
    <div v-if="showExportSuccess" class="export-success-tip">
      导出成功!
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, reactive, onBeforeUnmount } from 'vue';
import Http from '../../api/http';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
// 导入知识图谱组件
import KgGraph from './components/KgGraph.vue';

// 创建Markdown渲染器实例
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>';
      } catch (__) {}
    }
    
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  }
});

// Markdown渲染函数
function renderMarkdown(text: string): string {
  if (!text) return '';
  return md.render(text);
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  time: number;
  kgContext?: string; // 知识图谱上下文
  thinking?: string[]; // 思考过程
  fromKg: boolean; // 是否来自知识图谱
  entities?: string[]; // 实体列表
  kg_data?: any; // 单独存储原始的kg_data
}

interface Chat {
  id: number;
  title: string;
  messages: Message[];
  lastTime: number;
}

// 状态变量
const currentQuery = ref('');
const loading = ref(false);
const messageContainer = ref<HTMLElement | null>(null);
const showKgInfo = reactive<{[key: number]: boolean}>({});
const isFirstLoad = ref(true);
const isMobileView = ref(window.innerWidth < 768);
const showSidebar = ref(true);
const initialSidebarState = ref(true); // 添加变量存储初始侧边栏状态
const isSidebarLocked = ref(false); // 添加锁定变量，防止意外改变侧边栏状态
const showCopySuccess = ref(false);
const showExportSuccess = ref(false);
const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;

// 快捷提示
const quickPrompts = [
  "介绍一下这个知识图谱项目",
  "列出最重要的地名实体",
  "解释地名之间的关系",
  "如何利用这个知识图谱进行研究"
];

// 控制知识图谱可视化的显示状态
const showKgVisualization = ref<Record<number, boolean>>({});

// 添加ref用于获取textarea元素
const textareaRef = ref(null);

// 控制实体卡片是否显示
const showEntityCard = ref(true);

// 切换侧边栏显示，适用于所有设备
function toggleSidebar() {
  // 解锁侧边栏以允许状态改变
  isSidebarLocked.value = false;
  showSidebar.value = !showSidebar.value;
  initialSidebarState.value = showSidebar.value; // 保存用户选择的状态
  // 给一段时间后重新锁定侧边栏状态
  setTimeout(() => {
    isSidebarLocked.value = true;
  }, 300);
}

// 切换知识图谱可视化显示
function toggleKgVisualization(index: number, event: Event) {
  // 阻止事件冒泡
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  
  // 锁定侧边栏，防止状态被改变
  isSidebarLocked.value = true;
  
  // 保存当前图谱显示状态
  const currentState = showKgVisualization.value[index];
  
  // 切换图表显示状态
  showKgVisualization.value[index] = !currentState;
  
  // 延迟触发resize事件，等待DOM更新
  if (!currentState) { // 仅在展开图谱时执行
    nextTick(() => {
      // 确保侧边栏状态不变
      if (isSidebarLocked.value) {
        showSidebar.value = initialSidebarState.value;
      }
      
      // 用setTimeout给DOM更新留出时间
      setTimeout(() => {
        if (showKgVisualization.value[index]) { // 确保仍然是展开状态
          // 确保侧边栏状态不变
          if (isSidebarLocked.value) {
            showSidebar.value = initialSidebarState.value;
          }
          
          // 不改变侧边栏状态，仅调整图表大小
          if (document.dispatchEvent) {
            const resizeEvent = new Event('resize');
            window.dispatchEvent(resizeEvent);
          }
        }
      }, 100);
    });
  }
  
  // 300ms后解除侧边栏锁定
  setTimeout(() => {
    isSidebarLocked.value = false;
  }, 300);
}

// 使用快捷提示
function useQuickPrompt(prompt: string) {
  currentQuery.value = prompt;
}

// 复制消息
function copyMessage(content: string) {
  try {
    // 使用更可靠的剪贴板API，并添加错误处理
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(content)
        .then(() => {
          showCopySuccess.value = true;
          setTimeout(() => {
            showCopySuccess.value = false;
          }, 2000);
        })
        .catch(err => {
          console.error('复制失败:', err);
          // 回退方案：创建临时文本域元素
          fallbackCopy(content);
        });
    } else {
      // 浏览器不支持clipboard API，使用回退方案
      fallbackCopy(content);
    }
  } catch (error) {
    console.error('复制过程出错:', error);
    fallbackCopy(content);
  }
}

// 回退复制方法（创建临时文本域元素）
function fallbackCopy(text: string) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  
  // 确保元素不可见
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  document.body.appendChild(textArea);
  
  // 保存用户的选择范围
  const selected = document.getSelection()?.rangeCount ?? 0 > 0 
    ? document.getSelection()?.getRangeAt(0) 
    : false;
  
  // 选择文本
  textArea.select();
  textArea.setSelectionRange(0, textArea.value.length);
  
  // 执行复制命令
  try {
    document.execCommand('copy');
    showCopySuccess.value = true;
    setTimeout(() => {
      showCopySuccess.value = false;
    }, 2000);
  } catch (err) {
    console.error('回退复制失败:', err);
  }
  
  // 移除元素
  document.body.removeChild(textArea);
  
  // 恢复用户的选择
  if (selected && document.getSelection()) {
    document.getSelection()?.removeAllRanges();
    document.getSelection()?.addRange(selected);
  }
}

// 清空输入框
function clearInput() {
  currentQuery.value = '';
}

// 切换知识图谱信息显示
function toggleKgInfo(msgIndex: number) {
  showKgInfo[msgIndex] = !showKgInfo[msgIndex];
}

// 聊天历史
const chatHistory = ref<Chat[]>([
  {
    id: 1,
    title: '新对话',
    messages: [],
    lastTime: Date.now()
  }
]);

const currentChatIndex = ref(0);
const currentChat = computed(() => chatHistory.value[currentChatIndex.value]);

// 从localStorage加载聊天记录
function loadChatHistory() {
  try {
    const storedHistory = localStorage.getItem('chatHistory');
    if (storedHistory) {
      chatHistory.value = JSON.parse(storedHistory);
    }
    // 设置一个短暂的加载延迟，以显示加载状态
    setTimeout(() => {
      isFirstLoad.value = false;
    }, 500);
  } catch (error) {
    console.error('加载聊天历史失败:', error);
    isFirstLoad.value = false;
  }
}

// 保存聊天记录到localStorage
function saveChatHistory() {
  try {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory.value));
  } catch (error) {
    console.error('保存聊天历史失败:', error);
  }
}

// 创建新聊天
function createNewChat() {
  const newChat: Chat = {
    id: Date.now(),
    title: '新对话',
    messages: [],
    lastTime: Date.now()
  };
  chatHistory.value.unshift(newChat);
  currentChatIndex.value = 0;
  saveChatHistory();
}

// 切换聊天
function switchChat(index: number) {
  currentChatIndex.value = index;
}

// 更新聊天标题
function updateChatTitle(chatIndex: number, firstMessage: string) {
  const chat = chatHistory.value[chatIndex];
  if (!chat.title || chat.title === '新对话') {
    // 使用第一条消息的前15个字符作为标题
    chat.title = firstMessage.slice(0, 15) + (firstMessage.length > 15 ? '...' : '');
  }
}

// 格式化时间
function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  
  // 如果是今天的消息，只显示时间
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
  
  // 否则显示日期和时间
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) + ' ' + 
         date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
    }
  });
}

// 提交查询
async function handleQuery() {
  if (!currentQuery.value.trim() || loading.value) {
    return;
  }
  
  // 添加用户消息
  const userMessage: Message = {
    role: 'user',
    content: currentQuery.value,
    time: Date.now(),
    fromKg: true
  };
  
  currentChat.value.messages.push(userMessage);
  currentChat.value.lastTime = Date.now();
  
  // 如果是第一条消息，更新聊天标题
  if (currentChat.value.messages.length === 1) {
    updateChatTitle(currentChatIndex.value, userMessage.content);
  }
  
  const queryText = currentQuery.value;
  currentQuery.value = '';
  loading.value = true;
  
  scrollToBottom();
  
  try {
    // 使用POST请求获取回答
    const response = await Http.post('/api/ai/inference', {
      question: queryText  // 修改为question参数，与后端接口匹配
    });
    
    console.log('API响应数据:', response); // 输出完整响应，便于调试
    
    // 检查响应结构，适配后端API返回格式
    if (response && (response.success || response.code === 200)) {
      // 获取答案、实体和知识图谱数据
      const data = response.data || response;
      const answerText = data.answer || response.answer || '无法获取回答';
      const entities = data.entities || response.entities || [];
      const kgData = data.kg_data || response.kg_data || { nodes: [], lines: [] };
      // 使用格式化好的关系文本，不再尝试JSON解析处理
      const relationsText = data.relations_text || response.relations_text || '';
      
      console.log('解析后数据:', { answerText, entities, kgData, relationsText });
      
      // 提取思考过程和推理结论
      let thinking = '';
      let mainAnswer = answerText;
      
      // 首先尝试提取<think>标签中的内容
      const thinkMatch = answerText.match(/<think>([\s\S]*?)<\/think>/);
      if (thinkMatch && thinkMatch[1]) {
        // 提取思考过程部分
        thinking = thinkMatch[1].trim();
        
        // 提取推理结论 - 在</think>之后的内容
        const conclusionPart = answerText.split('</think>')[1];
        if (conclusionPart) {
          // 查找推理结论标题，提取后面的内容
          const conclusionMatch = conclusionPart.match(/4\.\s*推理结论:([\s\S]*)/);
          if (conclusionMatch && conclusionMatch[1]) {
            mainAnswer = conclusionMatch[1].trim();
          } else {
            // 如果没找到明确的推理结论标题，就使用</think>后的所有内容
            mainAnswer = conclusionPart.trim();
          }
        }
      } else {
        // 尝试匹配<思考过程>标签 (向后兼容)
        const thinkingMatch = answerText.match(/<思考过程>([\s\S]*?)<\/思考过程>/);
        if (thinkingMatch && thinkingMatch[1]) {
          // 提取思考过程部分
          thinking = thinkingMatch[1].trim();
          
          // 提取推理结论 - 在</思考过程>之后的内容
          const conclusionPart = answerText.split('</思考过程>')[1];
          if (conclusionPart) {
            // 查找推理结论标题，提取后面的内容
            const conclusionMatch = conclusionPart.match(/4\.\s*推理结论:([\s\S]*)/);
            if (conclusionMatch && conclusionMatch[1]) {
              mainAnswer = conclusionMatch[1].trim();
            } else {
              // 如果没找到明确的推理结论标题，就使用</思考过程>后的所有内容
              mainAnswer = conclusionPart.trim();
            }
          }
        } else {
          // 如果没有标签，尝试按旧格式提取
          const thinkingSections = answerText.split(/(?=\d+\.\s+(?:问题理解|实体分析|关系分析|推理结论):)/g)
            .filter(part => part.trim().length > 0);
          
          if (thinkingSections.length >= 4) {
            // 找到结构化的思考过程
            const conclusionMatch = answerText.match(/(\d+\.\s+推理结论:[\s\S]*?)$/);
            
            if (conclusionMatch && conclusionMatch[1]) {
              // 提取结论
              mainAnswer = conclusionMatch[1].replace(/^\d+\.\s+推理结论:\s*/, '').trim();
              
              // 提取思考过程
              thinking = answerText.substring(0, answerText.indexOf(conclusionMatch[1])).trim();
            } else {
              thinking = answerText;
              mainAnswer = '无法提取推理结论，请查看思考过程了解详情。';
            }
          }
        }
      }
      
      // 将提取出的思考过程放入数组，保留原始格式
      const thinkingParts = thinking ? [thinking] : [];
      
      // 收到回答后创建AI消息
      const newMessage: Message = {
        role: 'assistant',
        content: mainAnswer,
        time: Date.now(),
        // 优先使用后端返回的格式化文本
        kgContext: relationsText || '',
        kg_data: kgData, // 单独存储原始的kg_data
        thinking: thinkingParts, // 现在我们只传递一个完整的思考过程
        fromKg: kgData && (kgData.nodes.length > 0 || kgData.lines.length > 0),
        entities: entities
      };
      
      // 添加AI消息到对话
      currentChat.value.messages.push(newMessage);
    } else {
      // 处理错误响应
      const errorMsg = response?.error || response?.msg || '推理请求失败，请稍后再试';
      console.error('API响应错误:', errorMsg);
      
      const errorMessage: Message = {
        role: 'assistant',
        content: errorMsg,
        time: Date.now(),
        fromKg: false
      };
      currentChat.value.messages.push(errorMessage);
    }
    
    currentChat.value.lastTime = Date.now();
    loading.value = false;
    scrollToBottom();
  } catch (error) {
    console.error('推理请求失败:', error);
    
    // 创建错误消息
    const errorMessage: Message = {
      role: 'assistant',
      content: '推理请求发生错误，请稍后再试',
      time: Date.now(),
      fromKg: false
    };
    
    // 添加错误消息到对话
    currentChat.value.messages.push(errorMessage);
    currentChat.value.lastTime = Date.now();
    
    loading.value = false;
    scrollToBottom();
  }
}

// 监听消息变化，自动保存聊天历史
watch(() => chatHistory.value, () => {
  saveChatHistory();
}, { deep: true });

// 监听消息变化，自动滚动到底部
watch(() => currentChat.value.messages.length, () => {
  scrollToBottom();
});

// 监听聊天切换
watch(currentChatIndex, () => {
  scrollToBottom();
});

// 监听窗口大小变化
function handleResize() {
  isMobileView.value = window.innerWidth < 768;
  
  // 如果侧边栏已锁定，则不改变其状态
  if (!isSidebarLocked.value) {
    // 移除自动折叠侧边栏的逻辑，改为使用初始状态
    if (window.innerWidth < 768) {
      // 在小屏幕上根据初始状态决定是否显示侧边栏
      showSidebar.value = initialSidebarState.value && isMobileView.value;
    } else {
      // 在大屏幕上保持侧边栏状态
      showSidebar.value = initialSidebarState.value;
    }
  }
}

// 组件挂载时添加窗口大小监听
onMounted(() => {
  loadChatHistory();
  scrollToBottom();
  window.addEventListener('resize', handleResize);
  
  // 设置初始侧边栏状态
  initialSidebarState.value = true;
  showSidebar.value = window.innerWidth >= 768 ? true : false;
  
  // 阻止知识图谱相关元素的点击事件冒泡
  const preventKgEvents = () => {
    const kgElements = document.querySelectorAll('.kg-visualization, .kg-graph-wrapper, .kg-graph-container, .kg-graph-placeholder');
    kgElements.forEach(el => {
      el.addEventListener('click', (e) => e.stopPropagation());
    });
  };
  
  // 初次加载和每次DOM更新后都尝试添加事件处理
  nextTick(preventKgEvents);
  setInterval(preventKgEvents, 1000); // 每秒检查一次并添加事件处理
});

// 组件卸载时移除窗口大小监听
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
});

// 删除聊天
function deleteChat(index: number) {
  if (chatHistory.value.length <= 1) {
    // 如果只有一个聊天，清空它而不是删除
    chatHistory.value[0].messages = [];
    chatHistory.value[0].title = '新对话';
    chatHistory.value[0].lastTime = Date.now();
  } else {
    // 删除指定的聊天
    chatHistory.value.splice(index, 1);
    
    // 如果删除的是当前聊天，则切换到第一个聊天
    if (index === currentChatIndex.value) {
      currentChatIndex.value = 0;
    } 
    // 如果删除的聊天在当前聊天之前，需要调整索引
    else if (index < currentChatIndex.value) {
      currentChatIndex.value--;
    }
  }
  
  saveChatHistory();
}

// 导出对话内容到Markdown
function exportToMarkdown() {
  if (currentChat.value.messages.length === 0) {
    alert('当前对话为空，无法导出');
    return;
  }
  
  try {
    // 构建Markdown内容
    let markdownContent = `# ${currentChat.value.title || '对话记录'}\n\n`;
    markdownContent += `导出时间: ${formatTime(Date.now())}\n\n`;
    
    // 添加每条消息
    currentChat.value.messages.forEach((message, index) => {
      const role = message.role === 'user' ? '用户' : 'AI助手';
      const time = formatTime(message.time);
      
      markdownContent += `## ${role} (${time})\n\n`;
      
      // 如果是AI消息且有思考过程，添加思考过程
      if (message.role === 'assistant' && message.thinking && message.thinking.length > 0) {
        markdownContent += '### 思考过程\n\n';
        message.thinking.forEach((think, i) => {
          // 将思考过程转换为Markdown引用格式
          // 处理每一行，在每行前添加>符号
          const thinkLines = think.split('\n');
          const quotedThink = thinkLines.map(line => `> ${line}`).join('\n');
          markdownContent += `${quotedThink}\n\n`;
        });
      }
      
      // 添加消息内容
      markdownContent += `${message.content}\n\n`;
      
      // 如果是AI消息且有知识图谱上下文，添加知识图谱信息
      if (message.role === 'assistant' && message.kgContext) {
        markdownContent += '### 知识图谱参考信息\n\n';
        markdownContent += '```\n';
        markdownContent += message.kgContext;
        markdownContent += '\n```\n\n';
      }
      
      // 添加分隔线（除了最后一条消息）
      if (index < currentChat.value.messages.length - 1) {
        markdownContent += '---\n\n';
      }
    });
    
    console.log("准备导出Markdown内容，长度:", markdownContent.length);
    
    // 创建Blob对象
    const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
    
    // 创建下载链接
    const url = URL.createObjectURL(blob);
    
    // 设置文件名 (使用对话标题和日期时间)
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0]; // 格式: YYYY-MM-DD
    const fileName = `${currentChat.value.title || '对话记录'}_${dateStr}.md`;
    
    // 使用更可靠的下载方法
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    link.style.display = 'none';
    document.body.appendChild(link);
    
    // 点击并移除
    console.log("触发下载，文件名:", fileName);
    link.click();
    
    // 延迟移除元素和URL，确保浏览器有足够时间处理下载
    setTimeout(() => {
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      console.log("下载链接已清理");
      
      // 显示成功消息
      showExportSuccess.value = true;
      setTimeout(() => {
        showExportSuccess.value = false;
      }, 2000);
    }, 100);
  } catch (error) {
    console.error("导出对话到Markdown失败:", error);
    alert(`导出失败: ${error.message || '未知错误'}`);
  }
}

// 点击实体标签时询问关于该实体的问题
function askAboutEntity(entity: string) {
  // 构建关于实体的问题
  currentQuery.value = `请告诉我关于${entity}的历史沿革信息`;
  
  // 自动提交查询
  nextTick(() => {
    handleQuery();
  });
}

// 从消息中获取知识图谱数据
function getKgData(message: Message) {
  try {
    // 检查消息中是否直接包含kg_data属性
    if (message.kg_data) {
      return message.kg_data;
    }
    
    // 检查消息的kgContext是否是JSON字符串
    if (message.kgContext) {
      // 尝试解析JSON，如果失败则认为是格式化文本而非JSON
      try {
        const parsed = JSON.parse(message.kgContext);
        if (parsed && typeof parsed === 'object' && (parsed.nodes || parsed.lines)) {
          return parsed;
        }
      } catch (jsonError) {
        console.log('kgContext不是有效的JSON格式，可能是格式化文本');
      }
    }
  } catch (e) {
    console.error('解析知识图谱数据失败:', e);
  }
  
  // 返回空数据结构
  return { nodes: [], lines: [] };
}

// 渲染知识图谱上下文为Markdown
function renderKgContextMarkdown(context: string): string {
  if (!context) return '';
  
  // 尝试解析为JSON并转换为表格
  try {
    const jsonData = JSON.parse(context);
    if (typeof jsonData === 'object') {
      // 检查是否包含nodes和lines（知识图谱数据结构）
      if (jsonData.nodes && Array.isArray(jsonData.nodes)) {
        return renderJsonTableMarkdown(jsonData);
      }
      
      // 一般JSON对象转表格
      return jsonObjectToMarkdownTable(jsonData);
    }
  } catch (e) {
    // 解析失败，作为普通文本处理
    console.log('非JSON格式，按普通文本处理');
  }
  
  // 不是有效的JSON或无法转换为表格，直接渲染为Markdown
  return md.render(context);
}

// 将JSON对象转换为Markdown表格
function jsonObjectToMarkdownTable(json: any): string {
  // 处理非对象或空对象
  if (!json || typeof json !== 'object' || Array.isArray(json) && json.length === 0) {
    return md.render('*无有效数据*');
  }
  
  // 处理数组
  if (Array.isArray(json)) {
    // 提取所有可能的键
    const allKeys = new Set<string>();
    json.forEach(item => {
      if (item && typeof item === 'object') {
        Object.keys(item).forEach(key => allKeys.add(key));
      }
    });
    
    const keys = Array.from(allKeys);
    if (keys.length === 0) {
      // 数组包含的不是对象
      let tableContent = '数组内容：\n\n';
      json.forEach((item, index) => {
        tableContent += `${index+1}. ${String(item)}\n`;
      });
      return md.render(tableContent);
    }
    
    // 构建表头
    let table = '| # | ' + keys.join(' | ') + ' |\n';
    table += '|' + '---|'.repeat(keys.length + 1) + '\n';
    
    // 构建表行
    json.forEach((item, index) => {
      table += `| ${index+1} |`;
      keys.forEach(key => {
        const value = item[key];
        if (value === undefined || value === null) {
          table += ' - |';
        } else if (typeof value === 'object') {
          table += ` ${JSON.stringify(value).substr(0, 20)}... |`;
        } else {
          table += ` ${String(value)} |`;
        }
      });
      table += '\n';
    });
    
    return md.render(table);
  }
  
  // 处理普通对象
  let table = '| 属性 | 值 |\n|---|---|\n';
  
  Object.entries(json).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      table += `| ${key} | - |\n`;
    } else if (typeof value === 'object') {
      if (Array.isArray(value) && value.length > 0) {
        table += `| ${key} | ${value.length}个项目 |\n`;
      } else {
        table += `| ${key} | ${JSON.stringify(value).substr(0, 30)}... |\n`;
      }
    } else {
      table += `| ${key} | ${String(value)} |\n`;
    }
  });
  
  return md.render(table);
}

// 渲染知识图谱数据为Markdown表格
function renderJsonTableMarkdown(jsonData: any): string {
  let result = '';
  
  // 添加节点表格
  if (jsonData.nodes && jsonData.nodes.length > 0) {
    result += '## 实体节点\n\n';
    result += '| # | ID | 名称 | 类型 |\n';
    result += '|---|---|---|---|\n';
    
    jsonData.nodes.forEach((node: any, index: number) => {
      const id = node.id || '-';
      const name = node.name || node.label || '-';
      const type = node.type || node.category || '-';
      result += `| ${index+1} | ${id} | ${name} | ${type} |\n`;
    });
    
    result += '\n\n';
  }
  
  // 添加关系表格
  if (jsonData.lines && jsonData.lines.length > 0) {
    result += '## 实体关系\n\n';
    result += '| # | 源实体 | 关系 | 目标实体 | 类型 |\n';
    result += '|---|---|---|---|---|\n';
    
    // 创建节点ID到名称的映射
    const nodeMap = new Map();
    if (jsonData.nodes) {
      jsonData.nodes.forEach((node: any) => {
        if (node.id !== undefined && (node.name || node.label)) {
          nodeMap.set(String(node.id), node.name || node.label);
        }
      });
    }
    
    // 添加调试信息
    console.log("节点映射表:", Object.fromEntries([...nodeMap.entries()]));
    console.log("关系数据示例:", jsonData.lines[0]);
    
    jsonData.lines.forEach((line: any, index: number) => {
      // 源和目标节点ID
      const fromId = line.from !== undefined ? line.from : 
                    (line.source !== undefined ? line.source : '-');
      const toId = line.to !== undefined ? line.to : 
                  (line.target !== undefined ? line.target : '-');
      
      // 尝试获取关系文本
      let relationText = '-';
      if (line.text !== undefined && line.text !== '') {
        relationText = line.text;
      } else if (line.relation !== undefined && line.relation !== '') {
        relationText = line.relation;
      } else if (line.label !== undefined && line.label !== '') {
        relationText = line.label;
      } else if (line.name !== undefined && line.name !== '') {
        relationText = line.name;
      }
      
      // 关系类型（是否为推理关系）
      let relationType = '数据库关系';
      if (line.inferred === true) {
        relationType = '推理关系';
      } else if (line.derived_from) {
        relationType = '推理关系';
      } else if (line.rule_id) {
        relationType = '推理关系';
      }
      
      // 获取实体名称
      const sourceName = nodeMap.get(String(fromId)) || String(fromId);
      const targetName = nodeMap.get(String(toId)) || String(toId);
      
      result += `| ${index+1} | ${sourceName} | ${relationText} | ${targetName} | ${relationType} |\n`;
    });
    
    // 添加完整属性信息表格
    result += '\n\n## 关系详细属性\n\n';
    result += '| # | 关系 | 源 → 目标 | 属性信息 |\n';
    result += '|---|---|---|---|\n';
    
    jsonData.lines.forEach((line: any, index: number) => {
      // 获取源和目标ID
      const fromId = line.from !== undefined ? line.from : 
                   (line.source !== undefined ? line.source : '-');
      const toId = line.to !== undefined ? line.to : 
                 (line.target !== undefined ? line.target : '-');
      
      // 获取关系文本
      let relationText = line.text || line.relation || line.label || '-';
      
      // 获取实体名称
      const sourceName = nodeMap.get(String(fromId)) || String(fromId);
      const targetName = nodeMap.get(String(toId)) || String(toId);
      
      // 收集所有属性
      const propPairs = [];
      for (const [key, value] of Object.entries(line)) {
        // 跳过基本属性
        if (['from', 'to', 'source', 'target', 'text', 'relation', 'label'].includes(key)) {
          continue;
        }
        
        // 格式化值
        let formattedValue = value;
        if (typeof value === 'object') {
          formattedValue = JSON.stringify(value).substring(0, 50);
          if (JSON.stringify(value).length > 50) {
            formattedValue += '...';
          }
        }
        
        propPairs.push(`${key}: ${formattedValue}`);
      }
      
      const props = propPairs.length > 0 ? propPairs.join('<br>') : '-';
      result += `| ${index+1} | ${relationText} | ${sourceName} → ${targetName} | ${props} |\n`;
    });
  } else {
    result += '## 实体关系\n\n没有关系数据\n\n';
  }
  
  return md.render(result);
}

// 思考过程渲染函数
function renderThinkingContent(thinkingText: string): string {
  if (!thinkingText) return '';
  
  // 格式化MD内容
  let formattedText = thinkingText;
  
  // 处理标题格式（例如：1. **问题理解**:）
  formattedText = formattedText.replace(/(\d+\.\s*\*\*[^*]+\*\*:)/g, '<h4>$1</h4>');
  
  // 处理子标题和实体标记（例如：- **平江府**:）
  formattedText = formattedText.replace(/(-\s*\*\*[^*]+\*\*:)/g, '<h5>$1</h5>');
  
  // 处理普通加粗文本
  formattedText = formattedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // 处理列表项（以 - 开头的行）
  formattedText = formattedText.replace(/^-\s+([^<].*)/gm, '<div class="list-item">• $1</div>');
  
  // 将换行符转换为<br>标签
  formattedText = formattedText.replace(/\n/g, '<br>');
  
  // 修复在替换后可能出现的多余<br>标签
  formattedText = formattedText.replace(/<\/h4><br>/g, '</h4>');
  formattedText = formattedText.replace(/<\/h5><br>/g, '</h5>');
  formattedText = formattedText.replace(/<\/div><br>/g, '</div>');
  
  // 为代码块添加样式
  formattedText = formattedText.replace(/```([\s\S]*?)```/g, '<pre class="thinking-code"><code>$1</code></pre>');
  
  return formattedText;
}

// 处理回车键事件
function handleEnterKey(event: KeyboardEvent) {
  // 如果按下了Shift键，则允许换行
  if (event.shiftKey) {
    return;
  }
  
  // 否则，阻止默认行为并发送消息
  event.preventDefault();
  handleQuery();
}

// 隐藏实体卡片
function hideEntityCard() {
  showEntityCard.value = false;
}

// 在新消息到达时重置实体卡片显示状态
watch(() => currentChat.value.messages.length, () => {
  if (currentChat.value.messages.length > 0 && 
      currentChat.value.messages[currentChat.value.messages.length-1].role === 'assistant' &&
      currentChat.value.messages[currentChat.value.messages.length-1].entities?.length > 0) {
    showEntityCard.value = true;
  }
});
</script>

<style scoped>
.inference-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
  background-color: #f5f7fa;
}

/* 左侧边栏样式 */
.chat-sidebar {
  width: 250px;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  transition: all 0.3s ease;
  z-index: 100;
  height: 100%;
  box-shadow: 0 0 10px rgba(0,0,0,0.05);
  isolation: isolate; /* 创建新的堆叠上下文 */
  pointer-events: auto !important; /* 强制确保点击事件独立 */
}

/* 侧边栏折叠状态 */
.sidebar-collapsed {
  width: 0;
  padding: 0;
  overflow: hidden;
  border-right: none;
}

/* 移动设备适配 */
@media (max-width: 767px) {
  .chat-sidebar {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    box-shadow: 2px 0 10px rgba(0,0,0,0.1);
    z-index: 1000; /* 增加z-index值确保在最上层 */
  }
  
  /* 添加覆盖层，阻挡其他元素的点击事件影响侧边栏 */
  .sidebar-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.15);
    z-index: 999; /* 低于侧边栏但高于其他内容 */
    display: none; /* 默认隐藏 */
  }
  
  /* 当侧边栏显示时显示覆盖层 */
  .chat-sidebar:not(.sidebar-collapsed) + .chat-content .sidebar-overlay {
    display: block;
  }
  
  .chat-content {
    width: 100%;
    position: relative;
    z-index: 1;
  }
  
  /* 确保知识图谱容器不会影响侧边栏 */
  .kg-graph-container {
    transition: none; /* 移除过渡效果，避免与侧边栏冲突 */
  }
  
  /* 知识图谱展开时确保内容不超出右侧边界 */
  .kg-graph-placeholder {
    max-width: 100%;
    overflow-x: auto;
  }
}

/* 添加头部左侧区域样式 */
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 折叠按钮样式 */
.fold-button {
  cursor: pointer;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.fold-button:hover {
  background-color: #f0f9f6;
}

/* 修改右侧聊天内容区域 */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background-color: #fff;
}

/* 添加聊天头部 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #eee;
  background-color: #fff;
  height: 42px;
  flex-shrink: 0;
}

.header-title {
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
}

.chat-item {
  padding: 12px 16px;
  cursor: pointer;
  border-radius: 8px;
  margin: 0 8px 8px 8px;
  background-color: #fff;
  border: 1px solid #eee;
  transition: all 0.3s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.chat-item:hover {
  background-color: #f9f9f9;
  transform: translateY(-2px);
}

.chat-item.active {
  background-color: #e6f7f5;
  border-color: #009688;
  box-shadow: 0 2px 8px rgba(0,150,136,0.1);
}

.chat-item-content {
  flex: 1;
  overflow: hidden;
}

.chat-title {
  font-size: 14px;
  color: #333;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-time {
  font-size: 12px;
  color: #999;
}

.chat-actions {
  opacity: 0;
  transition: opacity 0.3s;
}

.chat-item:hover .chat-actions {
  opacity: 1;
}

.delete-icon {
  cursor: pointer;
}

/* 修改消息包装器，使其占满剩余空间 */
.message-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 修改消息容器样式，增加聊天区域空间 */
.message-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 20px 10px 20px;
  display: flex;
  flex-direction: column;
  position: relative;
}

.message-item {
  display: flex;
  margin-bottom: 24px;
  position: relative;
  max-width: 100%;
}

/* 修改输入容器，固定在底部 */
.input-container {
  padding: 8px 16px;
  background-color: #fff;
  border-top: 1px solid #eee;
  position: relative;
  flex-shrink: 0;
  z-index: 5;
  max-height: 90px;
  display: flex;
  flex-direction: column;
}

.input-textarea-wrapper {
  width: 100%;
  position: relative;
}

/* 恢复按钮组样式 */
.button-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2px;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hint {
  color: #999;
  font-size: 12px;
}

/* 恢复消息样式 */
.user-message {
  flex-direction: row-reverse;
}

.message-avatar {
  margin: 0 12px;
}

.message-content {
  max-width: 80%;
  position: relative;
}

.user-message .message-content {
  background-color: #e6f7f5;
  border-radius: 18px 4px 18px 18px;
  padding: 12px 16px;
  box-shadow: 0 1px 2px rgba(0,150,136,0.1);
}

.ai-message .message-content {
  background-color: #f5f5f5;
  border-radius: 4px 18px 18px 18px;
  padding: 12px 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

/* 消息动画 */
.message-item {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 思考过程样式 */
.thinking-section {
  margin: 12px 0 16px 0;
  border-left: 3px solid #009688;
  position: relative;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: #edf7f5;
  border-top: 1px solid #d1e7dd;
  border-right: 1px solid #d1e7dd;
  border-bottom: 1px solid #d1e7dd;
  margin-bottom: 0;
}

.thinking-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: #009688;
}

.thinking-header-right {
  display: flex;
  align-items: center;
}

.thinking-tag {
  background-color: #009688;
  color: white;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.thinking-content {
  background-color: #f8fbfa;
  padding: 12px 16px;
  margin-top: 0;
  border-right: 1px solid #d1e7dd;
  border-bottom: 1px solid #d1e7dd;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.thinking-content h4 {
  margin: 12px 0 8px 0;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.thinking-content h4:first-child {
  margin-top: 0;
}

.thinking-content h5 {
  margin: 10px 0 6px 0;
  font-size: 14px;
  font-weight: 500;
  color: #444;
}

.thinking-content .list-item {
  margin: 4px 0 4px 12px;
  position: relative;
}

.thinking-content strong {
  font-weight: 600;
  color: #0a5d52;
}

.thinking-code {
  background-color: #f0f0f0;
  padding: 12px;
  border-radius: 4px;
  margin: 10px 0;
  overflow-x: auto;
  font-family: Consolas, Monaco, 'Andale Mono', monospace;
  font-size: 13px;
  line-height: 1.4;
}

/* 思考中动画 */
.thinking-bubble {
  background-color: #f5f5f5;
  border-radius: 4px 18px 18px 18px;
  padding: 12px 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.thinking-animation {
  position: relative;
  display: inline-block;
}

.dot-animation::after {
  content: "...";
  display: inline-block;
  overflow: hidden;
  vertical-align: bottom;
  animation: dotAnimation 1.5s infinite steps(4, end);
  width: 0;
}

@keyframes dotAnimation {
  0% { width: 0; }
  25% { width: 0.25em; }
  50% { width: 0.5em; }
  75% { width: 0.75em; }
  100% { width: 1em; }
}

/* 消息底部样式 */
.message-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.message-actions {
  display: flex;
  gap: 8px;
}

.action-icon {
  cursor: pointer;
  opacity: 0.6;
  transition: all 0.3s;
}

.action-icon:hover {
  opacity: 1;
  transform: scale(1.2);
}

.message-time {
  font-size: 12px;
  color: #999;
}

/* 知识图谱相关样式 */
.kg-reference {
  margin-left: auto;
}

.kg-context {
  margin-top: 10px;
  padding: 10px;
  background-color: #f0f9f6;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  animation: fadeIn 0.3s ease;
}

.ai-notice {
  margin: 10px 0;
  padding: 8px 12px;
  background-color: #fff3e0;
  border-radius: 4px;
  border-left: 3px solid #FF9800;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #E65100;
}

/* 知识图谱可视化样式 */
.kg-visualization {
  margin-top: 15px;
  border-radius: 8px;
  background-color: #f7f9fa;
  overflow: hidden;
  position: relative;
  z-index: 1;
  pointer-events: auto; /* 确保图谱区域有自己的点击事件 */
  isolation: isolate; /* 创建新的堆叠上下文 */
}

.kg-header {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  background-color: #e8f4f4;
  cursor: pointer;
  font-weight: 500;
  color: #009688;
  pointer-events: auto; /* 确保点击事件独立 */
}

.kg-header span {
  margin-left: 8px;
}

.kg-graph-wrapper {
  padding: 15px;
  transition: all 0.3s ease;
  pointer-events: auto; /* 确保点击事件独立 */
}

.kg-graph-container {
  min-height: 300px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto; /* 确保点击事件独立 */
}

.kg-graph-placeholder {
  min-height: 300px;
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  position: relative;
  z-index: 1;
  pointer-events: auto; /* 确保点击事件独立 */
}

.kg-graph {
  width: 100%;
  height: 100%;
  min-height: 300px;
  pointer-events: auto; /* 确保点击事件独立 */
}

/* 添加响应式样式 */
@media screen and (min-width: 768px) {
  .kg-graph-placeholder {
    min-height: 400px;
  }
  
  .kg-graph {
    min-height: 400px;
  }
}

@media screen and (min-width: 1200px) {
  .kg-graph-placeholder {
    min-height: 500px;
  }
  
  .kg-graph {
    min-height: 500px;
  }
}

/* 确保移动设备上知识图谱不会影响侧边栏 */
@media (max-width: 767px) {
  .kg-visualization {
    overflow: visible;
  }
  
  .kg-graph-wrapper {
    padding: 10px;
  }
  
  .kg-graph-placeholder {
    max-width: 100%;
    overflow-x: auto;
  }
}

/* 实体卡片样式 */
.entity-card {
  background-color: #f7f9fa;
  border-radius: 6px;
  margin: 8px 0;
  padding: 8px 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #eee;
}

.entity-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.entity-card-title {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: #009688;
  font-size: 13px;
}

.entity-card-title span {
  margin-left: 4px;
}

.entity-card-close {
  cursor: pointer;
  opacity: 0.6;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.entity-card-close:hover {
  opacity: 1;
  background-color: #eee;
}

.entity-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.entity-tag {
  cursor: pointer;
  transition: transform 0.2s;
  font-size: 12px;
  padding: 1px 8px;
}

.entity-tag:hover {
  transform: scale(1.05);
}

/* 空聊天状态 */
.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.empty-icon {
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  margin-bottom: 24px;
}

/* 快捷提示样式 */
.quick-prompts {
  width: 100%;
  max-width: 500px;
  padding: 16px;
  margin-top: 16px;
}

.prompt-title {
  margin-bottom: 12px;
  color: #666;
  font-size: 14px;
  text-align: center;
}

.prompt-items {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.prompt-item {
  padding: 8px 16px;
  background-color: #f0f9f6;
  color: #009688;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
  border: 1px dashed #009688;
}

.prompt-item:hover {
  background-color: #009688;
  color: white;
  border-style: solid;
  transform: translateY(-2px);
}

/* 复制成功提示 */
.copy-success-tip {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 150, 136, 0.8);
  color: white;
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 16px;
  animation: fadeInOut 2s ease;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
  15% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  80% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
}

/* Markdown样式 */
.markdown-body {
  line-height: 1.6;
  word-break: break-word;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin-bottom: 10px;
  width: 100%;
  overflow: auto;
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
  vertical-align: top;
  word-break: break-word;
}

.markdown-body :deep(table th) {
  background-color: #f2f8f6;
  font-weight: 600;
  text-align: left;
  color: #009688;
}

.markdown-body :deep(table tr) {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-body :deep(table tr:nth-child(2n)) {
  background-color: #f6faf9;
}

/* 输入框相关样式 */
.clear-button {
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.3s;
}

.clear-button:hover {
  opacity: 1;
}

/* 特定于表格的样式 */
.markdown-body :deep(table td:nth-child(5)) {
  font-weight: 500;
}

.markdown-body :deep(table td:last-child) {
  max-width: 350px;
}

/* 添加紧凑型输入框样式 */
.compact-textarea {
  font-size: 14px;
  line-height: 1.5;
}

.compact-textarea :deep(.layui-textarea) {
  padding: 6px 8px;
  padding-right: 45px; /* 为发送按钮留出空间 */
  min-height: 22px !important;
  line-height: 1.5;
  resize: none;
  border-radius: 20px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.05);
  transition: all 0.3s;
}

.compact-textarea :deep(.layui-textarea:focus) {
  box-shadow: 0 2px 8px rgba(0,150,136,0.15);
}

/* 发送按钮样式 */
.send-button {
  position: absolute;
  right: 10px;
  bottom: 6px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f9f6;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  z-index: 10;
}

.send-button:hover {
  background-color: #e0f2f1;
  transform: translateY(-2px);
  box-shadow: 0 3px 5px rgba(0,0,0,0.15);
}

.send-button.disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.export-button {
  cursor: pointer;
  transition: all 0.3s;
}

.export-button:hover {
  transform: scale(1.2);
  color: #00b5a0;
}
</style> 