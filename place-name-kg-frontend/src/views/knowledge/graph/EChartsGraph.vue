<template>
  <div class="echarts-graph">
    <div ref="chartRef" class="chart-container"></div>
    
    <!-- 图谱功能小工具按钮组 -->
    <div class="graph-tools">
      <!-- 图例控制按钮 -->
      <div class="tool-button" @click="toggleLegendDisplay" :class="{ 'active': showLegend }">
        <i class="tool-icon">📊</i>
        <div class="tool-tooltip">{{ showLegend ? '隐藏图例' : '显示图例' }}</div>
      </div>
      
      <!-- 节点类型按钮 -->
      <div class="tool-button" @click="openNodeTypeMenu">
        <i class="tool-icon">📋</i>
        <div class="tool-tooltip">节点类型</div>
      </div>
      
      <!-- 关系控制按钮 -->
      <div class="tool-button" @click="openRelationMenu">
        <i class="tool-icon">🔗</i>
        <div class="tool-tooltip">关系控制</div>
      </div>
    </div>
    
    <!-- 关系控制菜单 -->
    <div v-if="showRelationMenu" class="relation-menu">
      <div class="menu-header">
        <div class="menu-title">关系控制</div>
        <div class="menu-close" @click="closeRelationMenu">×</div>
      </div>
      
      <div class="relation-actions">
        <button class="relation-btn" @click="toggleShowAllRelations">
          {{ showAllRelations ? '隐藏全部关系' : '显示全部关系' }}
        </button>
        
        <button v-if="expandedNodes.size > 0" class="relation-btn" @click="collapseAllRelations">
          收起所有已展开关系
        </button>
      </div>
      
      <div v-if="expandedNodes.size > 0" class="expanded-nodes-list">
        <div class="list-header">已展开的节点 ({{ expandedNodes.size }})</div>
        <div class="expanded-node-items">
          <div v-for="nodeId in Array.from(expandedNodes)" :key="nodeId" class="expanded-node-item">
            <span class="node-name">{{ getNodeName(nodeId) }}</span>
            <span class="collapse-btn" @click="collapseNode(nodeId)">收起</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 节点类型弹出菜单 -->
    <div v-if="showNodeTypeMenu" class="node-type-menu">
      <div class="menu-header">
        <div class="menu-title">节点类型</div>
        <div class="menu-close" @click="closeNodeTypeMenu">×</div>
      </div>
      
      <div class="menu-content">
        <div class="menu-select-all">
          <button class="mini-btn" v-if="isAllSelected" @click="unselectAll">
            取消全选
          </button>
          <button class="mini-btn" v-if="!isAllSelected" @click="selectAll">
            全选
          </button>
        </div>
        
        <div class="type-controls">
          <div 
            v-for="type in nodeTypes" 
            :key="type" 
            class="legend-item"
            @click="toggleNodeType(type)"
          >
            <div class="color-dot" :style="{ backgroundColor: typeColors[type]?.color || '#A9A9A9' }"></div>
            <div class="legend-text">{{ type }}</div>
            <div class="legend-checkbox" :class="{ 'checked': selectedNodeTypes.includes(type) }"></div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 节点菜单弹框 -->
    <div v-if="showMenu" class="node-menu-popup" :style="{ 
      left: menuPosition.x + 'px', 
      top: menuPosition.y + 'px'
    }">
      <div class="popup-header">
        <div class="popup-title">{{ selectedNode?.name }}</div>
        <div class="popup-type">{{ selectedNode?.category }}</div>
        <div class="popup-close" @click="closeMenu">×</div>
      </div>
      <div class="popup-actions">
        <div class="popup-button expand" @click="handleExpandRelations">
          <div class="popup-icon">↔</div>
          <div class="popup-text">{{ expandedNodes.has(selectedNode?.id) ? '收起关系' : '展开关系' }}</div>
        </div>
        <div class="popup-button view" @click="handleViewProperties">
          <div class="popup-icon">👁</div>
          <div class="popup-text">查看属性</div>
        </div>
      </div>
    </div>
    
    <!-- 节点属性对话框 -->
    <lay-layer v-model="propertyDialogVisible" title="节点属性" :area="['600px', '500px']">
      <div class="property-container">
        <div class="property-header">
          <div class="node-title">{{ nodeProperties.name }}</div>
          <div class="node-type">{{ nodeProperties.type }}</div>
        </div>
        
        <div class="property-content">
          <div v-for="(value, key) in nodeProperties" :key="key" class="property-item" v-if="!['id', 'name', 'type'].includes(key)">
            <div class="property-key">{{ key }}</div>
            <div class="property-value">{{ value }}</div>
          </div>
        </div>
      </div>
    </lay-layer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, reactive, computed } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import Http from "@/api/http";

const props = defineProps({
  data: {
    type: Object,
    default: () => ({
      nodes: [],
      lines: []
    })
  }
})

