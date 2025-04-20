import axios, {AxiosRequestHeaders, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import {useUserStore} from "../store/user";
import {layer} from '@layui/layui-vue';
import router from '../router'
import config from '@/config'

type TAxiosOption = {
    timeout: number;
    baseURL: string;
}

const axiosConfig: TAxiosOption = {
    timeout: config.timeout,
    baseURL: config.baseURL
}

class Http {
    service;

    constructor(config: TAxiosOption) {
        this.service = axios.create(config)

        /* 请求拦截 */
        this.service.interceptors.request.use((config: InternalAxiosRequestConfig) => {
            const userInfoStore = useUserStore();
            if (userInfoStore.token) {
                (config.headers as AxiosRequestHeaders).token = userInfoStore.token as string
            } else {
                if (router.currentRoute.value.path !== '/login') {
                    router.push('/login');
                }
            }
            return config
        }, error => {
            return Promise.reject(error);
        })

        /* 响应拦截 */
        this.service.interceptors.response.use((response: AxiosResponse<any>) => {
            console.log('API响应原始数据:', response.data)
            
            // 统一返回数据，不执行其他操作
            return response.data;
            
        }, error => {
            console.error('API请求错误:', error);
            return Promise.reject(error)
        })
    }

    /* GET 方法 */
    get<T>(url: string, params?: object, _object = {}): Promise<any> {
        return this.service.get(url, {params, ..._object})
    }

    /* POST 方法 */
    post<T>(url: string, params?: object, _object = {}): Promise<any> {
        return this.service.post(url, params, _object)
    }

    /* PUT 方法 */
    put<T>(url: string, params?: object, _object = {}): Promise<any> {
        return this.service.put(url, params, _object)
    }

    /* DELETE 方法 */
    delete<T>(url: string, params?: any, _object = {}): Promise<any> {
        return this.service.delete(url, {params, ..._object})
    }
}

export default new Http(axiosConfig)
