# 用前必读

基于`Vue3`、`Layui`搭建的苏州历史地名知识图谱

## 一、安装依赖

### 1.1 切换华为镜像源
npm config set registry https://mirrors.huaweicloud.com/repository/npm/

### 1.2 安装pnpm依赖
npm install -g pnpm

### 1.3 安装依赖
pnpm install

## 二、启动项目

npm run dev

## 三、打包项目

npm run build

## 四、技术说明

### 技术栈
- **Vue 3**: 用于构建用户界面的渐进式JavaScript框架。通过其响应式系统和Composition API，我们能够更灵活地管理组件状态和逻辑。
- **RelationGraph**: 用于实现知识图谱的图形布局和动画。
- **Vue Router**: Vue.js官方的路由管理器，用于管理页面导航。

### 项目结构
```
project-root/
│── public/                # 静态资源
│── src/
│   ├── assets/            # 资产文件，例如图像和样式
│   ├── components/        # Vue组件
│   ├── views/             # 路由视图
│   ├── router/            # Vue Router配置
│   ├── store/             # Vuex状态管理（如果需要）
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
│── package.json           # 项目依赖和脚本
└── README.md
```