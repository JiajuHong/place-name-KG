import axios from 'axios'
import config from '@/config'

const httpUtil = axios.create({
    timeout: config.timeout,
    baseURL: config.baseURL
})

httpUtil.interceptors.response.use(response => response.data)

export default httpUtil