const emit = defineEmits(['node-expanded'])

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const nodeTypes = ref<string[]>([])
// 是否显示所有关系
const showAllRelations = ref(true)
// 存储已选择的节点类型
const selectedNodeTypes = reactive<string[]>([])
// 存储已展开的节点ID
const expandedNodes = reactive(new Set<string>())
// 当前选中的节点
const selectedNode = ref<any>(null)
// 选项菜单的位置
const menuPosition = ref({ x: 0, y: 0 })
// 是否显示选项菜单
const showMenu = ref(false)
// 节点属性对话框
const propertyDialogVisible = ref(false)
const nodeProperties = ref<any>({})
// 节点大小
const nodeSize = ref(0)
// 是否显示图例
const showLegend = ref(true)
// 显示节点类型菜单
const showNodeTypeMenu = ref(false)
// 显示关系控制菜单
const showRelationMenu = ref(false)
// 判断是否全选状态
const isAllSelected = computed(() => {
  return selectedNodeTypes.length === nodeTypes.value.length
})

// 获取节点类型列表
const fetchNodeTypes = async () => {
  try {
    const response = await Http.get('/api/node_types')
    if (response.code === 200) {
      nodeTypes.value = response.data
      // 初始化时设置所有节点类型为选中状态
      selectedNodeTypes.splice(0, selectedNodeTypes.length, ...nodeTypes.value)
    }
  } catch (error) {
    console.error('获取节点类型失败：', error)
  }
}

// 节点类型颜色映射
const typeColors = {
  '府': {
    color: '#91cc75',
    size: 45,
    borderColor: '#a8d9ae',
    gradient: ['#91cc75', '#a8d9ae']
  },
  '县': {
    color: '#5470c6',
    size: 42,
    borderColor: '#6a85d1',
    gradient: ['#5470c6', '#6a85d1']
  },
  '行政区': {
    color: '#fac858',
    size: 40,
    borderColor: '#fbd47a',
    gradient: ['#fac858', '#fbd47a']
  },
  '地级市': {
    color: '#ee6666',
    size: 45,
    borderColor: '#f18585',
    gradient: ['#ee6666', '#f18585']
  },
  '县级市': {
    color: '#73c0de',
    size: 42,
    borderColor: '#8ccde4',
    gradient: ['#73c0de', '#8ccde4']
  },
  '市辖区': {
    color: '#fc8452',
    size: 40,
    borderColor: '#fd9b74',
    gradient: ['#fc8452', '#fd9b74']
  },
  '郡': {
    color: '#9a60b4',
    size: 38,
    borderColor: '#ad7ac2',
    gradient: ['#9a60b4', '#ad7ac2']
  },
  '乡': {
    color: '#ea7ccc',
    size: 35,
    borderColor: '#ee96d6',
    gradient: ['#ea7ccc', '#ee96d6']
  },
  '监察区': {
    color: '#ff69b4',
    size: 35,
    borderColor: '#ff87c2',
    gradient: ['#ff69b4', '#ff87c2']
  },
  '地域': {
    color: '#3ba272',
    size: 40,
    borderColor: '#52b388',
    gradient: ['#3ba272', '#52b388']
  },
  '省': {
    color: '#4169e1',
    size: 48,
    borderColor: '#5a7ee6',
    gradient: ['#4169e1', '#5a7ee6']
  },
  '临时政区': {
    color: '#00ffff',
    size: 35,
    borderColor: '#33ffff',
    gradient: ['#00ffff', '#33ffff']
  },
  '路': {
    color: '#808080',
    size: 38,
    borderColor: '#999999',
    gradient: ['#808080', '#999999']
  },
  '州': {
    color: '#8b4513',
    size: 42,
    borderColor: '#a35b1a',
    gradient: ['#8b4513', '#a35b1a']
  },
  '村': {
    color: '#556b2f',
    size: 35,
    borderColor: '#6b853b',
    gradient: ['#556b2f', '#6b853b']
  },
  '人民公社': {
    color: '#483d8b',
    size: 38,
    borderColor: '#5a4ea2',
    gradient: ['#483d8b', '#5a4ea2']
  },
  '政权': {
    color: '#2f4f4f',
    size: 40,
    borderColor: '#3b6262',
    gradient: ['#2f4f4f', '#3b6262']
  },
  '军镇': {
    color: '#800000',
    size: 38,
    borderColor: '#991a1a',
    gradient: ['#800000', '#991a1a']
  },
  '道': {
    color: '#9370db',
    size: 40,
    borderColor: '#a88ce1',
    gradient: ['#9370db', '#a88ce1']
  },
  '王朝': {
    color: '#ff8c00',
    size: 45,
    borderColor: '#ffa333',
    gradient: ['#ff8c00', '#ffa333']
  }
}

