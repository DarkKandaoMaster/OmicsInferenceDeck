<script setup>
import { ref } from 'vue'
import axios from 'axios'

// 定义响应式数据，用于存储后端返回的信息
const backendResponse = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

// 模拟的算法选项（模仿论文中的算法选择功能，目前仅作展示）
const selectedAlgorithm = ref('K-means') // 将默认算法改为我们正在测试的 K-means
const algorithms = ['K-means', 'PIntMF', 'Subtype-GAN', 'NEMO', 'SNF'] // 添加 K-means 到列表

const selectedFile = ref(null) // 用于存储用户在输入框中选中的文件对象
const uploadStatus = ref('')   // 用于存储上传状态的提示信息（如“上传成功”）

const uploadedFilename = ref('') // 新增：用于存储上传成功后的文件名，以便发送给分析接口
// K-means 算法的参数变量，将与前端输入框进行双向绑定
const kValue = ref(3)         //定义聚类簇数，初始值设为3
const randomSeed = ref(42)    //定义随机种子，用于保证结果可复现，初始值42
const maxIter = ref(300)      //定义最大迭代次数，初始值300

// 新增：执行文件上传的函数
const uploadFile = async () => {
  // 防御性编程：如果没有选择文件，直接返回并提示
  if (!selectedFile.value) {
    alert("请先选择一个文件！")
    return
  }

  // 创建 FormData 对象，这是 HTML5 中用于异步上传文件的标准方式
  const formData = new FormData()
  // 将选中的文件追加到表单数据中，键名为 'file'，需与后端接口参数名一致
  formData.append('file', selectedFile.value)

  try {
    // 设置上传状态为“上传中...”
    uploadStatus.value = "正在上传..."
    
    // 发送 POST 请求到后端的上传接口 /api/upload
    // 注意：必须设置 Content-Type 为 multipart/form-data，但在 axios 中传输 FormData 时通常会自动设置
    const res = await axios.post('http://127.0.0.1:8000/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data' // 显式指定请求头，确保后端正确解析文件流
      }
    })
    
    // 上传成功，显示后端返回的消息
    uploadStatus.value = `✅ 上传成功: ${res.data.filename}`
    console.log('上传结果:', res.data)
    uploadedFilename.value = res.data.filename // 关键：保存后端返回的文件名，下一步分析要用

  } catch (error) {
    // 捕获错误并打印日志
    console.error('上传出错:', error)
    // 在界面上显示错误提示
    // 修改：增强错误处理，显示后端返回的具体校验失败原因
    if (error.response && error.response.data && error.response.data.detail) {
      // 如果后端返回了详细错误信息（比如我们在server.py里写的那些ValueError）
      // 使用 HTML 换行符让长错误信息更好读，或者直接显示
      uploadStatus.value = `❌ 数据不合规: ${error.response.data.detail}`
    } else {
      // 网络错误或其他未知错误
      uploadStatus.value = "❌ 上传失败，请检查后端服务是否启动"
    }
    
    // 上传失败后，清空已保存的文件名，防止用户用上一个合法文件的名义去跑这个非法文件的名字（虽然文件已经被后端删了）
    uploadedFilename.value = ''
  }
}

// 修改：处理文件选择框改变的事件
const handleFileChange = (event) => {
  // 获取当前输入框中选中的第一个文件
  const file = event.target.files[0]
  
  // 只有当用户确实选择了文件时才执行（防止用户打开文件框后取消，导致报错）
  if (file) {
    selectedFile.value = file // 更新响应式变量
    uploadStatus.value = ''   // 清空旧的状态提示
    
    // 新增：一旦选中文件，直接触发上传函数，无需用户点击按钮
    uploadFile() 
  }
}

