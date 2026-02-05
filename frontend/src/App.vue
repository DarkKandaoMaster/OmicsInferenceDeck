<script setup>
import { ref,computed,nextTick } from 'vue' //引入Vue框架的核心函数 //ref：用于定义基本类型的响应式数据（数据变化时视图自动更新） //computed：用于定义计算属性（依赖其他数据变化而自动重新计算并缓存结果） //nextTick：用于确保DOM元素渲染完成后再执行绘图代码
import axios from 'axios' //引入 axios 库，用于在浏览器端发送 HTTP 请求，与后端服务器进行数据交互
import * as echarts from 'echarts' //引入整个 echarts 库，命名为 echarts #为什么不这么写“import echarts from 'echarts'”？这是因为不同的库有不同的导出策略

// ===================== 状态定义区 =====================

const backendResponse=ref(null) //定义响应式变量，用于存储从后端 API 接收到的 JSON 响应数据 //对应论文图3中后端返回的 "Clustering results"

const isLoading=ref(false) //定义布尔类型的响应式变量，用于控制“加载中”状态（如禁用按钮、显示Loading动画） //防止用户在分析计算过程中重复点击

const errorMessage=ref('') //定义字符串变量，用于存储请求失败时的错误描述信息，以便在前端界面显示错误提示

const selectedAlgorithm=ref('') //定义当前选中的算法，默认值为空 //双向绑定到界面的下拉选择框

const algorithms=['K-means', 'PIntMF', 'Subtype-GAN', 'NEMO', 'SNF'] //定义算法候选数组，供下拉框渲染使用 //这些算法对应论文表3和表5中提到的 "11种前沿多组学聚类算法" 及基础算法

const selectedFile=ref(null) //定义响应式变量，用于存储用户通过文件输入框选择的本地文件对象 //对应论文 3.3.2 节提到的 "User uploaded omics data"

const uploadStatus=ref('') //定义字符串变量，用于向用户反馈文件上传的进度或结果（如 "上传成功" 或 错误信息）

const uploadedFilename=ref('') //定义字符串变量，用于存储后端返回的用户上传文件的新名称 //前端在后续调用 "运行分析" 接口时，需要将此文件名传回后端，指定处理哪个文件

const chartRef=ref(null) //定义一个引用变量，用来绑定template中的图表容器div

// ===================== 数据格式处理区 =====================

const dataFormat=ref('row_feat_col_sample') //定义数据矩阵的格式选项，默认值为 'row_feat_col_sample' //对应论文 2.2.1 数据预处理中对 "特征(Features)" 和 "样本(Samples)" 排列方式的定义

//定义表达矩阵格式的常量数组，包含显示标签(label)和传递给后端的实际值(value) //这是为了适配不同来源的组学数据（如 CSV 文件的转置情况）
const dataFormatOptions=[
  { label: '第一行为特征名称，第一列为样本名称', value: 'row_feat_col_sample' },
  { label: '第一行为样本名称，第一列为特征名称', value: 'row_sample_col_feat' },
  { label: '第一行为特征名称', value: 'row_feat' },
  { label: '第一行为样本名称', value: 'row_sample' },
  { label: '第一列为特征名称', value: 'col_feat' },
  { label: '第一列为样本名称', value: 'col_sample' },
  { label: '纯数据：每一行是样本', value: 'no_name_row_sample' },
  { label: '纯数据：每一行是特征', value: 'no_name_row_feat' },
]

//定义计算属性，根据当前选中的 dataFormat 动态生成 CSV 文本示例 //帮助用户校验自己的数据格式是否符合预期
const exampleText=computed(()=>{
  switch(dataFormat.value){ //根据 dataFormat.value 的不同值，返回对应的字符串模板
    case 'row_feat_col_sample':
      return `,特征1,特征2\n样本1,10,20\n样本2,30,40` //【【【【【这里记得修改一下
    case 'row_sample_col_feat':
      return `,样本1,样本2\n特征1,10,30\n特征2,20,40`
    case 'row_feat':
      return `特征1,特征2\n10,20\n30,40`
    case 'row_sample':
      return `样本1,样本2\n10,30\n20,40`
    case 'col_feat':
      return `特征1,10,20\n特征2,30,40`
    case 'col_sample':
      return `样本1,10,20\n样本2,30,40`
    case 'no_name_row_sample':
      return `10,20\n30,40`
    case 'no_name_row_feat':
      return `10,30\n20,40`
    default:
      return ''
  }
})

