<template>
  <div class="kg-graph-container" ref="graphContainer" @click.stop @mousedown.stop @touchstart.stop></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  data: {
    type: Object,
    required: true,
    default: () => ({ nodes: [], lines: [] })
  }
});

const graphContainer = ref(null);
let chart = null;
let resizeObserver = null;

// 初始化图表
function initChart() {
  if (!graphContainer.value) return;
  
  // 创建ECharts实例
  chart = echarts.init(graphContainer.value);
  
  // 监听窗口大小变化，调整图表大小
  window.addEventListener('resize', handleResize);
  
  // 使用ResizeObserver监听容器大小变化
  setupResizeObserver();
  
  // 监听点击事件，阻止冒泡
  graphContainer.value.addEventListener('click', (event) => {
    event.stopPropagation();
  });
  
  // 阻止其他可能冒泡的事件
  const stopEvents = ['mousedown', 'touchstart', 'mousemove', 'mouseup', 'touchmove', 'touchend'];
  stopEvents.forEach(eventName => {
    graphContainer.value.addEventListener(eventName, (event) => {
      event.stopPropagation();
    });
  });
  
  // 渲染图表
  renderGraph();
}

// 设置ResizeObserver监听容器大小变化
function setupResizeObserver() {
  if (typeof ResizeObserver !== 'undefined' && graphContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      if (chart) {
        // 使用requestAnimationFrame确保resize在重绘前执行
        requestAnimationFrame(() => {
          try {
            chart.resize({
              animation: {
                duration: 0 // 禁用动画以避免与其他UI元素的过渡冲突
              }
            });
          } catch (e) {
            console.error('图表调整大小失败:', e);
          }
        });
      }
    });
    resizeObserver.observe(graphContainer.value);
  }
}

// 处理窗口大小变化
function handleResize() {
  if (chart) {
    // 使用requestAnimationFrame确保resize在重绘前执行
    requestAnimationFrame(() => {
      try {
        chart.resize({
          animation: {
            duration: 0 // 禁用动画以避免与其他UI元素的过渡冲突
          }
        });
      } catch (e) {
        console.error('图表调整大小失败:', e);
      }
    });
  }
}

