<template>
  <div class="login-wrap">
    <div class="login-root">
      <div class="login-main">
        <div class="login-container">
          <div class="login-side">
            <div class="login-bg-title">
              <h1 style="letter-spacing: 1px;font-weight: 700">苏州历史地名知识图谱</h1>

<!--              <h3 style="margin: 20px auto">-->
<!--                Knowledge Graph Visualization System-->
<!--              </h3>-->

              <div>
                <img src="/login.png" style="width: 300px;margin-top: 40px"/>
              </div>
            </div>
          </div>
          <div class="login-ID">
            <lay-tab type="brief" v-model="method">
              <lay-tab-item title="登录" id="1">
                <div style="height: 250px">
                  <lay-form-item :label-width="0">
                    <lay-input :allow-clear="true" prefix-icon="layui-icon-username" placeholder="用户名"
                               v-model="loginForm.account"></lay-input>
                  </lay-form-item>
                  <lay-form-item :label-width="0">
                    <lay-input :allow-clear="true" prefix-icon="layui-icon-password" placeholder="密码" password
                               type="password" v-model="loginForm.password"></lay-input>
                  </lay-form-item>
                  <lay-checkbox value="" name="like" v-model="remember" skin="primary" label="1">记住密码</lay-checkbox>
                  <lay-form-item :label-width="0">
                    <lay-button style="margin-top: 80px" type="primary" :loading="loging" :fluid="true"
                                loadingIcon="layui-icon-loading" @click="loginSubmit">登录
                    </lay-button>
                  </lay-form-item>
                </div>
              </lay-tab-item>
              <lay-tab-item title="注册" id="2">
                <div style="height: 250px">
                  <lay-form-item :label-width="0">
                    <lay-input :allow-clear="true" prefix-icon="layui-icon-username" placeholder="用户名"
                               v-model="loginForm.account"></lay-input>
                  </lay-form-item>
                  <lay-form-item :label-width="0">
                    <lay-input :allow-clear="true" prefix-icon="layui-icon-username" placeholder="昵称"
                               v-model="loginForm.name"></lay-input>
                  </lay-form-item>
                  <lay-form-item :label-width="0">
                    <lay-input :allow-clear="true" prefix-icon="layui-icon-password" placeholder="密码" password
                               type="password" v-model="loginForm.password"></lay-input>
                  </lay-form-item>
                  <lay-checkbox value="" name="like" v-model="remember" skin="primary" label="1">记住密码</lay-checkbox>
                  <lay-form-item :label-width="0">
                    <lay-button style="margin-top: 60px" type="primary" :loading="loging" :fluid="true"
                                loadingIcon="layui-icon-loading" @click="signinSubmit">注册
                    </lay-button>
                  </lay-form-item>
                </div>
              </lay-tab-item>
            </lay-tab>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import {loginQrcode, verificationImg} from '../../api/module/commone'
import {defineComponent, reactive, ref} from 'vue'
import {useRouter} from 'vue-router'
import {useUserStore} from '../../store/user'
import {layer} from "@layui/layui-vue"
import httpUtil from "@/utils/httpUtil";

