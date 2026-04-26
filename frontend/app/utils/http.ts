import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
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