// 初始化图表
const initChart = () => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', handleResize)
    
    // 添加节点点击事件
    chart.on('click', function(params) {
      if (params.dataType === 'node') {
        // 如果点击的是当前选中的节点，则关闭菜单
        if (selectedNode.value && selectedNode.value.id === params.data.id) {
          showMenu.value = false
          selectedNode.value = null
          return
        }
        
        // 保存选中的节点
        selectedNode.value = params.data
        // 设置菜单位置 - 直接使用点击位置，不再进行坐标转换
        menuPosition.value = {
          x: params.event.offsetX,
          y: params.event.offsetY
        }
        // 获取节点大小
        nodeSize.value = params.data.symbolSize || 40
        showMenu.value = true
      } else {
        // 点击空白处关闭菜单
        showMenu.value = false
        selectedNode.value = null
      }
      
      // 点击图表时关闭节点类型菜单
      if (showNodeTypeMenu.value) {
        showNodeTypeMenu.value = false
      }
    })
    
    // 添加节点拖拽事件
    chart.on('graphRoam', function() {
      // 在用户手动平移或缩放图谱时，不再进行处理
      // 允许用户自由操作图谱
    })
    
    // 定义拖拽状态变量
    let isDragging = false
    let draggedNodeId = null
    
    // 添加节点拖拽开始事件
    chart.on('dragstart', function(params) {
      // 设置当前节点为拖拽状态
      if (params.dataType === 'node') {
        isDragging = true
        draggedNodeId = params.data.id
        
        // 添加视觉反馈
        document.body.style.cursor = 'grabbing'
        
        // 突出显示当前节点
        chart.setOption({
          series: [{
            type: 'graph',
            data: [{
              id: params.data.id,
              itemStyle: {
                shadowBlur: 20,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }]
          }]
        }, {replaceMerge: false})
      }
    })
    
    // 添加节点拖拽过程事件
    chart.on('drag', function(params) {
      if (params.dataType === 'node' && isDragging) {
        // 实时更新节点位置，提升拖动流畅度
        chart.setOption({
          series: [{
            type: 'graph',
            data: [{
              id: params.data.id,
              x: params.event.offsetX,
              y: params.event.offsetY,
              fixed: true // 拖拽过程中固定位置
            }]
          }]
        }, {replaceMerge: false})
      }
    })
    
    // 添加节点拖拽结束事件
    chart.on('dragend', function(params) {
      // 拖拽结束后固定节点位置
      if (params.dataType === 'node' && isDragging && draggedNodeId === params.data.id) {
        isDragging = false
        draggedNodeId = null
        
        // 恢复鼠标样式
        document.body.style.cursor = 'auto'
        
        // 取消节点的阴影效果
        chart.setOption({
          series: [{
            type: 'graph',
            data: [{
              id: params.data.id,
              itemStyle: {
                shadowBlur: 0 // 移除拖动时的阴影效果
              }
            }]
          }]
        }, {replaceMerge: false})  // 不完全替换，仅更新指定项
      }
    })
    
    // 添加document点击事件以关闭节点类型菜单
    document.addEventListener('click', handleDocumentClick)
  }
}

// 处理窗口大小变化
const handleResize = () => {
  chart?.resize()
}

// 切换显示所有关系
const toggleShowAllRelations = () => {
  showAllRelations.value = !showAllRelations.value
  
  // 如果切换到隐藏关系模式，清空所有已展开的节点
  if (!showAllRelations.value) {
    expandedNodes.clear()
  }
  
  updateChart()
}

