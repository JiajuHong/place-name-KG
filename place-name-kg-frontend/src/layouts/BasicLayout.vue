<template>
  <lay-config-provider
      :themeVariable="appStore.themeVariable"
      :theme="appStore.theme"
      :locales="locales"
      :locale="appStore.locale"
  >
    <lay-layout
        :class="[
        appStore.tab ? 'has-tab' : '',
        appStore.collapse ? 'collapse' : '',
        appStore.greyMode ? 'grey-mode' : ''
      ]"
    >
      <!-- 遮盖层 -->
      <div
          v-if="!appStore.collapse"
          class="layui-layer-shade hidden-sm-and-up"
          @click="collapse"
      ></div>
      <!-- 核心菜单  -->
      <lay-side
          :width="sideWidth"
          :class="appStore.sideTheme == 'dark' ? 'dark changeBgc' : 'light'"
      >
        <div
            v-if="appStore.logo"
            style="color: #ffffff;font-size: 16px;font-weight: 600;display: flex;align-items: center;padding: 10px 10px 10px 20px;"
        >
          <div style="display: flex;justify-content: space-between;width: 100%;padding: 5px 10px">
           <div style="font-size: 14px">苏州历史地名知识图谱</div>
            <lay-tooltip content="退出登录">
              <div style="cursor:pointer;margin-left: 5px" @click="logOut">
                <img src="/icon/logout.svg" style="width: 16px;"/>
              </div>
            </lay-tooltip>
          </div>
        </div>
        <div class="side-menu-wrapper">
          <div
              class="side-menu1"
              v-if="appStore.subfield && appStore.subfieldPosition == 'side'"
          >
            <global-main-menu
                :collapse="true"
                :menus="mainMenus"
                :selectedKey="mainSelectedKey"
                @changeSelectedKey="changeMainSelectedKey"
            ></global-main-menu>
          </div>
          <div class="side-menu2">
            <global-menu
                :collapse="appStore.collapse"
                :menus="menus"
                :openKeys="openKeys"
                :selectedKey="selectedKey"
                @changeOpenKeys="changeOpenKeys"
                @changeSelectedKey="changeSelectedKey"
            ></global-menu>
          </div>
        </div>
      </lay-side>
      <lay-layout style="width: 0px">
        <lay-body>
          <global-content></global-content>
        </lay-body>
        <lay-footer></lay-footer>
      </lay-layout>
    </lay-layout>
    <global-setup v-model="visible"></global-setup>
  </lay-config-provider>
</template>

<script lang="ts">
import {computed, onMounted, ref} from 'vue'
import {useAppStore} from '../store/app'
import {useUserStore} from '../store/user'
import GlobalSetup from './global/GlobalSetup.vue'
import GlobalContent from './global/GlobalContent.vue'
import GlobalBreadcrumb from './global/GlobalBreadcrumb.vue'
import GlobalTab from './global/GlobalTab.vue'
import GlobalMenu from './global/GlobalMenu.vue'
import GlobalMainMenu from './global/GlobalMainMenu.vue'
import GlobalMessageTab from './global/GlobalMessageTab.vue'
import {useRouter} from 'vue-router'
import {useMenu} from './composable/useMenu'
import zh_CN from '../lang/zh_CN'
import en_US from '../lang/en_US'

