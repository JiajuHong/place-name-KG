import { createApp } from 'vue'
import Router from './router'
import Store from './store'
import App from './App.vue'
import { permission } from "./directives/permission";
import './mockjs'
import Layui from '@layui/layui-vue'
import '@layui/layui-vue/lib/index.css'

const app = createApp(App)

app.use(Store);
app.use(Router);
app.use(Layui);
app.directive("permission",permission);
app.mount('#app');
