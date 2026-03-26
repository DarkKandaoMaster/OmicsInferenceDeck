import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  server: {
    host: '0.0.0.0', //允许局域网访问。和后端配置监听所有网卡、跨域支持一样，必须在这里写这么一句，别人才能访问我这个平台
    proxy: { // 增加代理配置
      '/api': {
        target: 'http://127.0.0.1:8000', // 这里写后端的本地地址即可，因为后端和 Vite 通常在同一台机器上运行
        changeOrigin: true,
      }
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
