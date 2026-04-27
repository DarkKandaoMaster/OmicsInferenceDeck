import axios from 'axios'

export const API_BASE_URL = 'http://127.0.0.1:8000/api'

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