// 渲染知识图谱
function renderGraph() {
  if (!chart) return;
  
  const { nodes, lines } = props.data;
  
  // 定义节点类型颜色配置
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
  };
  
  // 准备数据
  // 处理节点数据，根据类型分组
  const allNodes = nodes.map(node => {
    const nodeType = node.type || '其他';
    const nodeStyle = typeColors[nodeType] || {
      color: '#A9A9A9',
      size: 35,
      borderColor: '#C0C0C0',
      gradient: ['#A9A9A9', '#C0C0C0']
    };
    
    return {
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
    };
  });

  // 节点ID映射表
  const nodeMap = new Map(allNodes.map(node => [node.id, node]));
  
  // 获取所有类别
  const categories = Array.from(new Set(nodes.map(node => node.type)))
    .map(type => ({ 
      name: type,
      itemStyle: {
        color: typeColors[type]?.color || '#A9A9A9'
      }
    }));
  
  // 处理连线数据
  const graphLinks = lines.filter(line => {
    return nodeMap.has(String(line.from)) && 
           nodeMap.has(String(line.to)) && 
           !line.inferred;
  }).map(line => {
    let lineColor = '#999'; // 默认颜色
    let curveness = 0.05; // 默认弧度

    // 检查是否存在相同起点和终点的多条连接线
    const parallelLinks = lines.filter(
      l => (l.from === line.from && l.to === line.to) || (l.from === line.to && l.to === line.from)
    );

    if (parallelLinks.length > 1) {
      // 计算当前连接线在平行连接线中的位置
      const linkIndex = parallelLinks.findIndex(
        l => l.from === line.from && l.to === line.to && l.text === line.text
      );
      
      // 增加基础曲率以减少线条交叉
      const baseCurvature = 0.4;
      
      // 检查当前线的方向是否与第一条线相反
      const firstLink = parallelLinks[0];
      const isOppositeDirection = (firstLink.from === line.to && firstLink.to === line.from);
      
      // 修改弯曲逻辑：考虑方向因素
      if (parallelLinks.length === 2) {
        if (isOppositeDirection) {
          curveness = linkIndex % 2 === 0 ? -baseCurvature : baseCurvature;
        } else {
          curveness = linkIndex % 2 === 0 ? baseCurvature : -baseCurvature;
        }
      } else {
        const curveStep = baseCurvature / Math.ceil(parallelLinks.length / 2);
        const magnitude = Math.ceil((linkIndex + 1) / 2) * curveStep;
        
        if (isOppositeDirection) {
          curveness = linkIndex % 2 === 0 ? -magnitude : magnitude;
        } else {
          curveness = linkIndex % 2 === 0 ? magnitude : -magnitude;
        }
      }

      // 根据关系类型设置颜色
      if (line.relation_type === '演变类' || 
          (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
            line.text.includes('更名') || line.text.includes('改置') || 
            line.text.includes('设置') || line.text.includes('撤销')))) {
        lineColor = '#e63946';
        curveness = curveness > 0 ? curveness + 0.05 : curveness - 0.05;
      } else if (line.relation_type === '所属类' ||
                (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                  line.text.includes('辖域')))) {
        lineColor = '#457b9d';
      }
    } else {
      // 为单一连接线也设置微弱的曲率，帮助减少交叉
      curveness = 0.05;
      
      if (line.relation_type === '演变类' || 
          (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
            line.text.includes('更名') || line.text.includes('改置') || 
            line.text.includes('设置') || line.text.includes('撤销')))) {
        lineColor = '#e63946';
      } else if (line.relation_type === '所属类' ||
                (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                  line.text.includes('辖域')))) {
        lineColor = '#457b9d';
      }
    }
    
    const showLabel = true; // 总是显示标签

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
        fontSize: 7,
        color: '#333',
        padding: [1, 3],
        backgroundColor: 'transparent',
        borderRadius: 2,
        textBorderColor: 'rgba(255, 255, 255, 0.8)',
        textBorderWidth: 1,
        distance: 3
      }
    };
  });
  
  // 图表配置
  const option = {
    backgroundColor: '#f8f9fa',
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
      formatter: (params) => {
        if (params.dataType === 'node') {
          const node = nodes.find(n => String(n.id) === params.data.id);
          if (!node) return params.name;
          
          let tooltipHtml = `<div style="font-weight:bold">${node.name}</div>
                      <div style="color:${params.data.itemStyle.color.colorStops[0].color}">类型: ${node.type || '未知'}</div>`;
          
          return tooltipHtml;
        } else if (params.dataType === 'edge') {
          return `<div style="font-weight:bold">${params.data.value}</div>`;
        }
      }
    },
    series: [
      {
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
        categories: categories,
        data: allNodes,
        links: graphLinks,
        force: {
          repulsion: 350,       // 增加斥力，使节点之间距离更远
          edgeLength: 150,      // 增加边长度，使连接的节点距离更大
          gravity: 0.01,        // 减小引力，减少节点向中心聚集
          friction: 0.8,        // 增加摩擦系数，使布局更快达到稳定状态
          initLayout: 'circular',
          layoutAnimation: true,
          coolingTime: 500,     // 冷却时间
          maxIterations: 50,    // 最大迭代次数
          gravityCenter: [0, 0],
          edgeStrength: 0.01,   // 降低边强度，使边的牵引力更弱
          nodeStrength: 0.08,   // 调整节点强度
          draggable: true,
          fixX: false,
          fixY: false,
          layoutBy: 'force',
          preventOverlap: true,
          nodeScaleRatio: 0.6,  // 降低节点比例，减少节点大小对布局的影响
          minMovement: 0.1,     // 减小最小移动距离，更精细的稳定条件
          maxSpeed: 10          // 最大速度
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
          fontSize: 7,
          color: '#333',
          padding: [1, 3],
          backgroundColor: 'transparent',
          textBorderColor: 'rgba(255, 255, 255, 0.8)',
          textBorderWidth: 1,
          distance: 3
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 3
          }
        }
      }
    ]
  };
  
  // 仅当节点类型不为空时添加legend配置
  if (categories.length > 0) {
    option.legend = {
      type: 'plain',
      orient: 'vertical',
      left: 20,
      top: 20,
      itemGap: 10,
      selectedMode: 'multiple',
      data: categories,
      textStyle: {
        color: '#333',
        fontSize: 12
      },
      selected: Object.fromEntries(categories.map(item => [item.name, true]))
    };
  }
  
  // 设置图表选项
  chart.setOption(option);
}

// 组件挂载后初始化图表
onMounted(() => {
  initChart();
});

// 当数据变化时，更新图表
watch(() => props.data, () => {
  renderGraph();
}, { deep: true });

// 组件卸载前清理资源
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (chart) {
    chart.dispose();
    chart = null;
  }
});
</script>

<style scoped>
.kg-graph-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
  background-color: #f8f9fa; /* 更改为与主页图谱相同的背景色 */
  pointer-events: auto;
  isolation: isolate;
  touch-action: pan-x pan-y;
}
</style> 