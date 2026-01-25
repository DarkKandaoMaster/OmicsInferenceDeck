<script setup>
import { ref } from 'vue'
import axios from 'axios'

// 定义响应式数据，用于存储后端返回的信息
const backendResponse = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

// 模拟的算法选项（模仿论文中的算法选择功能，目前仅作展示）
const selectedAlgorithm = ref('PIntMF') 
const algorithms = ['PIntMF', 'Subtype-GAN', 'NEMO', 'SNF']

// 核心功能：点击按钮触发的函数
const runAnalysis = async () => {
  // 重置状态
  isLoading.value = true
  errorMessage.value = ''
  backendResponse.value = null

  try {
    // 发送 POST 请求给后端 FastAPI
    // 假设后端地址是 http://127.0.0.1:8000
    // 这里的 '/api/run' 是我们要和后端约定的接口路径
    const res = await axios.post('http://127.0.0.1:8000/api/run', {
      algorithm: selectedAlgorithm.value,
      timestamp: new Date().toISOString()
    })

    // 请求成功，将后端返回的数据保存到 backendResponse
    backendResponse.value = res.data
    console.log('后端返回数据:', res.data)

  } catch (error) {
    console.error('请求失败:', error)
    errorMessage.value = '连接后端失败，请检查 FastAPI 是否启动并配置了 CORS。'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="container">
    <header class="header">
      <div class="logo">InferenceDeck</div>
      <nav class="nav">
        <span>Home</span>
        <span class="active">Analysis</span>
        <span>Resources</span>
        <span>Help</span>
      </nav>
    </header>

    <main class="main-content">
      <div class="analysis-panel">
        <h1>多组学癌症亚型分析</h1>
        <p class="description">
          基于多组学数据的癌症分型方法评估及平台研发。
          <br>请选择算法并点击运行以测试后端连接。
        </p>

        <div class="control-group">
          <label>选择聚类算法：</label>
          <select v-model="selectedAlgorithm">
            <option v-for="algo in algorithms" :key="algo" :value="algo">
              {{ algo }}
            </option>
          </select>
        </div>

        <div class="action-area">
          <button 
            @click="runAnalysis" 
            :disabled="isLoading"
            class="run-btn"
          >
            <span v-if="isLoading">正在运行...</span>
            <span v-else>运行分析 (Run Analysis)</span>
          </button>
        </div>

        <div v-if="backendResponse || errorMessage" class="result-area">
          <h3>后端响应结果：</h3>
          
          <div v-if="backendResponse" class="success-box">
            <p><strong>状态:</strong> {{ backendResponse.status }}</p>
            <p><strong>信息:</strong> {{ backendResponse.message }}</p>
            <p><strong>接收到的数据:</strong></p>
            <pre>{{ backendResponse.data }}</pre>
          </div>

          <div v-if="errorMessage" class="error-box">
            {{ errorMessage }}
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* 整体容器布局 */
.container {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  color: #333;
  min-height: 100vh;
  background-color: #f5f7fa;
}

/* 头部样式 - 模仿论文图14的简约风格 */
.header {
  background-color: #2c3e50;
  color: white;
  padding: 0 40px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.logo {
  font-size: 24px;
  font-weight: bold;
  letter-spacing: 1px;
}

.nav span {
  margin-left: 30px;
  cursor: pointer;
  opacity: 0.8;
  font-size: 16px;
}

.nav span:hover, .nav span.active {
  opacity: 1;
  font-weight: bold;
  border-bottom: 2px solid #42b983;
}

/* 主内容区域 */
.main-content {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

.analysis-panel {
  background: white;
  width: 800px;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  text-align: center;
}

h1 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.description {
  color: #666;
  margin-bottom: 30px;
  line-height: 1.6;
}

/* 控制组件样式 */
.control-group {
  margin-bottom: 20px;
}

select {
  padding: 8px 12px;
  font-size: 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 200px;
}

/* 按钮样式 */
.run-btn {
  background-color: #42b983; /* Vue的主题色，也适合科研平台的清新感 */
  color: white;
  border: none;
  padding: 12px 30px;
  font-size: 18px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.run-btn:hover:not(:disabled) {
  background-color: #3aa876;
}

.run-btn:disabled {
  background-color: #a8d5c2;
  cursor: not-allowed;
}

/* 结果区域样式 */
.result-area {
  margin-top: 40px;
  text-align: left;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.success-box {
  background-color: #e8f5e9;
  border: 1px solid #c8e6c9;
  padding: 15px;
  border-radius: 4px;
  color: #2e7d32;
}

.error-box {
  background-color: #ffebee;
  border: 1px solid #ffcdd2;
  padding: 15px;
  border-radius: 4px;
  color: #c62828;
}

pre {
  background: #f1f1f1;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}
</style>