// ===================== 算法参数配置区 =====================

const kValue=ref(3) //定义簇的数量 (K值)，初始值3 //对应论文 2.1.2 节中提到的 "最大簇数(K值)" 或论文表2中的 K 值设定

const maxIter=ref(300) //定义最大迭代次数，初始值300，用于控制算法收敛前的最大循环数，防止死循环

const randomSeed=ref(42) //定义随机种子，初始值42 //确保算法结果的可复现性（论文 2.1.2 提到 Consensus Clustering 需要重采样，种子很重要）

// ===================== 方法定义区 =====================

//定义异步函数，处理文件上传逻辑
const uploadFile= async ()=>{
  if(!selectedFile.value){ //防御性编程：检查 selectedFile 是否为空，若为空则弹出浏览器原生警告并中断执行。正常情况下，因为handleFileChange函数中有个if(file)，所以不可能触发这个if
    alert("请先选择一个文件！")
    return
  }

  const formData=new FormData() //创建 FormData 对象，这是 Web API 中用于构建键值对集合的标准对象，可以用作请求体，是JSON格式 //专门用于通过 XMLHttpRequest 或 fetch/axios 发送 multipart/form-data 格式的数据（即文件上传）
  formData.append('file',selectedFile.value) //将用户选择的文件追加到表单数据中，键名为'file'。这里需与后端接口"/api/upload"的形参参数名保持一致
  formData.append('data_format',dataFormat.value) //将用户选择的数据格式字符串追加到表单数据中

  try{
    uploadStatus.value="正在上传..." //更新界面状态提示，告知用户上传正在进行
    //使用axios发送POST请求到后端接口"/api/upload"
    // 参数1：接口URL
    // 参数2：请求体，就是那个formData
    // 参数3：配置对象，显式指定Content-Type头部，确保后端能正确解析文件流
    const res=await axios.post('http://127.0.0.1:8000/api/upload',formData,{
      headers:{
        'Content-Type': 'multipart/form-data' //显式指定请求头，确保后端能正确解析文件流
      }
    })
    //请求成功后，后端不是会返回一个字典嘛，我们要根据这个字典修改前端
    uploadStatus.value=`✅ 上传成功: ${res.data.original_filename} \n📊 文件原始形状: ${   res.data.original_shape ? `(行=${res.data.original_shape[0]}, 列=${res.data.original_shape[1]})` : ''   }` //更新状态提示为成功，并显示用户上传文件的原始名称和文件原始形状
    console.log('上传结果:',res.data) //在控制台打印日志
    uploadedFilename.value=res.data.filename //将后端返回的用户上传文件的新名称保存到前端变量，下一步分析要用
  }
  catch(error){ //捕获并处理请求过程中的错误（如网络错误、4xx/5xx 状态码）
    console.error('上传出错:',error) //在控制台打印日志
    if(error.response && error.response.data && error.response.data.detail){ //如果遇到错误，后端不是会raise HTTPException嘛，我们先来判断一下后端有没有返回详细错误信息（比如那些ValueError），这通常是文件解析失败返回的信息
      uploadStatus.value=`❌ 数据不合规: ${error.response.data.detail}`
    }
    else{ //不然的话就是网络连接中断or后端未启动or其他未知错误
      uploadStatus.value="❌ 上传失败，请检查后端服务是否启动"
    }
    uploadedFilename.value='' //既然遇到错误了，那么就要清空文件名变量，避免后续操作使用非法文件名。顺带一提，既然遇到错误了，那么这个文件也肯定已经被后端删了
  }
}

