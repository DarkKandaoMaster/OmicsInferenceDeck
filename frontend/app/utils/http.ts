import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes for long-running analysis
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[HTTP Error]', error?.response?.data || error.message)
    return Promise.reject(error)
  },
)

export default http