// 添加辅助函数来处理连线
const getProcessedLinks = (data: any) => {
  if (!data || !data.nodes || !data.lines) return []
  
  // 节点ID映射表（用于快速查找）
  const nodeMap = new Map(data.nodes.map((node: any) => [String(node.id), node]))
  
  // 处理连线数据
  return data.lines.filter(line => {
    return nodeMap.has(String(line.from)) && nodeMap.has(String(line.to))
  }).map((line, index) => {
    // 建立多节点间的连接线，避免重叠
    let lineColor = '#999' // 默认连接线颜色
    let curveness = 0 // 默认弧度

    // 检查是否存在相同起点和终点的多条连接线
    const parallelLinks = data.lines.filter(
      l => (l.from === line.from && l.to === line.to) || (l.from === line.to && l.to === line.from)
    )

    if (parallelLinks.length > 1) {
      // 计算当前连接线在平行连接线中的位置
      const linkIndex = parallelLinks.findIndex(
        l => l.from === line.from && l.to === line.to && l.text === line.text
      )
      
      // 增加基础曲率以减少线条交叉
      const baseCurvature = 0.4
      
      // 检查当前线的方向是否与第一条线相反
      const firstLink = parallelLinks[0]
      const isOppositeDirection = (firstLink.from === line.to && firstLink.to === line.from)
      
      // 修改弯曲逻辑：考虑方向因素
      if (parallelLinks.length === 2) {
        if (isOppositeDirection) {
          curveness = linkIndex % 2 === 0 ? -baseCurvature : baseCurvature
        } else {
          curveness = linkIndex % 2 === 0 ? baseCurvature : -baseCurvature
        }
      } else {
        const curveStep = baseCurvature / Math.ceil(parallelLinks.length / 2)
        const magnitude = Math.ceil((linkIndex + 1) / 2) * curveStep
        
        if (isOppositeDirection) {
          curveness = linkIndex % 2 === 0 ? -magnitude : magnitude
        } else {
          curveness = linkIndex % 2 === 0 ? magnitude : -magnitude
        }
      }

      // 根据关系类型设置颜色
      if (line.relation_category === '演变类' || 
          (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
            line.text.includes('更名') || line.text.includes('改置') || 
            line.text.includes('设置') || line.text.includes('撤销')))) {
        lineColor = '#e63946'
        curveness = curveness > 0 ? curveness + 0.05 : curveness - 0.05
      } else if (line.relation_category === '所属类' ||
                (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                  line.text.includes('辖域')))) {
        lineColor = '#457b9d'
      }
    } else {
      // 为单一连接线也设置微弱的曲率，帮助减少交叉
      curveness = 0.05
      
      if (line.relation_category === '演变类' || 
          (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
            line.text.includes('更名') || line.text.includes('改置') || 
            line.text.includes('设置') || line.text.includes('撤销')))) {
        lineColor = '#e63946'
      } else if (line.relation_category === '所属类' ||
                (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                  line.text.includes('辖域')))) {
        lineColor = '#457b9d'
      }
    }
    
    const showLabel = true // 总是显示标签

    return {
      source: String(line.from),
      target: String(line.to),
      value: line.text,
      lineStyle: {
        color: lineColor,
        curveness: curveness,
        width: 1.5,
        opacity: 0.7
      },
      label: {
        show: showLabel,
        formatter: line.text,
        fontSize: 9, // 从11减小到9
        color: '#333',
        backgroundColor: 'transparent',
        padding: [2, 3], // 从[3, 5]减小到[2, 3]
        borderRadius: 2, // 从3减小到2
        distance: 3,
        align: 'center',
        verticalAlign: 'middle',
        position: 'middle'
      },
      edgeLabel: {
        show: true,
        formatter: function(params) {
          return params.data.value;
        },
        fontSize: 8, // 从10减小到8
        color: '#333', // 更深的文字颜色
        padding: [1, 3], // 从[2, 4]减小到[1, 3]
        backgroundColor: 'transparent', // 将背景色设置为透明
        textBorderColor: 'rgba(255, 255, 255, 0.8)', // 添加白色描边提高可读性
        textBorderWidth: 2, // 描边宽度保持不变以确保可读性
        distance: 3 // 添加距离参数，使文字更贴近连线
      }
    }
  })
}

// 更新图表数据
const updateChart = () => {
  if (chart && props.data) {
    const option = getChartOption(props.data)
    chart.setOption(option)
  }
}

// 监听数据变化
watch(() => props.data, () => {
  updateChart()
}, { deep: true })

// 处理document点击事件，关闭菜单
const handleDocumentClick = (event: MouseEvent) => {
  // 检查点击事件是否发生在节点类型菜单或工具按钮之外
  const isClickOutsideNodeTypeMenu = showNodeTypeMenu.value && 
    !event.composedPath().some(el => {
      const element = el as HTMLElement
      return element.classList && 
      (element.classList.contains('node-type-menu') || 
       element.classList.contains('tool-button') ||
       element.classList.contains('tool-icon') ||
       element.classList.contains('tool-tooltip'))
    })
  
  if (isClickOutsideNodeTypeMenu) {
    showNodeTypeMenu.value = false
  }
  
  // 检查点击事件是否发生在关系控制菜单或工具按钮之外
  const isClickOutsideRelationMenu = showRelationMenu.value && 
    !event.composedPath().some(el => {
      const element = el as HTMLElement
      return element.classList && 
      (element.classList.contains('relation-menu') || 
       element.classList.contains('tool-button') ||
       element.classList.contains('tool-icon') ||
       element.classList.contains('tool-tooltip'))
    })
  
  if (isClickOutsideRelationMenu) {
    showRelationMenu.value = false
  }
}

// 获取节点名称
const getNodeName = (nodeId: string): string => {
  if (!props.data || !props.data.nodes) return nodeId
  
  const node = props.data.nodes.find((node: any) => String(node.id) === nodeId)
  return node ? node.name : nodeId
}

// 收起单个节点的关系
const collapseNode = (nodeId: string) => {
  expandedNodes.delete(nodeId)
  updateChart()
}

// 打开关系控制菜单
const openRelationMenu = () => {
  showRelationMenu.value = true
}

