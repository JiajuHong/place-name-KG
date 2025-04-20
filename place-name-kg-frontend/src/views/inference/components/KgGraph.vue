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
    '府': '#91cc75',
    '县': '#5470c6',
    '行政区': '#fac858',
    '地级市': '#ee6666',
    '县级市': '#73c0de',
    '市辖区': '#fc8452',
    '郡': '#9a60b4',
    '乡': '#ea7ccc',
    '监察区': '#ff69b4',
    '地域': '#3ba272',
    '省': '#4169e1',
    '临时政区': '#00ffff',
    '路': '#808080',
    '州': '#8b4513',
    '村': '#556b2f',
    '人民公社': '#483d8b',
    '政权': '#2f4f4f',
    '军镇': '#800000',
    '道': '#9370db',
    '王朝': '#ff8c00'
  };
  
  // 准备数据
  // 处理节点数据，根据类型分组
  const allNodes = nodes.map(node => {
    const nodeType = node.type || '其他';
    const nodeStyle = typeColors[nodeType] || {
      color: '#A9A9A9',
      size: 40,
      borderColor: '#C0C0C0',
      gradient: ['#A9A9A9', '#C0C0C0']
    };
    
    return {
      id: String(node.id),
      name: node.name,
      category: nodeType,
      symbolSize: typeof nodeStyle === 'object' ? nodeStyle.size : 40,
      itemStyle: {
        color: typeof nodeStyle === 'object' ? {
          type: 'radial',
          x: 0.5,
          y: 0.5,
          r: 0.5,
          colorStops: [
            { offset: 0, color: nodeStyle.gradient ? nodeStyle.gradient[0] : nodeStyle.color || '#A9A9A9' },
            { offset: 1, color: nodeStyle.gradient ? nodeStyle.gradient[1] : nodeStyle.color || '#C0C0C0' }
          ]
        } : typeColors[nodeType] || '#A9A9A9',
        borderColor: typeof nodeStyle === 'object' ? nodeStyle.borderColor : '#ccc',
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
        color: typeColors[type] || '#A9A9A9'
      }
    }));
  
  // 处理连线数据
  const graphLinks = lines.filter(line => {
    // 过滤掉推理关系和无效节点连线
    return nodeMap.has(String(line.from)) && 
           nodeMap.has(String(line.to)) && 
           !line.inferred; // 确保不是推理关系
  }).map(line => {
    // 根据关系类型设置不同颜色
    let lineColor = '#999'; // 默认颜色
    let curveness = 0.1; // 默认弧度
    
    // 创建唯一标识符（包含方向）
    const lineKey = `${line.from}_${line.to}_${line.text}`;
    
    // 检查是否存在相同起点和终点的多条连接线
    const parallelLinks = lines.filter(
      l => (l.from === line.from && l.to === line.to) || (l.from === line.to && l.to === line.from)
    );
    
    if (parallelLinks.length > 1) {
      // 根据位置计算弧度，使平行连接线分开显示
      const linkIndex = parallelLinks.findIndex(
        l => `${l.from}_${l.to}_${l.text}` === lineKey
      );
      curveness = 0.1 + (linkIndex * 0.05);
    }
    
    // 根据关系类型设置颜色
    if (line.relation_type === '演变类' || 
        (line.text && (line.text.includes('沿革') || line.text.includes('改名') || 
          line.text.includes('更名') || line.text.includes('改置') || 
          line.text.includes('设置') || line.text.includes('撤销') ||
          line.text.includes('演变') || line.text.includes('降格')))) {
      lineColor = '#e63946'; // 醒目的红色
    } else if (line.relation_type === '所属类' ||
              (line.text && (line.text.includes('隶属') || line.text.includes('下辖') || 
                line.text.includes('辖域')))) {
      lineColor = '#457b9d'; // 蓝色，表示所属关系
    }
    
    return {
      source: String(line.from),
      target: String(line.to),
      value: line.text,
      lineStyle: {
        color: lineColor,
        curveness: curveness,
        width: 1.5,
        opacity: 0.7 // 稍微提高不透明度
      },
      label: {
        show: true,
        formatter: line.text,
        fontSize: 10,
        color: '#333',
        padding: [2, 4],
        textBorderColor: 'rgba(255, 255, 255, 0.8)', // 添加白色描边提高可读性
        textBorderWidth: 2 // 描边宽度
      }
    };
  });
  
  // 图表配置
  const option = {
    backgroundColor: '#f8f9fa',
    title: {
      // text: '地名知识图谱',
      // subtext: '实体关系可视化',
      top: 10,
      left: 'center'
    },
    tooltip: {
      show: true,
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#ddd',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      },
      formatter: function(params) {
        if (params.dataType === 'node') {
          const node = nodes.find(n => String(n.id) === params.data.id);
          if (!node) return params.name;
          
          let html = `<div style="font-weight:bold">${node.name}</div>`;
          html += `<div style="color:${params.color}">类型: ${node.type || '未知'}</div>`;
          
          // 添加其他属性
          for (const key in node) {
            if (['id', 'name', 'type'].includes(key)) continue;
            html += `<div>${key}: ${node[key]}</div>`;
          }
          
          return html;
        } else if (params.dataType === 'edge') {
          return `<div style="font-weight:bold">${params.data.value}</div>`;
        }
      }
    },
    legend: {
      data: categories.map(cate => cate.name),
      orient: 'vertical',
      left: 20,
      top: 50,
      itemGap: 10,
      textStyle: {
        color: '#333',
        fontSize: 12
      },
      selected: Object.fromEntries(categories.map(item => [item.name, true])),
    },
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: allNodes,
        links: graphLinks,
        categories: categories,
        roam: true,
        draggable: true,
        // 当图表大小变化时，自动进行布局适应
        autosizeEnabled: true,
        label: {
          show: true,
          position: 'inside',
          formatter: '{b}',
          fontSize: 12,
          color: '#fff',
          fontWeight: 'bold'
        },
        force: {
          repulsion: 150,
          edgeLength: 120,
          gravity: 0.05,
          friction: 0.6,
          layoutAnimation: true
        },
        lineStyle: {
          color: 'source',
          curveness: 0.15,
          width: 1.5
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        edgeLabel: {
          show: true,
          formatter: '{c}',
          fontSize: 10,
          color: '#333',
          padding: [2, 4],
          textBorderColor: 'rgba(255, 255, 255, 0.8)',
          textBorderWidth: 2
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
  background-color: #fff;
  pointer-events: auto;
  isolation: isolate;
  touch-action: pan-x pan-y;
}
</style> 