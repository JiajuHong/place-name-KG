<template>
  <lay-container fluid="true" style="padding-top: 14px">
    <lay-card>
      <lay-form style="margin-top: 10px">
        <lay-row>
          <lay-col :md="8">
            <lay-form-item label="节点名称" label-width="80">
              <lay-input
                  v-model="searchQuery.name"
                  placeholder="请输入"
                  size="sm"
                  :allow-clear="true"
                  style="width: 98%"
              ></lay-input>
            </lay-form-item>
          </lay-col>
          <lay-col :md="6">
            <lay-form-item label="节点类型" label-width="80">
              <lay-select
                  v-model="searchQuery.node_type"
                  placeholder="请选择"
                  size="sm"
                  :allow-clear="true"
                  style="width: 98%"
              >
                <lay-select-option
                    v-for="type in nodeTypes"
                    :key="type"
                    :value="type"
                    :label="type"
                />
              </lay-select>
            </lay-form-item>
          </lay-col>
          <lay-col :md="6">
            <lay-form-item label="关系类型" label-width="80">
              <lay-select
                  v-model="searchQuery.rel_type"
                  placeholder="请选择"
                  size="sm"
                  :allow-clear="true"
                  style="width: 98%"
              >
                <lay-select-option
                    v-for="type in relTypes"
                    :key="type"
                    :value="type"
                    :label="type"
                />
              </lay-select>
            </lay-form-item>
          </lay-col>
          <lay-col :md="4">
            <lay-form-item label-width="20">
              <lay-button
                  style="margin-left: 20px"
                  type="primary"
                  size="sm"
                  @click="getGraph"
              >
                查询
              </lay-button>
              <lay-button size="sm" @click="toReset"> 重置</lay-button>
            </lay-form-item>
          </lay-col>
        </lay-row>
      </lay-form>
    </lay-card>
    <lay-loading :loading="loading">
      <EChartsGraph :data="datasource" @node-expanded="loadNodeRelations" />
    </lay-loading>
  </lay-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EChartsGraph from './EChartsGraph.vue'
import Http from "@/api/http";

const loading = ref(false)
let datasource = ref<any>({ nodes: [], lines: [] })
const nodeTypes = ref<string[]>([])
const relTypes = ref<string[]>([])

const searchQuery = ref({
  name: '',
  node_type: '',
  rel_type: ''
})

function toReset() {
  searchQuery.value = {
    name: '',
    node_type: '',
    rel_type: ''
  }
  loading.value = true
  try {
    // 重置时显式指定加载所有节点和关系
    Http.post("/search_name_kg", { load_all: true })
      .then(response => {
        if (response.code === 200) {
          datasource.value = response.data
          console.log("已加载所有节点和关系")
        }
      })
      .catch(error => {
        console.error('获取图谱数据失败：', error)
        datasource.value = { nodes: [], lines: [] }
      })
      .finally(() => {
        loading.value = false
      })
  } catch (error) {
    console.error('获取图谱数据失败：', error)
    datasource.value = { nodes: [], lines: [] }
    loading.value = false
  }
}

// 获取节点类型列表
const fetchNodeTypes = async () => {
  try {
    const response = await Http.get('/api/node_types')
    if (response.code === 200) {
      nodeTypes.value = response.data
    }
  } catch (error) {
    console.error('获取节点类型失败：', error)
  }
}

// 获取关系类型列表
const fetchRelTypes = async () => {
  try {
    const response = await Http.get('/api/relationship_types')
    if (response.code === 200) {
      relTypes.value = response.data
    }
  } catch (error) {
    console.error('获取关系类型失败：', error)
  }
}

// 加载节点关系
async function loadNodeRelations(nodeId) {
  loading.value = true
  try {
    const response = await Http.get(`/api/node/relations?id=${nodeId}`)
    if (response.code === 200) {
      // 合并新的节点和关系
      const currentNodes = new Set(datasource.value.nodes.map(n => n.id))
      const currentLines = new Set(datasource.value.lines.map(l => `${l.from}-${l.to}-${l.text}`))
      
      // 添加新节点
      const newNodes = response.data.nodes.filter(node => !currentNodes.has(node.id))
      
      // 添加新关系
      const newLines = response.data.lines.filter(line => {
        const lineKey = `${line.from}-${line.to}-${line.text}`
        return !currentLines.has(lineKey)
      })
      
      // 更新数据源
      datasource.value = {
        nodes: [...datasource.value.nodes, ...newNodes],
        lines: [...datasource.value.lines, ...newLines]
      }
    }
  } catch (error) {
    console.error('获取节点关系失败：', error)
  } finally {
    loading.value = false
  }
}

async function getGraph() {
  loading.value = true
  try {
    // 判断查询方式
    if (searchQuery.value.name) {
      // 有节点名称，进行模糊搜索
      const response = await Http.get(`/api/node/search_by_name?name=${encodeURIComponent(searchQuery.value.name.trim())}`)
      if (response.code === 200) {
        datasource.value = response.data
      }
    } else if (searchQuery.value.node_type) {
      // 按节点类型筛选
      const response = await Http.get(`/api/node/by_type?type=${encodeURIComponent(searchQuery.value.node_type)}`)
      if (response.code === 200) {
        datasource.value = response.data
      }
    } else if (searchQuery.value.rel_type) {
      // 按关系类型筛选
      const response = await Http.get(`/api/node/by_relationship?type=${encodeURIComponent(searchQuery.value.rel_type)}`)
      if (response.code === 200) {
        datasource.value = response.data
      }
    } else {
      // 没有任何条件，使用默认搜索并显式指定加载所有节点和关系
      const response = await Http.post("/search_name_kg", { load_all: true })
      if (response.code === 200) {
        datasource.value = response.data
      }
    }
  } catch (error) {
    console.error('获取图谱数据失败：', error)
    datasource.value = { nodes: [], lines: [] }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchNodeTypes(), fetchRelTypes()])
  getGraph()
})
</script>

<style scoped>
.search-input {
  display: inline-block;
  width: 98%;
  margin-right: 10px;
}
</style>
