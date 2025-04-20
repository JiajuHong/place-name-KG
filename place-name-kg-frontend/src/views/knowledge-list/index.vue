<template>
  <lay-container fluid="true" style="padding: 10px">
    <lay-row :space="10">
      <lay-col :md="24">
        <lay-card>
          <lay-form style="margin-top: 20px">
            <lay-row>
              <lay-col :md="6">
                <lay-form-item label="知识节点名称：" label-width="50">
                  <lay-input
                      v-model="searchName"
                      style="width: 90%"
                  ></lay-input>
                </lay-form-item>
              </lay-col>
              <lay-col :md="6">
                <lay-form-item label-width="0">
                  <lay-button type="primary" @click="toSearch">查询</lay-button>
                  <lay-button @click="toReset">重置</lay-button>
                </lay-form-item>
              </lay-col>
            </lay-row>
          </lay-form>
        </lay-card>
      </lay-col>
      <lay-col :md="24">
        <lay-card>
          <lay-table
              :page="page"
              :columns="columns"
              :dataSource="dataSource"
              @change="change"
          >
            <template v-slot:type="{row}">
              <lay-tag :color="row.color" class="type_tag">{{ row.type }}</lay-tag>
            </template>
            <template v-slot:toolbar>
              <lay-button size="sm" type="primary" @click="add">新增</lay-button>
            </template>
            <template v-slot:operator="{row}">
              <lay-button size="xs" type="primary" @click="viewDetail(row)">编辑</lay-button>
              <lay-button size="xs" type="danger" @click="deleteNode(row)">删除</lay-button>
            </template>
          </lay-table>
        </lay-card>
      </lay-col>
    </lay-row>

    <lay-layer
        v-model="visible"
        title="新增/编辑"
        shade="true"
    >
      <lay-form ref="formRef" :model="formData" style="width: 600px;padding:20px">
        <lay-form-item label="节点名称" prop="name" required="true">
          <lay-input v-model="formData.name"></lay-input>
        </lay-form-item>
        <lay-form-item label="节点类型" prop="type" required="true">
          <lay-input v-model="formData.type" :readonly="formData.id"></lay-input>
        </lay-form-item>
        <lay-form-item style="text-align: right">
          <lay-button type="normal" style="width: 100px" @click="submit">提交</lay-button>
          <lay-button style="width: 100px" @click="close">取消</lay-button>
        </lay-form-item>
      </lay-form>
    </lay-layer>
    
    <lay-layer
        v-model="detailVisible"
        title="节点详细属性"
        shade="true"
        :area="['800px', '600px']"
    >
      <div v-if="isLoading" class="loading-container">
        <lay-loading-bar color="var(--global-primary-color)"></lay-loading-bar>
        <div>加载中...</div>
      </div>
      <div v-else-if="loadError" class="error-container">
        <lay-icon type="layui-icon-face-cry"></lay-icon>
        <div>{{ loadError }}</div>
      </div>
      <div v-else class="detail-container">
        <lay-form :model="nodeDetail" style="padding:20px">
          <div class="section-title">基本信息</div>
          <lay-row>
            <lay-col :md="12">
              <lay-form-item label="节点ID" prop="id">
                <lay-input v-model="nodeDetail.id" readonly></lay-input>
              </lay-form-item>
            </lay-col>
            <lay-col :md="12">
              <lay-form-item label="节点类型" prop="type">
                <lay-input v-model="nodeDetail.type"></lay-input>
              </lay-form-item>
            </lay-col>
          </lay-row>
          <lay-form-item label="节点名称" prop="name">
            <lay-input v-model="nodeDetail.name"></lay-input>
          </lay-form-item>
          
          <div class="section-title">其他属性</div>
          <div v-for="(value, key) in nodeProperties" :key="key" class="property-item">
            <lay-row>
              <lay-col :md="8">
                <lay-form-item :label="key" :prop="key">
                  <lay-input v-model="nodeProperties[key]"></lay-input>
                </lay-form-item>
              </lay-col>
              <lay-col :md="4" style="padding-top: 30px">
                <lay-button size="xs" type="danger" @click="removeProperty(key)">删除</lay-button>
              </lay-col>
            </lay-row>
          </div>
          
          <div class="section-title">添加新属性</div>
          <lay-row>
            <lay-col :md="8">
              <lay-form-item label="属性名" prop="newPropertyKey">
                <lay-input v-model="newPropertyKey" placeholder="请输入属性名"></lay-input>
              </lay-form-item>
            </lay-col>
            <lay-col :md="8">
              <lay-form-item label="属性值" prop="newPropertyValue">
                <lay-input v-model="newPropertyValue" placeholder="请输入属性值"></lay-input>
              </lay-form-item>
            </lay-col>
            <lay-col :md="4" style="padding-top: 30px">
              <lay-button type="normal" @click="addProperty">添加</lay-button>
            </lay-col>
          </lay-row>
          
          <lay-form-item style="text-align: right; margin-top: 20px">
            <lay-button type="primary" style="width: 100px" @click="saveProperties" :loading="isSaving">保存</lay-button>
            <lay-button style="width: 100px" @click="closeDetail">取消</lay-button>
          </lay-form-item>
        </lay-form>
      </div>
    </lay-layer>
  </lay-container>
</template>

<script setup>
import {onMounted, ref, reactive} from "vue";
import Http from "@/api/http";
import {layer} from "@layui/layui-vue";