// 关闭关系控制菜单
const closeRelationMenu = () => {
  showRelationMenu.value = false
}

// 收起所有已展开的关系
const collapseAllRelations = () => {
  expandedNodes.clear()
  updateChart()
}

// 切换节点类型显示/隐藏
const toggleNodeType = (type: string) => {
  const index = selectedNodeTypes.indexOf(type)
  if (index > -1) {
    selectedNodeTypes.splice(index, 1)
  } else {
    selectedNodeTypes.push(type)
  }
  
  // 强制更新图表以确保图例状态正确
  if (chart) {
    const option = getChartOption(props.data)
    chart.setOption(option, {
      replaceMerge: ['legend', 'series'] // 替换legend和series部分
    })
  }
}

// 切换图例显示状态
const toggleLegendDisplay = () => {
  showLegend.value = !showLegend.value
  // 强制重新设置选项，确保图例变化立即生效
  if (chart) {
    const option = getChartOption(props.data)
    // 设置动画为false，使变化立即生效
    chart.setOption(option, {
      notMerge: true, // 不合并之前的配置
      replaceMerge: ['legend'] // 替换legend配置
    })
  }
}

// 全选操作
const selectAll = () => {
  selectedNodeTypes.splice(0, selectedNodeTypes.length, ...nodeTypes.value)
  
  // 强制更新图表以确保图例状态正确
  if (chart) {
    const option = getChartOption(props.data)
    chart.setOption(option, {
      replaceMerge: ['legend']
    })
  }
}

// 取消全选操作
const unselectAll = () => {
  selectedNodeTypes.splice(0, selectedNodeTypes.length)
  
  // 强制更新图表以确保图例状态正确
  if (chart) {
    const option = getChartOption(props.data)
    chart.setOption(option, {
      replaceMerge: ['legend']
    })
  }
}