// 核心功能：点击按钮触发的函数
const runAnalysis = async () => {
  // 检查是否已经上传了文件
  if (!uploadedFilename.value) {
    alert("请先上传数据文件！")
    return
  }

  // 重置状态
  isLoading.value = true
  errorMessage.value = ''
  backendResponse.value = null

  try {
    // 发送 POST 请求给后端 FastAPI
    // 假设后端地址是 http://127.0.0.1:8000
    // 这里的 '/api/run' 是我们要和后端约定的接口路径
    const res = await axios.post('http://127.0.0.1:8000/api/run', {
      algorithm: selectedAlgorithm.value, // 发送选中的算法名称
      timestamp: new Date().toISOString(), // 发送当前时间戳
      filename: uploadedFilename.value,    // 发送要处理的文件名
      n_clusters: kValue.value,            // 新增：发送用户自定义的 K 值
      random_state: randomSeed.value,      // 新增：发送用户自定义的随机种子
      max_iter: maxIter.value              // 新增：发送用户自定义的最大迭代次数
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

        <div class="step-section upload-section">
          <h3>1. 数据上传 (Data Upload)</h3>
          <div class="upload-controls">
            <input type="file" @change="handleFileChange" />
          </div>
          <p class="status-message" :class="{ 'error-text': uploadStatus.startsWith('❌') }">
            {{ uploadStatus }}
          </p>
        </div>
        <div class="step-section control-group">
          <h3>2. 算法选择 (Clustering Method)</h3>
          <label>选择聚类算法：</label>
          <select v-model="selectedAlgorithm">
            <option v-for="algo in algorithms" :key="algo" :value="algo">
              {{ algo }}
            </option>
          </select>

          <div v-if="selectedAlgorithm === 'K-means'" class="params-box">
            <h4>K-means 参数配置：</h4>
            
            <div class="param-item">
              <label>簇数 (K):</label>
              <input type="number" v-model="kValue" min="2" max="20" />
            </div>

            <div class="param-item">
              <label>随机种子:</label>
              <input type="number" v-model="randomSeed" />
            </div>

            <div class="param-item">
              <label>最大迭代:</label>
              <input type="number" v-model="maxIter" step="50" />
            </div>
          </div>
        </div>

        <div class="step-section action-area">
          <h3>3. 运行分析 (Execution)</h3>
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

/* 步骤模块的通用样式，使界面看起来像分步骤操作 */
.step-section {
  text-align: left; /* 内容左对齐 */
  background-color: #f8f9fa; /* 浅灰色背景区分模块 */
  padding: 20px; /* 内边距 */
  margin-bottom: 20px; /* 底部间距 */
  border-radius: 8px; /* 圆角 */
  border: 1px solid #e9ecef; /* 细边框 */
}

.step-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 16px;
  color: #2c3e50;
  border-bottom: 2px solid #42b983; /* 标题下划线 */
  padding-bottom: 5px;
  display: inline-block;
}

/* 新增：上传控件布局 */
.upload-controls {
  display: flex; /* 弹性布局 */
  gap: 15px; /* 控件之间的间距 */
  align-items: center; /* 垂直居中 */
}

/* 新增：上传按钮样式 */
.upload-btn {
  background-color: #3498db; /* 蓝色背景 */
  color: white; /* 白色文字 */
  border: none; /* 无边框 */
  padding: 8px 16px; /* 内边距 */
  border-radius: 4px; /* 圆角 */
  cursor: pointer; /* 鼠标悬停手势 */
  transition: background-color 0.3s; /* 颜色渐变动画 */
}

.upload-btn:hover:not(:disabled) {
  background-color: #2980b9; /* 悬停深蓝色 */
}

.upload-btn:disabled {
  background-color: #bdc3c7; /* 禁用时灰色 */
  cursor: not-allowed; /* 禁用鼠标手势 */
}

/* 新增：状态消息文本样式 */
.status-message {
  margin-top: 10px;
  font-size: 14px;
  font-weight: bold;
  color: #27ae60; /* 绿色文字 */
  white-space: pre-wrap; /* 新增：允许错误信息自动换行，防止太长溢出 */
  word-break: break-all; /* 新增：允许在单词内换行 */
}

/* 新增：错误文本的红色样式 */
.error-text {
  color: #e74c3c !important; /* 强制使用红色 */
}

.control-group {
  margin-bottom: 20px;
}

/* 参数配置区域的样式 */
.params-box {
  margin-top: 15px;       /* 与上方下拉框保持距离 */
  padding: 15px;          /* 内部留白 */
  background-color: #fff; /* 白色背景 */
  border: 1px dashed #bbb;/* 虚线边框，表示这是可选配置区 */
  border-radius: 6px;     /* 圆角 */
}

/* 标题样式 */
.params-box h4 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 14px;
  color: #555;
}

/* 单个参数项的布局：使用 inline-block 让它们横向排列 */
.param-item {
  display: inline-block; /* 让输入框在一行显示 */
  margin-right: 20px; /*这一项与下一项的间距 */
  margin-bottom: 5px;
}

/* 参数标签样式 */
.param-item label {
  font-size: 14px;
  margin-right: 8px; /* 标签与输入框的距离 */
  color: #666;
}

/* 输入框样式 */
.param-item input {
  width: 60px; /* 限制输入框宽度 */
  padding: 5px;
  border: 1px solid #ddd;
  border-radius: 4px;
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