export default defineComponent({
  setup() {
    const router = useRouter()
    const userStore = useUserStore()
    const method = ref('1')
    const verificationImgUrl = ref('')
    const loging = ref(false);
    const loginQrcodeText = ref('')
    const remember = ref(false)
    const loginForm = reactive({
      account: '',
      password: '',
    })

    const loginSubmit = async () => {
      loging.value = true;
      httpUtil.post("/api/login", {
        account: loginForm.account,
        password: loginForm.password
      })
          .then(({data, code, msg}) => {
            if (code == 200) {
              userStore.token = data
              userStore.loadMenus()
              userStore.loadPermissions()
              router.push('/')
            } else {
              layer.msg(msg, {icon: 2})
            }
          })
          .finally(() => (loging.value = false));
    }

    const signinSubmit = async () => {
      loging.value = true;
      httpUtil.post("/api/sign_in", loginForm)
          .then(({data, code, msg}) => {
            if (code == 200) {
              layer.msg('注册成功', {icon: 1})
            } else {
              layer.msg(msg, {icon: 2})
            }
          })
          .finally(() => (loging.value = false));
    }

    const toRefreshImg = async () => {
      let {data, code, msg} = await verificationImg()
      if (code == 200) {
        verificationImgUrl.value = data.data
      } else {
        layer.msg(msg, {icon: 2})
      }
    }
    const toRefreshQrcode = async () => {
      let {data, code, msg} = await loginQrcode()
      if (code == 200) {
        loginQrcodeText.value = data.data
      } else {
        layer.msg(msg, {icon: 2})
      }
    }

    return {
      toRefreshQrcode,
      toRefreshImg,
      loginSubmit,
      signinSubmit,
      loginForm,
      remember,
      method,
      loging
    }
  }
})
</script>

<style scoped>

.login-wrap {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  overflow: auto;
  min-width: 600px;
  z-index: 9;
  background-image: url(background.png);
  background-repeat: no-repeat;
  background-size: cover;
  min-height: 100vh;
}

.login-wrap :deep(.layui-input-block) {
  margin-left: 0 !important;
}

.login-root {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  justify-content: center;
  width: 100%;
  min-width: 320px;
  background-color: initial;
}

.login-main {
  position: relative;
  display: block;
}

.logo-container {
  max-width: calc(100vw - 28px);
  margin-bottom: 40px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-container .logo {
  display: inline-block;
  height: 30px;
  width: 143px;
  background: url() no-repeat 50%;
  background-size: contain;
  cursor: pointer;
}

.login-container {
  position: relative;
  overflow: hidden;
  width: 940px;
  height: 540px;
  max-width: calc(100vw - 28px);
  border-radius: 4px;
  background: hsla(0, 0%, 100%, 0.5);
  backdrop-filter: blur(30px);
  display: flex;
  box-shadow: 6px 6px 12px 4px rgba(0, 0, 0, 0.1);
}

.login-side {
  padding: 40px 20px 20px;
  background-color: #ffffff;
  flex: 1;
  height: 100%;
}

.login-bg-title {
  flex: 1;
  height: 110%;
  color: #01500c;
  text-align: center;
  background-repeat: no-repeat;
  background-position: bottom;
  text-align: center;
  min-width: 200px;
}

.login-ID {
  padding: 20px 30px;
  min-width: 420px;
}

.login-container .layui-tab-head {
  background: transparent;
}

.login-container .layui-input-wrapper {
  margin-top: 10px;
  margin-bottom: 10px;
}

.login-container .layui-input-wrapper {
  margin-top: 12px;
  margin-bottom: 12px;
}

.login-container .assist {
  margin-top: 5px;
  margin-bottom: 5px;
  letter-spacing: 2px;
}

.login-container .layui-btn {
  margin: 10px 0px 10px 0px;
  letter-spacing: 2px;
  height: 40px;
}

.login-container .layui-line-horizontal {
  letter-spacing: 2px;
  margin-bottom: 34px;
  margin-top: 24px;
}

.other-ways {
  display: flex;
  justify-content: space-between;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 14px;
  font-weight: 400;
}

.other-ways li {
  width: 100%;
}

.line-container {
  justify-content: center;
  align-items: center;
  text-align: center;
  cursor: pointer;
}

.line-container .icon {
  height: 28px;
  width: 28px;
  margin-right: 0;
  vertical-align: middle;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px 0 rgb(9 30 66 / 4%), 0 1px 4px 0 rgb(9 30 66 / 10%),
  0 0 1px 0 rgb(9 30 66 / 10%);
}

.line-container .text {
  display: block;
  margin: 12px 0 0;
  font-size: 12px;
  color: #8592a6;
}

:deep(.layui-tab-title .layui-this) {
  background-color: transparent;
}
</style>