// 图表配置
const getChartOption = (data: any): EChartsOption => {
  if (!data || !data.nodes || !data.lines) {
    return {}
  }

  // 准备图例数据
  const legendData = nodeTypes.value.map(type => ({
    name: type,
    icon: 'circle',
    itemStyle: {
      color: typeColors[type]?.color || '#A9A9A9'
    },
    // 使用已选择的节点类型列表来确定是否选中
    selected: selectedNodeTypes.includes(type)
  }))

  // 处理节点数据，根据类型分组
  const nodesByCategory: {[key: string]: any[]} = {}
  const allNodes = data.nodes.map((node: any) => {
    const nodeType = node.type || '其他'
    const nodeStyle = typeColors[nodeType] || {
      color: '#A9A9A9',
      size: 35,
      borderColor: '#C0C0C0',
      gradient: ['#A9A9A9', '#C0C0C0']
    }
    
    // 按类型分组
    if (!nodesByCategory[nodeType]) {
      nodesByCategory[nodeType] = []
    }
    
    const processedNode = {
      id: String(node.id),
      name: node.name,
      category: nodeType,
      value: [0, 0, nodeStyle.size],
      symbolSize: nodeStyle.size,
      itemStyle: {
        color: {
          type: 'radial',
          x: 0.5,
          y: 0.5,
          r: 0.5,
          colorStops: [
            { offset: 0, color: nodeStyle.gradient[0] },
            { offset: 1, color: nodeStyle.gradient[1] }
          ]
        },
        borderColor: nodeStyle.borderColor,
        borderWidth: 2,
        shadowColor: 'rgba(0, 0, 0, 0.2)',
        shadowBlur: 10
      },
      label: {
        show: true,
        position: 'inside',
        formatter: '{b}',
        fontSize: 12,
        color: '#fff',
        fontWeight: 'bold'
      }
    }
    
    nodesByCategory[nodeType].push(processedNode)
    return processedNode
  })

  // 节点ID映射表（用于快速查找）
  const nodeMap = new Map(allNodes.map(node => [node.id, node]))

  // 处理连线数据
  const links = data.lines.filter(line => {
    return nodeMap.has(String(line.from)) && nodeMap.has(String(line.to))
  }).map((line, index) => {
    // 建立多节点间的连接线，避免重叠
    let lineColor = '#999' // 默认连接线颜色
    let curveness = 0 // 默认弧度

    // 检查是否存在相同起点和终点的多条连接线
    const parallelLinks = data.lines.filter(
      l => (l.from === line.from && l.to === line.to) || (l.from === line.to && l.to === line.from)
    )

    if (parallelLinks.length > 1) {
      // 计算当前连接线在平行连接线中的位置
      const linkIndex = parallelLinks.findIndex(
        l => l.from === line.from && l.to === line.to && l.text === line.text
      )
      
      // 增加基础曲率以减少线条交叉
      const baseCurvature = 0.4
      
      // 检查当前线的方向是否与第一条线相反
      const firstLink = parallelLinks[0]
      const isOppositeDirection = (firstLink.from === line.to && firstLink.to === line.from)
      
      // 修改弯曲逻辑：考虑方向因素
      if (parallelLinks.length === 2) {
        if (isOppositeDirection) {
          curveness = linkIndex % 2 === 0 ? -baseCurvature : baseCurvature
        } else {
          curveness = linkIndex % 2 === 0 ? baseCurvature : -baseCurvature
        }
      } else {
        const curveStep = baseCurvature / Math.ceil(parallelLinks.length / 2)
        const magnitude = Math.ceil((linkIndex + 1) / 2) * curveStep
        
        if (isOppositeDirection) {
          curveness = linkIndex % 2 === 0 ? -magnitude : magnitude
        } else {
          curveness = linkIndex % 2 === 0 ? magnitude : -magnitude
        }
      }

      // 根据关系类型设置颜色
      if (line.relation_category === '演变类' || 
          (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
            line.text.includes('更名') || line.text.includes('改置') || 
            line.text.includes('设置') || line.text.includes('撤销')))) {
        lineColor = '#e63946'
        curveness = curveness > 0 ? curveness + 0.05 : curveness - 0.05
      } else if (line.relation_category === '所属类' ||
                (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                  line.text.includes('辖域')))) {
        lineColor = '#457b9d'
      }
    } else {
      // 为单一连接线也设置微弱的曲率，帮助减少交叉
      curveness = 0.05
      
      if (line.relation_category === '演变类' || 
          (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
            line.text.includes('更名') || line.text.includes('改置') || 
            line.text.includes('设置') || line.text.includes('撤销')))) {
        lineColor = '#e63946'
      } else if (line.relation_category === '所属类' ||
                (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                  line.text.includes('辖域')))) {
        lineColor = '#457b9d'
      }
    }
    
    const showLabel = true // 总是显示标签

    return {
      source: String(line.from),
      target: String(line.to),
      value: line.text,
      lineStyle: {
        color: lineColor,
        curveness: curveness,
        width: 1.5,
        opacity: 0.7
      },
      label: {
        show: showLabel,
        formatter: line.text,
        fontSize: 9, // 从10减小到8
        color: '#333', // 更深的文字颜色
        padding: [1, 3], // 从[2, 4]减小到[1, 3]
        backgroundColor: 'transparent', // 将背景色设置为透明
        textBorderColor: 'rgba(255, 255, 255, 0.8)', // 添加白色描边提高可读性
        textBorderWidth: 1, // 描边宽度保持不变以确保可读性
        distance: 3 // 添加距离参数，使文字更贴近连线
      }
    }
  })

  // 筛选节点
  let displayNodes = allNodes;
  let displayLinks = links;
  
  // 如果不显示所有关系，且有已展开的节点，则只显示已展开节点的关系
  if (!showAllRelations.value) {
    displayLinks = links.filter(link => {
      return expandedNodes.has(link.source) || expandedNodes.has(link.target);
    });
  }
  
  // 处理节点类型筛选
  if (selectedNodeTypes.length > 0 && selectedNodeTypes.length < nodeTypes.value.length) {
    // 筛选出选中类型的节点
    displayNodes = allNodes.filter(node => selectedNodeTypes.includes(node.category));
    
    // 筛选关系：保留至少一端连接到选中类型节点的关系
    displayLinks = displayLinks.filter(link => {
      const sourceNode = nodeMap.get(link.source);
      const targetNode = nodeMap.get(link.target);
      return sourceNode && targetNode && 
             (selectedNodeTypes.includes(sourceNode.category) || 
              selectedNodeTypes.includes(targetNode.category));
    });
  }

  // 构建基础配置
  const baseOption: EChartsOption = {
    backgroundColor: '#f8f9fa',
    // 添加全局动画配置
    animation: true,
    animationDuration: 1000,
    animationEasing: 'elasticOut',
    animationDelay: function (idx) {
      return idx * 50;
    },
    animationDurationUpdate: 1000,
    animationEasingUpdate: 'quinticInOut',
    animationDelayUpdate: function (idx) {
      return idx * 100;
    },
    tooltip: {
      show: true,
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#ddd',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      },
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          let tooltipHtml = `<div style="font-weight:bold">${params.data.name}</div>
                  <div style="color:${params.data.itemStyle.color.colorStops[0].color}">类型: ${params.data.category}</div>`;
          
          // 如果是筛选模式且不显示所有关系，才显示点击提示
          if (selectedNodeTypes.length > 0 && !showAllRelations.value) {
            tooltipHtml += `<div>${expandedNodes.has(params.data.id) ? '点击收起关联' : '点击展开关联'}</div>`;
          }
          return tooltipHtml;
        } else if (params.dataType === 'edge') {
          return `<div style="font-weight:bold">${params.data.value}</div>`;
        }
      }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      animation: true,
      animationDuration: 1000,
      animationEasing: 'elasticOut',
      animationDelay: function (idx) {
        return idx * 50;
      },
      animationDurationUpdate: 1000,
      animationEasingUpdate: 'quinticInOut',
      animationDelayUpdate: function (idx) {
        return idx * 100;
      },
      categories: nodeTypes.value.map(type => ({
        name: type,
        itemStyle: {
          color: typeColors[type]?.color || '#A9A9A9'
        }
      })),
      data: displayNodes,
      links: displayLinks,
      force: {
        repulsion: 350,       // 增加斥力，使节点之间距离更远
        edgeLength: 150,      // 增加边长度，使连接的节点距离更大
        gravity: 0.01,        // 减小引力，减少节点向中心聚集
        friction: 0.8,        // 增加摩擦系数，使布局更快达到稳定状态
        initLayout: 'circular',
        layoutAnimation: true,
        coolingTime: 800,    // 增加冷却时间，给布局更多时间稳定
        maxIterations: 110,   // 增加最大迭代次数
        gravityCenter: [0, 0],
        edgeStrength: 0.03,   // 降低边强度，使边的牵引力更弱
        nodeStrength: 0.08,   // 调整节点强度
        draggable: true,
        fixX: false,
        fixY: false,
        layoutBy: 'force',
        preventOverlap: true,
        nodeScaleRatio: 0.6,  // 降低节点比例，减少节点大小对布局的影响
        minMovement: 0.1,     // 减小最小移动距离，更精细的稳定条件
        maxSpeed: 10          // 减小最大速度，使节点移动更平稳
      },
      roam: true,
      draggable: true,
      cursor: 'auto',
      focusNodeAdjacency: true,
      label: {
        show: true,
        position: 'inside',
        formatter: '{b}',
        fontSize: 12,
        color: '#fff',
        fontWeight: 'bold'
      },
      lineStyle: {
        color: '#999',
        curveness: 0.15,
        width: 1.5,
        opacity: 0.7
      },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 12],
      edgeLabel: {
        show: true,
        formatter: function(params) {
          return params.data.value;
        },
        fontSize: 8, // 从10减小到8
        color: '#333', // 更深的文字颜色
        padding: [1, 3], // 从[2, 4]减小到[1, 3]
        backgroundColor: 'transparent', // 将背景色设置为透明
        textBorderColor: 'rgba(255, 255, 255, 0.8)', // 添加白色描边提高可读性
        textBorderWidth: 2, // 描边宽度保持不变以确保可读性
        distance: 3 // 添加距离参数，使文字更贴近连线
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 3
        }
      }
    }]
  };

  // 仅当showLegend为true时添加legend配置
  if (showLegend.value) {
    baseOption.legend = {
      type: 'plain',
      orient: 'vertical',
      left: 20,
      top: 20,
      itemGap: 10,
      selectedMode: 'multiple',
      data: legendData,
      textStyle: {
        color: '#333',
        fontSize: 12
      },
      selected: Object.fromEntries(legendData.map(item => [item.name, selectedNodeTypes.includes(item.name)]))
    };
  }

  return baseOption;
}

