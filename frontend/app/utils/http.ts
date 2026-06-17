import axios from 'axios'

export const API_BASE_URL = '/api' //走 Nuxt devProxy 转发到后端 8000，同源访问，外网穿透只需暴露 3000 端口

const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000000, // 500 minutes for long-running analysis（开发阶段用）
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[HTTP Error]', error?.response?.data || error.message)
    return Promise.reject(error)
  },
)

export default http
