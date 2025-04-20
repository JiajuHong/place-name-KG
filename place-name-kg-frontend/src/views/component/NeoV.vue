<template>
  <div style="display: flex;">
    <div :style="styles">
      <div style="padding: 10px 0 40px 20px;background: #ffffff">
        <lay-tag v-for="(value, key) in typeMapping" :key="key" :color="value.color" style="margin: 10px 20px 0 0">
          {{ key }}({{ value.count }})
        </lay-tag>
      </div>
      <RelationGraph ref="graphRef" :options="graphOptions" @node-click="onNodeClick">
        <template #node="{node}">
          <div style="display:flex;justify-content:center;">
            <lay-tooltip :content="node.text">
              <div class="node-text" style="width:160px">
                {{ node.text }}
              </div>
            </lay-tooltip>
          </div>
        </template>
      </RelationGraph>
    </div>

    <lay-layer :title="false" :closeBtn="false" type="drawer" area="600px" v-model="visible">
      <div class="global-setup" style="padding: 24px">
        <div style="display: flex;align-items: center">
          <div style="font-size: 16px;font-weight: bold" :style="'color:' + selectNode.color">
            {{ selectNode.name }}
          </div>
          <lay-tag style="margin-left: 20px">
            &nbsp;{{ selectNode.type }}
          </lay-tag>
        </div>
        <lay-line style="margin: 20px 0"></lay-line>
        <div
            v-for="(value, key) in selectNode"
            :key="key"
        >
          <div style="display: flex;align-items: center;margin-top: 20px" v-if="!['id', 'name', 'type', 'color','images'].includes(key)">
            <div style="width: 100px;">
              <lay-tag color="#57c7e3">{{ key}}</lay-tag>
            </div>
            <div style="margin-left: 20px">
              {{ value }}
            </div>
          </div>
        </div>
      </div>
    </lay-layer>
  </div>
</template>

<script setup lang="ts">
import {onMounted, reactive, ref, watch} from "vue";
import RelationGraph, {RelationGraphComponent, RGOptions} from 'relation-graph-vue3';

const props = defineProps({
  data: {
    type: Object,
    default() {
      return {};
    },
  },
  styles: {
    type: Object,
    default() {
      return {};
    },
  },
});
const visible = ref(false)
const nodeProperties = [
  {
    width: 140,
    height: 140,
    color: '#8dcc93',
  },
  {
    width: 130,
    height: 130,
    color: '#57c7e3',
  },
  {
    width: 120,
    height: 120,
    color: '#ec719d',
  },
  {
    width: 110,
    height: 110,
    color: '#f16667',
  },
  {
    width: 100,
    height: 100,
    color: '#4c8eda',
  },
  {
    width: 90,
    height: 90,
    color: '#f79767',
  },
  {
    width: 80,
    height: 80,
    color: '#d9c8ae'
  },
  {
    width: 80,
    height: 80,
    color: '#ff9d00'
  },
  {
    width: 80,
    height: 80,
    color: '#cf00ff'
  },
  {
    width: 80,
    height: 80,
    color: '#5790ff'
  },
  {
    width: 30,
    height: 30,
    color: '#bbd3ff'
  },
  {
    width: 80,
    height: 80,
    color: '#57ffcd'
  }
];
const typeMapping = ref({})
const graphOptions: RGOptions = {
  debug: false,
  defaultNodeBorderWidth: 0,
  defaultNodeColor: 'rgba(238, 178, 94, 1)',
  allowSwitchLineShape: true,
  allowSwitchJunctionPoint: true,
  defaultLineShape: 1,
  isMoveByParentNode: false,
  layouts: [
    {
      label: 'Auto Layout',
      layoutName: 'force',
      layoutClassName: 'seeks-layout-force'
    }
  ],
  defaultJunctionPoint: 'border',
  allowShowMiniToolBar: false
};
const graphRef = ref<RelationGraphComponent>();
let datasource = reactive<{
  nodes: [],
  lines: [],
}>({
  nodes: [],
  lines: [],
});

const selectNode = ref<any>({});
selectNode.value = {}
const onNodeClick = (nodeObject) => {
  selectNode.value = {
    id: nodeObject.id,
    color: nodeObject.color,
    ...nodeObject.data
  };
  // visible.value = true  // 注释掉这行，不再显示侧边栏
}

const setGraphData = async (data) => {
  datasource = {
    nodes: [],
    lines: []
  }
  if (!data.nodes || data.nodes.length === 0) {
    return;
  }

  let index = 0
  const colorMapping = {}
  data.nodes.forEach(item => {
    if (typeMapping.value[item.type]) {
      typeMapping.value[item.type].count += 1
    } else {
      typeMapping.value[item.type] = {
        color: nodeProperties[index] ? nodeProperties[index].color : '#7a7a7a',
        count: 1
      }
      colorMapping[item.type] = nodeProperties[index]
      index += 1
    }
  })

  data.nodes.forEach(item => {
    const node = {
      id: item.id,
      text: item.name,
      ...colorMapping[item.type],
      data: {...item}
    }
    datasource.nodes.push(node);
  });

  data.lines.forEach(line => {
    if (!datasource.lines.some(item => String(item.from) === String(line.from) && String(item.to) === String(line.to))) {
      line.from = String(line.from)
      line.to = String(line.to)
      datasource.lines.push(line);
    }
  })
  const graphInstance = graphRef.value!.getInstance();
  await graphInstance.setJsonData(datasource).then(() => {
    graphInstance.moveToCenter();
    graphInstance.zoomToFit();
  });
};

onMounted(() => {
  watch(
      () => props.data,
      () => {
        setGraphData(props.data)
      }
  );
});
</script>

<style scoped>

.node-text {
  color: #008489;
  position: absolute;
  top: 100%; /* 将子元素置于父容器的底部 */
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

</style>