// 打开节点类型菜单
const openNodeTypeMenu = () => {
  showNodeTypeMenu.value = true
}

// 关闭节点类型菜单
const closeNodeTypeMenu = () => {
  showNodeTypeMenu.value = false
}

// 处理展开关系
const handleExpandRelations = () => {
  if (selectedNode.value) {
    const nodeId = selectedNode.value.id
    if (expandedNodes.has(nodeId)) {
      expandedNodes.delete(nodeId)
    } else {
      expandedNodes.add(nodeId)
      // 触发节点展开事件
      emit('node-expanded', nodeId)
    }
    updateChart()
    // 操作完成后关闭菜单
    showMenu.value = false
  }
}

// 处理查看属性
const handleViewProperties = async () => {
  if (selectedNode.value) {
    try {
      const response = await Http.get(`/api/node/detail?id=${selectedNode.value.id}`)
      if (response.code === 200) {
        nodeProperties.value = response.data
        propertyDialogVisible.value = true
      }
    } catch (error) {
      console.error('获取节点属性失败:', error)
    }
    // 操作完成后关闭菜单
    showMenu.value = false
  }
}

// 关闭菜单
const closeMenu = () => {
  showMenu.value = false
  selectedNode.value = null
}

onMounted(() => {
  initChart()
  updateChart()
  fetchNodeTypes()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', handleDocumentClick)
  chart?.dispose()
})
</script>

<style scoped>
.echarts-graph {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden; /* 防止图表溢出 */
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
  background-color: #f8f9fa;
}

/* 图谱工具按钮组 */
.graph-tools {
  position: fixed;
  right: 20px;
  bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 100;
}

.tool-button {
  width: 40px;
  height: 40px;
  background-color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  position: relative;
  transition: all 0.2s;
}