//定义事件处理函数，监听文件输入框的change事件，用户更换输入文件时触发
const handleFileChange= (event)=>{
  const file=event.target.files[0] //获取文件输入框中的第一个文件
  if(file){ //判断用户是否真的选中了文件（防止用户打开文件选择框后点击取消，导致file为undefined，于是报错）
    selectedFile.value=file //更新响应式变量，存储用户通过文件输入框选择的本地文件对象
    uploadStatus.value='' //清空旧的状态提示
    uploadFile() //用户选中文件后直接触发uploadFile函数
  }
  else{ //否则就清空状态提示
    uploadStatus.value=""
  }
}

//定义事件处理函数，监听数据格式下拉菜单的change事件，用户改变选项时触发
const handleFormatChange= ()=>{
  if(selectedFile.value){ //判断用户是否已经选中了输入文件，如果是，那么说明用户想用新格式重新解析这个文件；如果不是，那么不需要任何操作
    console.log("格式已变更，正在重新校验文件...") //在控制台打印日志
    uploadFile() //此时需要重新触发uploadFile函数
  }
}

//渲染散点图
const renderChart= (plot_data)=>{
  if(!chartRef.value || !plot_data) return //防御性检查：确保DOM元素存在，且有数据
  const myChart=echarts.init(chartRef.value) //初始化echarts实例，绑定到对应div上

  const seriesData=[] //初始化一个数组，用来存放散点图中每个点的信息
  const clusters=[...new Set(   plot_data.map(item=>item.cluster)   )]   .sort() //plot_data.map(item=>item.cluster)表示遍历plot_data数组，把每一项的cluster字段拿出来，组成一个新数组；然后我们把这个数组传给new出来的一个Set对象，于是存储在里面的数据没有重复值，实现去重；[... ]是扩展运算符，可以把Set对象里的数据一个个展开，放入一个新数组中；最后.sort()对数组元素进行默认升序排序
  clusters.forEach(clusterId=>{ //遍历clusters数组，对数组中的每一个元素，它都会执行一次箭头函数clusterId=>{}内部的代码块
    const clusterPoints=plot_data.filter(item=>item.cluster===clusterId) //遍历plot_data数组，筛选出cluster字段的值等于clusterId的所有项，并将它们组成一个新数组返回
    seriesData.push({ //把下面这个对象push到seriesData数组的末尾
      name: `Cluster ${clusterId}`, //表示该点被分到哪个cluster里了
      type: 'scatter', //图表类型：散点图
      symbolSize: 10, //点的大小
      data: clusterPoints.map(p=>[p.x,p.y,p.name]), //[后端传来的x坐标,后端传来的y坐标,后端传来的name]。不把后端传来的name放在数组的第一位是因为echarts默认规定数组的前两位必须是坐标值，否则坐标失效
      itemStyle: {
        opacity: 0.8 //设置透明度为0.8，防止点重叠时看不清
        //颜色的话就让echarts自动分配吧，echarts默认色板就很好看，所以这里不手动指定color
      }
    })
  })

  //为图表设置选项
  myChart.setOption({
    series: seriesData, //把我们刚才处理的seriesData数组传入这个图表
    tooltip: {
      trigger: 'item', //鼠标悬停在点上时触发
      formatter: function(params){ //params的值来源于echarts内部引擎，当鼠标悬停时，echarts会自动打包该点的所有信息，并作为参数传给函数
        return `<b>${params.data[2]}</b><br/>Cluster: ${params.seriesName}<br/>(x: ${params.data[0].toFixed(2)}, y: ${params.data[1].toFixed(2)})`
        //params.data是该点对应的data数组，就是上面的[后端传来的x坐标,后端传来的y坐标,后端传来的name]
        //params.seriesName是该点对应的name，就是上面的`Cluster ${clusterId}`
        //.toFixed(2)表示保留2位小数
      }
    },
    legend: { //为图例设置选项，就是散点图下方的那些东西
      bottom: '5%', //把图例组件放置在距离容器底部5%的位置
      data: clusters.map(c =>`Cluster ${c}`) //图例组件的内容
    },
    xAxis: {
      name: 'PC 1', //x轴名称
      splitLine: { show: false } //不显示网格线【【【【【以后考虑让用户自定义？
    },
    yAxis: {
      name: 'PC 2', //y轴名称
      splitLine: { show: false }
    }
  })
}