export default {
  components: {
    GlobalSetup,
    GlobalContent,
    GlobalTab,
    GlobalMenu,
    GlobalBreadcrumb,
    GlobalMainMenu,
    GlobalMessageTab
  },
  setup() {
    const appStore = useAppStore()
    const userInfoStore = useUserStore()
    const fullscreenRef = ref()
    const visible = ref(false)
    const sideWidth = computed(() =>
        appStore.collapse
            ? '60px'
            : appStore.subfield && appStore.subfieldPosition == 'side'
                ? '280px'
                : '220px'
    )
    const router = useRouter()

    const {
      selectedKey,
      openKeys,
      menus,
      mainMenus,
      mainSelectedKey,
      changeMainSelectedKey,
      changeSelectedKey,
      changeOpenKeys
    } = useMenu()

    onMounted(() => {
      if (document.body.clientWidth < 768) {
        appStore.collapse = true
      }
      userInfoStore.loadMenus()
      userInfoStore.loadPermissions()
    })

    const changeVisible = () => {
      visible.value = !visible.value
    }

    const currentIndex = ref('1')

    const collapse = () => {
      appStore.collapse = !appStore.collapse
    }

    const refresh = () => {
      appStore.routerAlive = false
      setTimeout(function () {
        appStore.routerAlive = true
      }, 500)
    }

    const logOut = () => {
      const userInfoStore = useUserStore()
      userInfoStore.token = ''
      userInfoStore.userInfo = {}
      router.push('/login')
    }

    const locales = [
      {name: 'zh_CN', locale: zh_CN, merge: true},
      {name: 'en_US', locale: en_US, merge: true}
    ]

    function toUserInfo() {
      router.push('/enrollee/profile')
    }

    function toSystemSet() {
      router.push('/system/menu')
    }

    const flag = ref(false)

    function changeDropdown() {
      flag.value = !flag.value
    }

    return {
      sideWidth,
      mainSelectedKey,
      fullscreenRef,
      appStore,
      visible,
      menus,
      mainMenus,
      userInfoStore,
      currentIndex,
      selectedKey,
      openKeys,
      collapse,
      changeOpenKeys,
      changeSelectedKey,
      changeMainSelectedKey,
      changeVisible,
      refresh,
      logOut,
      locales,
      toUserInfo,
      toSystemSet,
      changeDropdown,
      flag
    }
  }
}
</script>

<style lang="less">
@media screen and (max-width: 767px) {
  .layui-side {
    position: absolute;
    height: 100vh;
  }
}

/*鼠标经过背景色，增加了improtant，否则设置无效*/
.layui-header .layui-nav-item .layui-icon:hover {
  background: whitesmoke !important;
}

/*面包屑颜色兼容*/
.layui-header .layui-nav-item .layui-breadcrumb a {
  color: #999 !important;
}

.layui-header .layui-nav-item .layui-breadcrumb a:nth-last-child(2) {
  color: #666 !important;
}

/*图标默认颜色修复，指定 .layui-icon 去掉improtant，否则无法设置图标其他颜色*/
.layui-header .layui-nav-item .layui-icon {
  color: #666;
}

/*取消默认a标签的padding:0 20px，否则扩大图标后容器变形*/
.layui-header .layui-nav-item > a {
  padding: 0 !important;
}

/*扩大图标尺寸与所在容器大小一致，默认大小导致鼠标必须点击图标才能触发事件效果*/
.layui-header .layui-nav-item .layui-icon {
  height: 50px;
  padding: 20px;
}

/*增加鼠标经过图标时改变图标颜色，颜色为当前系统主题色*/
.layui-header .layui-nav-item .layui-icon:hover {
  color: var(--global-primary-color) !important;
}

.grey-mode {
  filter: grayscale(1);
}

.side-menu-wrapper {
  width: 100%;
  overflow-y: auto;
  height: calc(100% - 52px);
  display: flex;
}

.side-menu-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.side-menu-wrapper::-webkit-scrollbar-thumb {
  border-radius: 10px;
  background-color: rgb(40, 51, 62);
}

.light .side-menu-wrapper::-webkit-scrollbar-thumb {
  background-color: #e2e2e2;
}

.side-menu1 {
  width: 60px;
  flex: 0 0 60px;
  border-right: 1px solid rgba(0, 0, 0, 0.12);
}

.light .side-menu1 {
  border-right: 1px solid whitesmoke;
}

.side-menu2 {
  flex: 1;
}

.changeBgc {
  background-color: #171717 !important;
}

.underpainting {
  .layui-tab-title {
    .layui-this {
      color: var(--global-primary-color) !important;
      border-bottom: 2px solid var(--global-primary-color) !important;
      background-color: #009b8e0d !important;

      .layui-icon {
        color: var(--global-primary-color) !important;
      }
    }
  }
}

.layui-body
> .global-tab
> .layui-tab
> .layui-tab-head
> .layui-tab-title
> li {
  height: 38px;
  line-height: 38px;
}

.designer {
  padding-left: 5px;
  box-sizing: border-box;

  .layui-tab-head {
    background-color: unset !important;
  }

  .layui-tab-title {
    background-color: unset !important;

    > li {
      background-color: #fff;
      margin: 5px 0 0 5px;
      border-radius: 4px;
      height: 32px !important;
      line-height: 32px !important;
    }
  }
}
</style>
