// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',

  devtools: { enabled: true }, //这个就是网页底部那个悬浮图标，是一个调试神器，不过很碍眼。想把它隐藏可以把这句代码改成false

  devServer: {
    host: '0.0.0.0', //允许局域网访问。和后端配置监听所有网卡、跨域支持一样，必须在这里写这么一句，别人才能访问我这个平台
    port: 3000 //可以在这里修改端口号
  },

  routeRules: { //增加代理配置
    '/api/**': { proxy: 'http://127.0.0.1:8000/api/**' } //这里写后端的本地地址即可，因为后端和Nuxt通常在同一台机器上运行
  },

  ssr: false //关闭SSR，退化成纯SPA模式
})