//定义事件处理函数，监听运行分析按钮的click事件，用户点击按钮时触发
const runAnalysis= async ()=>{
  if(!uploadedFilename.value){ //判断用户是否已经选中了输入文件
    alert("请先上传数据文件！")
    return
  }
  if(!selectedAlgorithm.value){ //判断用户是否已经选择了算法
    alert("请先选择一种算法！")
    return
  }

  //初始化请求状态：开启加载动画，清空旧错误信息和旧结果
  isLoading.value=true
  errorMessage.value=''
  backendResponse.value=null

  try{
    //使用axios发送POST请求到后端接口"/api/run"
    // 参数1：接口URL
    // 参数2：请求体
    const res= await axios.post('http://127.0.0.1:8000/api/run',{
      algorithm: selectedAlgorithm.value, //用户选中的算法名称
      timestamp: new Date().toISOString(), //当前时间戳，格式为ISO 8601
      filename: uploadedFilename.value, //要处理的文件名
      n_clusters: kValue.value, //用户自定义的K值
      random_state: randomSeed.value, //用户自定义的随机种子
      max_iter: maxIter.value //用户自定义的最大迭代次数
    })
    backendResponse.value=res.data //请求成功后，将后端返回的数据赋值给backendResponse。此时前端界面也会更新
    console.log('后端返回数据:',res.data) //在控制台打印日志
    if(res.data.data.plot_data){ //如果成功返回了plot_data，那么渲染散点图
        await nextTick() //暂停当前代码的执行，直到vue完成对网页界面的更新（DOM元素渲染完成），然后再继续。这是因为我们要渲染的div被包裹在这个div里：<div v-if="backendResponse" class="success-box">，所以只有backendResponse赋值完毕、要渲染成散点图的div加载完毕之后，我们才能执行下面这句代码
        renderChart(res.data.data.plot_data) //plot_data就是后端传来的存放每个样本对应的信息的那个列表
    }
  }
  catch(error){ //捕获并处理请求过程中的错误
    console.error('请求失败:', error) //在控制台打印日志
    errorMessage.value='连接后端失败，请检查 FastAPI 是否启动并配置了 CORS。' //在前端界面显示错误提示
  }
  finally{ //无论请求成功还是失败，最终都要关闭加载状态，恢复按钮可用性
    isLoading.value=false
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

          <p class="status-message" :class="{ 'error-text': uploadStatus.startsWith('❌') }"><!-- :class 动态绑定: 当 uploadStatus 以 '❌' 开头时，添加 'error-text' 类名【【【【【这是啥？ -->
            {{ uploadStatus }}
          </p>

          <div class="upload-config">
            <div class="config-item">
               <label>我的数据格式是：</label>
               <select v-model="dataFormat" @change="handleFormatChange" class="format-select"><!-- v-model: 双向绑定选择框的值到 dataFormat 变量 -->
                 <option v-for="opt in dataFormatOptions" :key="opt.value" :value="opt.value"><!-- v-for: 遍历 dataFormatOptions 数组生成选项 --><!-- :key: 列表渲染的唯一标识符 --><!-- :value: 动态绑定选项的 value 值 -->
                   {{ opt.label }}
                 </option>
               </select>
            </div>

            <div class="example-box">
                <span class="example-label">示例CSV文本：</span>
                <pre class="example-content">{{ exampleText }}</pre><!-- pre 元素: 保留文本的空格和换行格式 -->
            </div>
          </div>
        </div>

        <div class="step-section control-group">
          <h3>2. 算法选择 (Clustering Method)</h3>
          <label>选择算法：</label>
          <select v-model="selectedAlgorithm"><!-- v-model: 双向绑定选择框的值到 selectedAlgorithm 变量 -->
            <option v-for="algo in algorithms" :key="algo" :value="algo"><!-- v-for: 遍历 algorithms 数组生成选项 -->
              {{ algo }}
            </option>
          </select>

          <div v-if="selectedAlgorithm === 'K-means'" class="params-box">
            <h4>K-means 参数配置：</h4>

            <div class="param-item">
              <label>聚类簇数 (K值):</label>
              <input type="number" v-model="kValue" min="2" max="20" /><!-- v-model: 双向绑定输入值到 kValue 变量 --><!-- min/max: 限制输入范围为 2-20 -->
            </div>

            <div class="param-item">
              <label>随机种子:</label>
              <input type="number" v-model="randomSeed" /><!-- v-model: 双向绑定输入值到 randomSeed 变量 -->
            </div>

            <div class="param-item">
              <label>最大迭代:</label>
              <input type="number" v-model="maxIter" step="50" /><!-- v-model: 双向绑定输入值到 maxIter 变量 --><!-- step: 每次增减的步长为 50【【【【【这是什么意思？ -->
            </div>
          </div>
        </div>

        <div class="step-section action-area">
          <h3>3. 运行分析 (Execution)</h3>
          <button @click="runAnalysis" :disabled="isLoading" class="run-btn"><!-- :disabled: 动态绑定禁用状态，当 isLoading 为 true 时按钮禁用 -->
            <span v-if="isLoading">正在运行...</span><!-- 根据 isLoading 状态显示不同文本 -->
            <span v-else>运行分析 (Run Analysis)</span>
          </button>
        </div>

        <div v-if="backendResponse || errorMessage" class="result-area"><!-- 当后端响应成功或有错误信息时显示此区域 -->
          <h3>后端响应结果：</h3>
          <div v-if="backendResponse" class="success-box"><!-- 显示成功结果 -->
            <div v-if="backendResponse.data.metrics" class="metrics-container"><!-- 当响应数据中包含 metrics 对象时显示评估指标 -->
               <h4>📊 聚类效果评估 (Evaluation Metrics)</h4>
               <div class="metrics-grid">
                  <div class="metric-card">
                     <span class="m-label">轮廓系数 (Silhouette)</span>
                     <span class="m-value">{{ backendResponse.data.metrics.silhouette }}</span>
                  </div>
                  <div class="metric-card">
                     <span class="m-label">CH 指数 (Calinski-Harabasz)</span>
                     <span class="m-value">{{ backendResponse.data.metrics.calinski }}</span>
                  </div>
                  <div class="metric-card">
                     <span class="m-label">DB 指数 (Davies-Bouldin)</span>
                     <span class="m-value">{{ backendResponse.data.metrics.davies }}</span>
                  </div>
               </div>
            </div>

            <div ref="chartRef" class="chart-container"></div><!-- ref: 模板引用，将此 DOM 元素存储到 chartRef 变量中，用于把这个div渲染成散点图 -->

            <details><!-- details 元素: 可折叠的详情区域 -->
               <summary>查看原始 JSON 数据</summary>
               <pre>{{ backendResponse.data }}</pre>
            </details>
          </div>

          <div v-if="errorMessage" class="error-box"><!-- 显示错误信息 -->
            {{ errorMessage }}
          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<style scoped>
/* style scoped 表示这里的 CSS 样式仅应用于当前组件，不污染全局样式 */

/* 整体容器布局，设置字体、最小高度和背景色 */
.container {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  color: #333;
  min-height: 100vh;
  background-color: #f5f7fa;
}

/* 头部样式 - 模仿论文图14的简约风格 */
.header {
  background-color: #2c3e50; /* 深色背景 */
  color: white;
  padding: 0 40px;
  height: 60px;
  display: flex; /* Flexbox 布局 */
  align-items: center; /* 垂直居中 */
  justify-content: space-between; /* 两端对齐 */
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* 底部阴影 */
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

/* 导航项悬停和激活状态样式 */
.nav span:hover, .nav span.active {
  opacity: 1;
  font-weight: bold;
  border-bottom: 2px solid #42b983; /* 绿色下划线 */
}

/* 主内容区域，居中显示 */
.main-content {
  display: flex;
  justify-content: center;
  padding-top: 60px;
}

/* 分析面板卡片样式 */
.analysis-panel {
  background: white;
  width: 800px;
  padding: 40px;
  border-radius: 8px; /* 圆角 */
  box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* 柔和阴影 */
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
  border-bottom: 2px solid #42b983; /* 标题下划线装饰 */
  padding-bottom: 5px;
  display: inline-block;
}

/* 上传配置区样式 */
.upload-config {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px dashed #ddd; /* 加个虚线分割线，区分配置和文件选择 */
}

.config-item {
  margin-bottom: 15px;
  text-align: left;
}

/* 格式选择下拉框样式 */
.format-select {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: 100%; /* 下拉框占满容器宽度 */
  max-width: 400px;
  font-size: 14px;
}

/* 示例代码块容器 */
.example-box {
  background-color: #fff;
  border: 1px solid #eee;
  padding: 10px;
  border-radius: 4px;
  text-align: left;
  display: flex;
  align-items: flex-start;
}

.example-label {
  font-weight: bold;
  color: #555;
  margin-right: 10px;
  white-space: nowrap; /* 防止标签换行 */
}

/* 示例内容（pre标签）样式 */
.example-content {
  margin: 0;
  background: none; /* 去掉 pre 默认的灰色背景，融合进 box */
  padding: 0;
  font-family: Consolas, Monaco, 'Courier New', monospace; /* 等宽字体 */
  color: #2c3e50;
  font-size: 13px;
  border: none;
}

/* 上传控件布局容器 */
.upload-controls {
  display: flex; /* 弹性布局 */
  gap: 15px; /* 子控件之间的间距 */
  align-items: center; /* 垂直居中 */
}

/* 已经废弃的上传按钮样式（因为逻辑改为自动上传，所以样式保留供参考） */
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

/* 状态反馈消息样式 */
.status-message {
  margin-top: 10px;
  font-size: 14px;
  font-weight: bold;
  color: #27ae60; /* 成功状态绿色文字 */
  white-space: pre-wrap; /* 允许错误信息自动换行，防止太长溢出 */
  word-break: break-all; /* 允许在单词内换行，防止文件名过长溢出 */
}

/* 错误状态文本红色样式，使用 !important 提高优先级 */
.error-text {
  color: #e74c3c !important; /* 强制使用红色 */
}

.control-group {
  margin-bottom: 20px;
}

/* 动态参数配置区域的样式 */
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
  display: inline-block; /* 水平排列，让输入框在一行显示 */
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

/* 主要操作按钮（运行分析）样式 */
.run-btn {
  background-color: #42b983; /* Vue的主题色，也适合科研平台的清新感 */
  color: white;
  border: none;
  padding: 12px 30px;
  font-size: 18px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s; /* 背景色过渡动画 */
}

.run-btn:hover:not(:disabled) {
  background-color: #3aa876;
}

.run-btn:disabled {
  background-color: #a8d5c2; /* 禁用时的浅绿色 */
  cursor: not-allowed;
}

/* 结果显示区域样式 */
.result-area {
  margin-top: 40px;
  text-align: left;
  border-top: 1px solid #eee; /* 顶部分隔线 */
  padding-top: 20px;
}

/* 成功结果容器 */
.success-box {
  background-color: #e8f5e9; /* 浅绿背景 */
  border: 1px solid #c8e6c9;
  padding: 15px;
  border-radius: 4px;
  color: #2e7d32;
}

/* 错误结果容器 */
.error-box {
  background-color: #ffebee; /* 浅红背景 */
  border: 1px solid #ffcdd2;
  padding: 15px;
  border-radius: 4px;
  color: #c62828;
}

pre {
  background: #f1f1f1;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto; /* 内容过宽时显示滚动条 */
}

/* 指标容器布局 */
.metrics-container {
  margin-bottom: 30px;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.metrics-container h4 {
  margin-top: 0;
  color: #2c3e50;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

/* 网格布局，让三个指标横向排列 */
.metrics-grid {
  display: flex;
  justify-content: space-around; /* 平均分布 */
  margin-top: 15px;
}

/* 单个指标卡片样式 */
.metric-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #f8f9fa;
  padding: 15px 25px;
  border-radius: 6px;
  min-width: 120px;
}

.m-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.m-value {
  font-size: 20px;
  font-weight: bold;
  color: #42b983; /* 使用主题绿色 */
}

/* 图表容器样式：必须指定高度，否则 echarts 无法显示 */
.chart-container {
  width: 100%;
  height: 400px; /* 设定高度为 400px */
  background-color: #fff;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-bottom: 20px;
}
</style>