const searchName = ref('')
const page = ref({total: 0, limit: 10, current: 1})
const columns = ref([
  {
    title: 'ID',
    key: 'id',
    width: 80
  },
  {
    title: '知识节点名称',
    key: 'name'
  },
  {
    title: '知识节点类型',
    width: '400px',
    customSlot: 'type',
    key: 'type',
    fixed: 'right'
  },
  {
    title: '操作',
    width: '240px',
    customSlot: 'operator',
    key: 'operator',
    fixed: 'right'
  }
])
const dataSource = ref([])
const type_colors = ['#8dcc93', '#57c7e3', '#ec719d', '#f16667', '#4c8eda', '#f79767', '#d9c8ae'];
let typeColorMap = {};
const visible = ref(false)
const formData = ref({})
const formRef = ref(null)

const detailVisible = ref(false)
const nodeDetail = ref({})
const nodeProperties = ref({})
const isLoading = ref(false)
const loadError = ref('')
const isSaving = ref(false)
const newPropertyKey = ref('')
const newPropertyValue = ref('')
const currentNodeId = ref(null)

async function viewDetail(row) {
  detailVisible.value = true
  currentNodeId.value = row.id
  await fetchNodeDetail(row.id)
}

async function fetchNodeDetail(nodeId) {
  isLoading.value = true
  loadError.value = ''
  try {
    const response = await Http.get(`/api/node/detail?id=${nodeId}`)
    if (response.code === 200) {
      nodeDetail.value = {
        id: response.data.id,
        type: response.data.type,
        name: response.data.name
      }
      
      const otherProps = {...response.data}
      delete otherProps.id
      delete otherProps.type
      delete otherProps.name
      
      nodeProperties.value = otherProps
    } else {
      loadError.value = response.msg || '获取节点详情失败'
    }
  } catch (error) {
    console.error('获取节点详情失败:', error)
    loadError.value = '获取节点详情失败，请重试'
  } finally {
    isLoading.value = false
  }
}

function addProperty() {
  if (newPropertyKey.value.trim() && newPropertyValue.value.trim()) {
    nodeProperties.value[newPropertyKey.value.trim()] = newPropertyValue.value.trim()
    newPropertyKey.value = ''
    newPropertyValue.value = ''
  } else {
    layer.msg('属性名和属性值不能为空', {icon: 2})
  }
}

function removeProperty(key) {
  delete nodeProperties.value[key]
}

async function saveProperties() {
  isSaving.value = true
  try {
    const properties = {
      ...nodeDetail.value,
      ...nodeProperties.value
    }
    
    const response = await Http.post('/api/node/update_properties', {
      id: nodeDetail.value.id,
      properties
    })
    
    if (response.code === 200) {
      layer.msg('属性保存成功', {icon: 1})
      detailVisible.value = false
      query()
    } else {
      layer.msg(response.msg || '保存失败', {icon: 2})
    }
  } catch (error) {
    console.error('保存节点属性失败:', error)
    layer.msg('保存失败，请重试', {icon: 2})
  } finally {
    isSaving.value = false
  }
}

function closeDetail() {
  detailVisible.value = false
  nodeDetail.value = {}
  nodeProperties.value = {}
  loadError.value = ''
  currentNodeId.value = null
}

function add() {
  visible.value = true
}

function edit(row) {
  visible.value = true
  formData.value = {...row}
}

function deleteNode(row) {
  Http.post("/delete_node", row).then((res) => {
    layer.msg("删除成功", {icon: 1})
    submitAfter()
  })
}

function submit() {
  formRef.value.validate((isValidate, formData) => {
    if (isValidate) {
      if (formData.id) {
        Http.post("/update_node", formData).then((res) => {
          layer.msg("修改成功", {icon: 1})
          submitAfter()
        })
      } else {
        Http.post("/create_node", formData).then((res) => {
          layer.msg("创建成功", {icon: 1})
          submitAfter()
        })
      }
    }
  })
}

function submitAfter() {
  visible.value = false
  formData.value = {}
  query()
}

function close() {
  visible.value = false
}

function change({current, limit}) {
  page.value.current = current
  page.value.limit = limit
  query()
}

function toSearch() {
  query()
}

function toReset() {
  searchName.value = ''
  query()
}

function getTypeColor(type) {
  if (!typeColorMap[type]) {
    typeColorMap[type] = type_colors.length > 0 ? type_colors.shift() : '#cccccc';
  }
  return typeColorMap[type];
}

function query() {
  Http.post("/api/find_node_page", {
    pageNum: page.value.current,
    pageSize: page.value.limit,
    name: searchName.value,
  }).then((res) => {
    dataSource.value = res.data.records
    if (dataSource.value) {
      dataSource.value.forEach(item => {
        item.color = getTypeColor(item.type);
      })
    }
    page.value.total = res.data.total
  })
}

onMounted(() => {
  query()
})
</script>

<style>
.type_tag {
  width: 140px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.section-title {
  font-weight: bold;
  margin: 15px 0 10px 0;
  padding-bottom: 5px;
  border-bottom: 1px solid #eee;
  color: #333;
}

.loading-container, .error-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.error-container {
  color: #f56c6c;
}

.error-container .layui-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.detail-container {
  max-height: 520px;
  overflow-y: auto;
}

.property-item {
  margin-bottom: 5px;
  padding: 5px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.property-item:hover {
  background-color: #f5f5f5;
}
</style>