.tool-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.tool-button.active {
  background-color: #5470c6;
  color: white;
}

.tool-icon {
  font-size: 18px;
  font-style: normal;
}

.tool-tooltip {
  position: absolute;
  right: 50px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  visibility: hidden;
  opacity: 0;
  transition: all 0.2s;
}

.tool-button:hover .tool-tooltip {
  visibility: visible;
  opacity: 1;
}

/* 关系控制菜单 */
.relation-menu {
  position: fixed;
  right: 70px;
  bottom: 20px;
  width: 250px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
  z-index: 101;
  overflow: hidden;
  max-height: 450px;
  display: flex;
  flex-direction: column;
}

.menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ebeef5;
}

.menu-title {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
}

.menu-close {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 18px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.05);
}

.menu-close:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.relation-actions {
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid #ebeef5;
}

.relation-btn {
  width: 100%;
  padding: 8px 12px;
  background-color: #5470c6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  display: flex;
  justify-content: center;
  align-items: center;
}

.relation-btn:hover {
  background-color: #4863b2;
  transform: translateY(-1px);
}

.expanded-nodes-list {
  padding: 0;
  max-height: 300px;
  display: flex;
  flex-direction: column;
}

.list-header {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
  padding: 10px 15px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ebeef5;
}

.expanded-node-items {
  max-height: 250px;
  overflow-y: auto;
}

.expanded-node-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 15px;
  border-bottom: 1px solid #f5f5f5;
  transition: background-color 0.2s;
}

.expanded-node-item:hover {
  background-color: #f5f7fa;
}

.node-name {
  font-size: 13px;
  color: #606266;
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-btn {
  color: #5470c6;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background-color: rgba(84, 112, 198, 0.1);
  color: #3f51b5;
}

/* 节点类型菜单 */
.node-type-menu {
  position: fixed;
  right: 70px;
  bottom: 20px;
  width: 220px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
  z-index: 101;
  overflow: hidden;
  max-height: 450px;
  display: flex;
  flex-direction: column;
}

.menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ebeef5;
}

.menu-title {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
}

.menu-close {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 18px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.05);
}

.menu-close:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.menu-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.menu-select-all {
  padding: 10px 15px;
  display: flex;
  justify-content: center;
  border-bottom: 1px solid #ebeef5;
}

.mini-btn {
  padding: 5px 12px;
  background-color: #5470c6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: opacity 0.2s;
}

.mini-btn:hover {
  opacity: 0.9;
}

.type-controls {
  max-height: 350px;
  overflow-y: auto;
  padding: 5px 0;
}

.legend-item {
  display: flex;
  align-items: center;
  padding: 8px 15px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.legend-item:hover {
  background-color: #f5f7fa;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

.legend-text {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

.legend-checkbox {
  width: 16px;
  height: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 2px;
  position: relative;
}

.legend-checkbox.checked {
  background-color: #409eff;
  border-color: #409eff;
}

.legend-checkbox.checked::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 5px;
  width: 4px;
  height: 8px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

/* 节点菜单弹框样式 */
.node-menu-popup {
  position: absolute;
  transform: translate(10px, -50%);
  z-index: 100;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 180px;
  overflow: hidden;
  pointer-events: auto;
}

.popup-header {
  padding: 12px 15px;
  background: linear-gradient(135deg, #5470c6, #6a85d1);
  color: white;
  position: relative;
}

.popup-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.popup-type {
  font-size: 12px;
  opacity: 0.9;
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 8px;
  border-radius: 10px;
  display: inline-block;
}

.popup-actions {
  display: flex;
  padding: 10px;
  gap: 10px;
}

.popup-button {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 5px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.popup-button.expand {
  background: rgba(145, 204, 117, 0.1);
  color: #3ba272;
}

.popup-button.view {
  background: rgba(84, 112, 198, 0.1);
  color: #5470c6;
}

.popup-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.popup-button.expand:hover {
  background: rgba(145, 204, 117, 0.2);
}

.popup-button.view:hover {
  background: rgba(84, 112, 198, 0.2);
}

.popup-icon {
  font-size: 20px;
  margin-bottom: 6px;
}

.popup-text {
  font-size: 12px;
  font-weight: 500;
}

.property-container {
  padding: 20px;
}

.property-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.node-title {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-right: 12px;
}

.node-type {
  background-color: #409eff;
  color: white;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
}

.property-content {
  max-height: 400px;
  overflow-y: auto;
}

.property-item {
  display: flex;
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 4px;
  background: #f5f7fa;
}

.property-key {
  width: 120px;
  font-weight: bold;
  color: #606266;
}

.property-value {
  flex: 1;
  color: #303133;
}

.popup-close {
  position: absolute;
  top: 8px;
  right: 10px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  transition: all 0.2s;
}

.popup-close:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}
</style> 