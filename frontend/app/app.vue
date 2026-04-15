<script setup>
useHead({ title: 'InferenceDeck ---面向多组学癌症分型的全栈AI分析平台' })
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
// import { ref,computed,nextTick } from 'vue' //引入Vue框架的核心函数 //ref：用于定义基本类型的响应式数据（数据变化时视图自动更新） //computed：用于定义计算属性（依赖其他数据变化而自动重新计算并缓存结果） //nextTick：用于确保DOM元素渲染完成后再执行绘图代码
import axios from 'axios' //引入 axios 库，用于在浏览器端发送 HTTP 请求，与后端服务器进行数据交互
import * as echarts from 'echarts' //引入整个echarts库，命名为echarts //为什么不这么写“import echarts from 'echarts'”？这是因为不同的库有不同的导出策略
import 'echarts-gl' // [新增] 引入 echarts-gl 用于渲染 3D 曲面图。
import * as uuid from 'uuid'

// ===================== 状态定义区 =====================

//代表当前会话的UUID
const sessionId=ref(uuid.v4())

// 【新增】标记数据状态，用于判断在点击 Run 时是否需要真正发送 Upload 请求
const isOmicsUploaded = ref(false)
const isClinicalUploaded = ref(false)

// ======================== 新增代码 ========================
// 为什么要这么写：使用 ref() 函数创建一个具有响应式特性的基本类型变量 activeTab，用于存储当前处于激活状态的导航标签名称。
// 响应式（Reactive）意味着当 activeTab 的值在 JavaScript 中发生改变时，Vue 底层会通过依赖收集机制自动追踪这一变化，并触发绑定了该变量的 DOM 结构进行重新渲染。
// 将其初始参数设置为 'Home'，以此满足“初始界面为Home界面”的需求。
const activeTab = ref('Home')
// ==========================================================

const backendResponse=ref(null) //定义响应式变量，用于存储从后端 API 接收到的 JSON 响应数据 //对应论文图3中后端返回的 "Clustering results"

const isLoading=ref(false) //定义布尔类型的响应式变量，用于控制“加载中”状态（如禁用按钮、显示Loading动画） //防止用户在分析计算过程中重复点击

const errorMessage=ref('') //定义字符串变量，用于存储请求失败时的错误描述信息，以便在前端界面显示错误提示

const selectedAlgorithm=ref([]) // 定义当前选中的算法数组，默认值为空数组

const algorithms=['K-means', 'Spectral Clustering', 'PIntMF', 'Subtype-GAN', 'NEMO', 'SNF'] //定义算法候选数组，供下拉框渲染使用 //这些算法对应论文表3和表5中提到的 "11种前沿多组学聚类算法" 及基础算法

// const selectedFiles=ref([]) //用于存储用户通过文件输入框选择的各个文件对象
// 【新增】用来存储带 UUID、原始名称和组学类型的对象数组
const omicsFileConfigs = ref([])

// 【新增】定义系统支持的组学类型选项
const omicsTypes = [ 'CopyNumber', 'Methylation', 'miRNA', 'mRNA', 'Proteomics' , 'RPPA', 'Unknown' ]

const uploadStatus=ref('') //定义字符串变量，用于向用户反馈文件上传的进度或结果（如 "上传成功" 或 错误信息）

// const uploadedFilename=ref('') //定义字符串变量，用于存储后端返回的用户上传文件的新名称 //前端在后续调用 "运行分析" 接口时，需要将此文件名传回后端，指定处理哪个文件
// 【删除】不再需要依赖后端返回的文件名，统一使用 sessionId

const chartRef=ref(null) //定义一个引用变量，用来绑定template中的图表容器div

const currentReduction=ref('PCA') //用户选择的降维算法，默认PCA

const clinicalFile=ref(null) //用户选择的临床数据文件

const clinicalUploadStatus=ref('') //临床数据文件上传状态提示

// const clinicalFilename=ref('') //后端返回的临床文件名
// 【删除】统一使用 sessionId

// *********************************************
// [新增] 自定义算法评估模式相关状态
const isCustomEvalMode = ref(false) // 是否开启自定义评估模式
const customEvalFile = ref(null) // 用户上传的自定义结果文件
const customEvalUploadStatus = ref('') // 自定义结果文件上传状态
// *********************************************

const survivalResult=ref(null) //存储后端返回的生存分析结果（P值、KM数据）

const isSurvivalLoading=ref(false) //生存分析加载状态

const survivalChartRef=ref(null) //绑定生存曲线图表的DOM元素

const resultsAreaRef=ref(null) //绑定运行分析结果区域的DOM元素，用于自动滚动定位

const survivalAreaRef=ref(null) //绑定生存分析结果区域的DOM元素，用于自动滚动定位

// *********************************************
// [新增] 差异分析相关状态
const diffResult = ref(null) // 存储后端返回的差异分析结果
const isDiffLoading = ref(false) // 差异分析加载状态
const diffAnalysisAreaRef = ref(null) // 滚动定位用
const selectedVolcanoCluster = ref(0) // 用户当前选择查看哪个簇的火山图
const volcanoChartRef = ref(null) // 火山图 DOM 引用
const heatmapChartRef = ref(null) // 热图 DOM 引用  绑定热图DOM
const diffErrorMessage = ref('') // 差异分析错误信息

// 👈 【新增】用于绑定用户选择的单一差异分析组学类型
const selectedDiffOmicsType = ref('')
// *********************************************

// *********************************************
// [修改] 富集分析相关状态
const enrichmentResult = ref(null) // 存储富集分析结果，现在它是一个包含所有簇的字典：{"0": [...], "1": [...]}
const isEnrichmentLoading = ref(false) // 富集分析加载状态
const enrichmentChartRef = ref(null) // 富集分析图表 DOM 引用
// [新增] 绑定富集分析气泡图的DOM元素，用于渲染气泡图
const enrichmentBubbleChartRef = ref(null)
const enrichmentType = ref('') // 当前展示的是 GO 还是 KEGG
const enrichmentAreaRef = ref(null) // 滚动定位用
const selectedEnrichmentCluster = ref(0) // 新增：单独用于富集分析的簇选择绑定变量
// [新增] 气泡图显示模式状态
const bubbleChartMode = ref('combined') // 定义响应式变量，默认'combined'，表示复刻 Combined_KEGG_enrichment.pdf；'by_gene' 表示复刻单簇气泡图效果并用图例控制
// *********************************************

// *********************************************
// [新增] 测试模式（参数敏感性分析）相关状态
const isTestMode = ref(false) // 布尔变量，用于控制是否开启测试模式，通过复选框双向绑定
const testNClusters = ref('2,3,4,5') // 存储用户输入的聚类簇数测试范围（逗号分隔的字符串）
const testMaxIter = ref('100,200,300') // 存储用户输入的最大迭代次数测试范围（逗号分隔的字符串）
// 【新增】谱聚类测试范围
const testNNeighbors = ref('5,10,15')

const psResult = ref(null) // 存储后端返回的敏感性分析（Parameter Search）结果数据
const isPsLoading = ref(false) // 敏感性分析的加载状态，防止用户重复点击

const psParam1 = ref('n_clusters') // 敏感性分析图中选中的 X 轴参数，默认 K 值
const psParam2 = ref('max_iter') // 敏感性分析图中选中的 Y 轴参数，默认最大迭代。如果选空或选相同则绘制 2D 图
const psChartRef = ref(null) // 绑定敏感性分析图表容器的 DOM 引用
// *********************************************

// ===================== 数据格式处理区【【【【【这几个区改一下名 =====================

// 组学数据格式的三个复选框绑定变量（默认全为true）
const omicsIsRowSample=ref(true)//true：行代表特征，列代表病人；false：行代表病人，列代表特征
const omicsHasHeader=ref(true)//true：有表头行
const omicsHasIndex=ref(true)//true：有索引列

// 临床数据格式的三个复选框绑定变量（默认全为true） //【【【【【之后改一下？
const clinicalIsRowSample=ref(false)
const clinicalHasHeader=ref(true)
const clinicalHasIndex=ref(true)

// 使用 computed 自动将复选框的布尔值拼接成后端和示例所需的字符串格式
const dataFormat=computed(()=>{
  const part1=omicsIsRowSample.value ? 'row_feature' : 'row_sample'
  const part2=omicsHasHeader.value ? 'yes' : 'no'
  const part3=omicsHasIndex.value ? 'yes' : 'no'
  return `${part1}_${part2}_${part3}`
})

const clinicalDataFormat=computed(()=>{
  const part1=clinicalIsRowSample.value ? 'row_feature' : 'row_sample'
  const part2=clinicalHasHeader.value ? 'yes' : 'no'
  const part3=clinicalHasIndex.value ? 'yes' : 'no'
  return `${part1}_${part2}_${part3}`
})

//如果用户选择的数据格式为：行代表病人，列代表特征。有表头行✅、有索引列✅。那么拼接出来的字符串是'row_sample_yes_yes'
//如果用户选择的数据格式为：行代表病人，列代表特征。有表头行✅、无索引列❌。那么拼接出来的字符串是'row_sample_yes_no'
//如果用户选择的数据格式为：行代表病人，列代表特征。无表头行❌、有索引列✅。那么拼接出来的字符串是'row_sample_no_yes'
//如果用户选择的数据格式为：行代表病人，列代表特征。无表头行❌、无索引列❌。那么拼接出来的字符串是'row_sample_no_no'
//如果用户选择的数据格式为：行代表特征，列代表病人。有表头行✅、有索引列✅。那么拼接出来的字符串是'row_feature_yes_yes'
//如果用户选择的数据格式为：行代表特征，列代表病人。有表头行✅、无索引列❌。那么拼接出来的字符串是'row_feature_yes_no'
//如果用户选择的数据格式为：行代表特征，列代表病人。无表头行❌、有索引列✅。那么拼接出来的字符串是'row_feature_no_yes'
//如果用户选择的数据格式为：行代表特征，列代表病人。无表头行❌、无索引列❌。那么拼接出来的字符串是'row_feature_no_no'

//根据用户选择的组学数据格式，使用不同的示例CSV文本
const exampleText=computed(()=>{
  switch(dataFormat.value){
    case 'row_sample_yes_yes':
      return `,特征1,特征2,特征3,...\n病人1,11,12,13\n病人2,21,22,23\n病人3,31,32,33\n...`
    case 'row_sample_yes_no':
      return `特征1,特征2,特征3,...\n11,12,13\n21,22,23\n31,32,33\n...`
    case 'row_sample_no_yes':
      return `病人1,11,12,13,...\n病人2,21,22,23\n病人3,31,32,33\n...`
    case 'row_sample_no_no':
      return `11,12,13,...\n21,22,23\n31,32,33\n...`
    case 'row_feature_yes_yes':
      return `,病人1,病人2,病人3,...\n特征1,11,21,31\n特征2,12,22,32\n特征3,13,23,33\n...`
    case 'row_feature_yes_no':
      return `病人1,病人2,病人3,...\n11,21,31\n12,22,32\n13,23,33\n...`
    case 'row_feature_no_yes':
      return `特征1,11,21,31,...\n特征2,12,22,32\n特征3,13,23,33\n...`
    case 'row_feature_no_no':
      return `11,21,31,...\n12,22,32\n13,23,33\n...`
    default:
      return ''
  }
})

//根据用户选择的临床数据格式，使用不同的示例CSV文本
const clinicalExampleText=computed(()=>{
  switch(clinicalDataFormat.value){
    case 'row_sample_yes_yes':
      return `,OS,OS.time,特征3,...\n病人1,1,20,55\n病人2,0,45,60\n病人3,1,12,62\n...`
    case 'row_sample_yes_no':
      return `OS,OS.time,特征3,...\n1,20,55\n0,45,60\n1,12,62\n...`
    case 'row_sample_no_yes':
      return `病人1,1,20,55,...\n病人2,0,45,60\n病人3,1,12,62\n...`
    case 'row_sample_no_no':
      return `1,20,55,...\n0,45,60\n1,12,62\n...`
    case 'row_feature_yes_yes':
      return `,病人1,病人2,病人3,...\nOS,1,0,1\nOS.time,20,45,12\n特征3,55,60,62\n...`
    case 'row_feature_yes_no':
      return `病人1,病人2,病人3,...\n1,0,1\n20,45,12\n55,60,62\n...`
    case 'row_feature_no_yes':
      return `OS,1,0,1,...\nOS.time,20,45,12\n特征3,55,60,62\n...`
    case 'row_feature_no_no':
      return `1,0,1,...\n20,45,12\n55,60,62\n...`
    default:
      return ''
  }
})

// ===================== 算法参数配置区 =====================

const kValue=ref(3) //定义簇的数量 (K值)，初始值3 //对应论文 2.1.2 节中提到的 "最大簇数(K值)" 或论文表2中的 K 值设定

const maxIter=ref(300) //定义最大迭代次数，初始值300，用于控制算法收敛前的最大循环数，防止死循环

// 【新增】谱聚类参数
const nNeighbors=ref(10)

const randomSeed=ref(42) //定义随机种子，初始值42 //确保算法结果的可复现性（论文 2.1.2 提到 Consensus Clustering 需要重采样，种子很重要）

// ===================== 方法定义区 =====================

// 定义清理当前会话的函数
const cleanupSession = () => {
  if (!sessionId.value) return
  
  // 使用 FormData 打包要发送的数据
  const formData = new FormData()
  formData.append('session_id', sessionId.value)
  
  // 【关键技术】使用 navigator.sendBeacon 
  // 当浏览器页面卸载、关闭或刷新时，普通的 axios/fetch 异步请求大概率会被浏览器直接取消掉。
  // sendBeacon 是专门为此场景设计的原生 API，可以确保请求在后台可靠地发送给后端。
  navigator.sendBeacon('/api/cleanup', formData)
}

// 组件挂载时，监听浏览器的关闭/刷新事件 (beforeunload)
onMounted(() => {
  window.addEventListener('beforeunload', cleanupSession)
})

// 组件正常卸载时，移除监听器并执行一次清理
onUnmounted(() => {
  window.removeEventListener('beforeunload', cleanupSession)
  cleanupSession()
})

// 【修改】仅负责执行纯粹的组学数据上传动作
const uploadFile = async () => {
  if(omicsFileConfigs.value.length === 0) return

  const formData = new FormData()
  const mapping = {} // 【新增】用于存放 UUID -> 组学类型 的映射
  for(let i=0; i<omicsFileConfigs.value.length ;i++){
    const config = omicsFileConfigs.value[i]
    // 【关键】append 的第三个参数为指定的文件名，这里我们将原始文件名替换为 UUID 传给后端
    formData.append('files', config.file, config.id)
    // formData.append('files', selectedFiles.value[i])
    mapping[config.id] = config.type // 建立映射关系
  }
  // 【新增】把映射关系转为 JSON 字符串发给后端
  formData.append('omics_mapping', JSON.stringify(mapping))
  formData.append('data_format', dataFormat.value)
  formData.append('file_type', 'omics')
  formData.append('session_id', sessionId.value) // 【新增】发给后端创建文件夹

  uploadStatus.value = "正在上传组学数据..."
  try {
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    // 👇 【修改】先拼接基础成功信息
    let statusMsg = `✅ 组学数据就绪: ${omicsFileConfigs.value.map(c => c.originalName).join(' + ')}`
    
    // 👇 【新增】提示丢失的样本，追加一行显眼的提示
    statusMsg += `\n⚠️ 提示：这些数据有 ${res.data.lost_samples} 个病人无法对齐，计算时会忽略这些病人`
    uploadStatus.value = statusMsg
    // 【修改】用 originalName 把界面的成功提示拼回去
    // uploadStatus.value = `✅ 组学数据就绪: ${omicsFileConfigs.value.map(c => c.originalName).join(' + ')}`
    // uploadStatus.value = `✅ 组学数据就绪: ${res.data.original_filename}`
    isOmicsUploaded.value = true // 【新增】标记为已上传，后续多次点击Run不再重复触发
  } catch(error) {
    console.error('上传出错:', error)
    uploadStatus.value = `❌ 数据不合规: ${error.response?.data?.detail || "上传失败"}`
    isOmicsUploaded.value = false
    throw error // 抛出异常阻断运行流程
  }
}

// //定义异步函数，处理文件上传逻辑
// const uploadFile= async ()=>{
//   if(selectedFiles.value.length===0){ //检查文件数组长度是否为0 //正常情况下，因为handleFileChange函数中有个if(files.length>0)，所以不可能触发这个if
//     alert("请至少选择一个文件！")
//     return
//   }

//   const formData=new FormData() //创建FormData对象，这是Web API中用于构建键值对集合的标准对象，可以用作请求体，是JSON格式 //专门用于通过 XMLHttpRequest 或 fetch/axios 发送 multipart/form-data 格式的数据（即文件上传）
//   for(let i=0; i<selectedFiles.value.length ;i++){ //遍历selectedFiles数组，将用户选择的所有文件追加到formData中。FormData允许一个key对应多个值，FastAPI会自动将其解析为列表
//     formData.append('files',selectedFiles.value[i]) //键名为'files'，这个键名必须和后端接口"/api/upload"对应的函数形参files名称保持一致
//   }
//   formData.append('data_format',dataFormat.value) //将用户选择的数据格式字符串也追加到表单数据中

//   try{
//     uploadStatus.value="正在上传..." //更新界面状态提示，告知用户上传正在进行
//     //使用axios发送POST请求到后端接口"/api/upload"
//     // 参数1：接口URL
//     // 参数2：请求体，就是那个formData
//     // 参数3：配置对象，显式指定Content-Type头部，确保后端能正确解析文件流
//     const res=await axios.post('/api/upload',formData,{
//       headers:{
//         'Content-Type': 'multipart/form-data' //显式指定请求头，确保后端能正确解析文件流
//       }
//     })
//     //请求成功后，后端不是会返回一个字典嘛，我们要根据这个字典修改前端
//     uploadStatus.value=`✅ 上传成功: ${res.data.original_filename} \n📊 合并后的形状: ${   res.data.original_shape ? `(行=${res.data.original_shape[0]}, 列=${res.data.original_shape[1]})` : ''   }` //更新状态提示为成功，并显示用户上传的各个文件的原始名称和合并后的形状
//     console.log('上传结果:',res.data) //在控制台打印日志
//     uploadedFilename.value=res.data.filename //将后端返回的用户上传文件的新名称保存到前端变量，下一步分析要用
//   }
//   catch(error){ //捕获并处理请求过程中的错误（如网络错误、4xx/5xx 状态码）
//     console.error('上传出错:',error) //在控制台打印日志
//     if(error.response && error.response.data && error.response.data.detail){ //如果遇到错误，后端不是会raise HTTPException嘛，我们先来判断一下后端有没有返回详细错误信息（比如那些ValueError），这通常是文件解析失败返回的信息
//       uploadStatus.value=`❌ 数据不合规: ${error.response.data.detail}`
//     }
//     else{ //不然的话就是网络连接中断or后端未启动or其他未知错误
//       uploadStatus.value="❌ 上传失败，请检查后端服务是否启动"
//     }
//     uploadedFilename.value='' //既然遇到错误了，那么就要清空文件名变量，避免后续操作使用非法文件名。顺带一提，既然遇到错误了，那么这个文件也肯定已经被后端删了
//   }
// }

// 【修改】取消自动上传，仅标记需重新上传
const handleFileChange = (event) => {
  const files = Array.from(event.target.files)
  if(files.length > 0){
    // 【修改】构建包含 UUID 的文件配置对象
    omicsFileConfigs.value = files.map(f => ({
      id: uuid.v4(), // 为每个文件生成 UUID
      file: f,
      originalName: f.name,
      type: 'Unknown' // 默认选项设为 Unknown
    }))
    // selectedFiles.value = files
    uploadStatus.value = '文件已选择，将在运行时自动上传。'
    isOmicsUploaded.value = false // 选了新文件，撤销已上传状态
  } else {
    omicsFileConfigs.value = []
    uploadStatus.value = ''
  }
}

// //定义事件处理函数，监听文件输入框的change事件，用户更换输入文件时触发
// const handleFileChange= (event)=>{
//   const files=Array.from(event.target.files) //获取文件输入框中的所有文件 //event.target.files是一个FileList对象，Array.from可以将其转换为数组
//   if(files.length>0){ //判断用户是否真的选中了文件（防止用户打开文件选择框后点击取消，导致files为undefined，于是报错）【【【【【现在files还会为undefined吗？
//     selectedFiles.value=files //存储用户通过文件输入框选择的各个文件对象
//     uploadStatus.value='' //清空旧的状态提示
//     uploadFile() //用户选择文件后直接触发uploadFile函数
//   }
//   else{ //否则就清空状态提示
//     uploadStatus.value=""
//   }
// }

// 【修改】改变格式时，标记需重新上传
const handleFormatChange = () => {
  if(omicsFileConfigs.value.length > 0){
    uploadStatus.value = '格式已变更，将在运行时重新校验数据。'
    isOmicsUploaded.value = false 
  }
}

// //定义事件处理函数，监听组学数据格式选择复选框的change事件，用户改变选项时触发【【【【【或许可以考虑把这个if换掉？
// const handleFormatChange= ()=>{
//   if(selectedFiles.value.length>0){ //判断用户是否已经选择了输入文件，如果是，那么说明用户想用新格式重新解析这个文件；如果不是，那么不需要任何操作
//     console.log("格式已变更，正在重新校验文件...") //在控制台打印日志
//     uploadFile() //此时需要重新触发uploadFile函数
//   }
// }

// [新增] 监听自定义评估结果文件变化
const handleCustomEvalFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    customEvalFile.value = file
    customEvalUploadStatus.value = '结果文件已选择，将在运行时自动提交评估。'
  } else {
    customEvalFile.value = null
    customEvalUploadStatus.value = ''
  }
}

//绘制散点图（使用echarts）
const renderChart= (plot_data)=>{
  if(!chartRef.value || !plot_data) return //防御性检查：确保DOM元素存在，且有数据
  //检查是否已存在实例，若存在则销毁
  const existingInstance=echarts.getInstanceByDom(chartRef.value)
  if(existingInstance){
    existingInstance.dispose()
  }
  const myChart=echarts.init(chartRef.value) //初始化echarts实例，绑定到对应div上

  const series=[] //用来存放散点图中每个点的配置
  const clusters=[...new Set(   plot_data.map(item=>item.cluster)   )]   .sort() //plot_data.map(item=>item.cluster)表示遍历plot_data数组，把每一项的cluster字段拿出来，组成一个新数组；然后我们把这个数组传给new出来的一个Set对象，于是存储在里面的数据没有重复值，实现去重；[... ]是扩展运算符，可以把Set对象里的数据一个个展开，放入一个新数组中；最后.sort()对数组元素进行默认升序排序
  clusters.forEach(clusterId=>{ //遍历clusters数组，对数组中的每一个元素，它都会执行一次箭头函数clusterId=>{}内部的代码块
    const clusterPoints=plot_data.filter(item=>item.cluster===clusterId) //遍历plot_data数组，筛选出cluster字段的值等于clusterId的所有项，并将它们组成一个新数组返回
    series.push({ //把下面这个对象push到series数组的末尾
      name: `Cluster ${clusterId}`, //该点的名称，表示该点被分到哪个cluster里了，用于图例显示
      type: 'scatter', //选择类型为散点图
      symbolSize: 10, //点的大小
      data: clusterPoints.map(p=>[p.x,p.y,p.name]), //[后端传来的x坐标,后端传来的y坐标,后端传来的name]。不把后端传来的name放在数组的第一位是因为echarts默认规定数组的前两位必须是坐标值，否则坐标失效
      itemStyle: {
        opacity: 0.8 //设置透明度为0.8，防止点重叠时看不清
        //颜色的话就让echarts自动分配吧，echarts默认色板就很好看，所以这里不手动指定color
      }
    })
  })

  let axisPrefix //根据不同降维算法，选用不同名称，用于后续拼接成'PC 1'、'PC 2'这样的x轴名称和y轴名称
  switch(currentReduction.value){
    case 'PCA':
      axisPrefix='PC' //如果降维算法是PCA，那么选用'PC'，而不是'PCA'
      break
    case 't-SNE':
      axisPrefix='t-SNE'
      break
    case 'UMAP':
      axisPrefix='UMAP'
      break
    default:
      axisPrefix='Dim' //兜底使用'Dim'
  }
  //为图表设置选项
  myChart.setOption({
    series: series, //把我们刚才处理的series数组传入这个图表
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
      name: `${axisPrefix} 1`, //x轴名称，比如'PC 1'
      splitLine: { show: false } //不显示网格线
    },
    yAxis: {
      name: `${axisPrefix} 2`, //y轴名称
      splitLine: { show: false } //不显示网格线
    }
  })
}

// 【修改】整合自定义评估模式的运行逻辑
const runAnalysis = async () => {
  // ================= 模式 A: 自定义结果评估 =================
  if (isCustomEvalMode.value) {
    if (!customEvalFile.value) {
      alert("请先选择结果数据文件！")
      return
    }

    isLoading.value = true
    errorMessage.value = ''
    backendResponse.value = null

    try {
      // 核心拦截：如果用户配置了组学/临床数据但还没上传，顺带上传一下，确保后端的交集校验能拿到最新数据
      if (omicsFileConfigs.value.length > 0 && !isOmicsUploaded.value) await uploadFile()
      if (clinicalFile.value && !isClinicalUploaded.value) await uploadClinicalFile()

      const formData = new FormData()
      formData.append('file', customEvalFile.value)
      formData.append('session_id', sessionId.value)
      formData.append('reduction', currentReduction.value)
      formData.append('random_state', randomSeed.value)

      // 第一步：解析自定义结果文件
      await axios.post('/api/evaluate_custom', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      // 第二步：计算指标 + 降维可视化
      const res = await axios.post('/api/analysis', {
        session_id: sessionId.value,
        reduction: currentReduction.value,
        random_state: randomSeed.value,
      })

      backendResponse.value = res.data
      await nextTick()
      if (res.data.data.plot_data) {
        renderChart(res.data.data.plot_data)
      }
    } catch(error) {
      errorMessage.value = error.response?.data?.detail || '评估失败，请检查数据。'
    } finally {
      isLoading.value = false
      if (resultsAreaRef.value) {
        resultsAreaRef.value.scrollIntoView({ behavior:'smooth', block:'start' })
      }
    }
    return // 自定义评估完成，直接返回
  }

  // ================= 模式 B: 系统内置算法 =================
  if (omicsFileConfigs.value.length === 0) {
    alert("请先选择组学数据文件！")
    return
  }
  if (selectedAlgorithm.value.length === 0) { 
    alert("请先选择至少一种算法！")
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  backendResponse.value = null

  try {
    // 核心变动：如果数据被篡改过或者还没上传，先拦截执行上传
    if (!isOmicsUploaded.value) {
      await uploadFile() 
    }

    // 第一步：运行聚类算法
    await axios.post('/api/run', {
      algorithm: selectedAlgorithm.value[0],
      timestamp: new Date().toISOString(),
      session_id: sessionId.value,
      n_clusters: kValue.value,
      random_state: randomSeed.value,
      max_iter: maxIter.value,
      n_neighbors: nNeighbors.value,
    })

    // 第二步：计算指标 + 降维可视化
    const res = await axios.post('/api/analysis', {
      session_id: sessionId.value,
      reduction: currentReduction.value,
      random_state: randomSeed.value,
    })

    backendResponse.value = res.data
    await nextTick()
    if (res.data.data.plot_data) {
      renderChart(res.data.data.plot_data)
    }
  } catch(error) {
    errorMessage.value = error.response?.data?.detail || '连接后端失败或上传出错。'
  } finally {
    isLoading.value = false
    if (resultsAreaRef.value) {
      resultsAreaRef.value.scrollIntoView({ behavior:'smooth', block:'start' }) 
    }
  }
}

// //定义事件处理函数，监听运行分析按钮的click事件，用户点击按钮时触发
// const runAnalysis= async ()=>{
//   if(!uploadedFilename.value){ //判断用户是否已经选中了输入文件
//     alert("请先上传数据文件！")
//     return
//   }
// // ======================== 修改代码 ========================
//   // 为什么要这么写：判断 selectedAlgorithm 数组的 length 属性是否为 0，以此校验用户是否勾选了复选框。
//   if(selectedAlgorithm.value.length === 0){ 
//     alert("请先选择至少一种算法！")
//     return
//   }
//   // 为什么要这么写：判断 selectedAlgorithm 数组的 length 属性是否大于 1，实现业务需求中的“暂时不能多选”拦截机制，阻止函数继续执行并弹出提示。
//   if(selectedAlgorithm.value.length > 1){
//     alert("暂时不能多选算法，请只选择一种！")
//     return
//   }

//   //初始化请求状态：开启加载动画，清空旧错误信息和旧结果
//   isLoading.value=true
//   errorMessage.value=''
//   backendResponse.value=null

//   try{
//     //使用axios发送POST请求到后端接口"/api/run"
//     // 参数1：接口URL
//     // 参数2：请求体
//     const res= await axios.post('/api/run',{
//       algorithm: selectedAlgorithm.value[0], //用户选中的算法名称 // 为什么要这么写：由于上方逻辑已经确保了数组长度必然为 1，通过索引 [0] 获取数组中唯一的字符串元素，以匹配后端 pydantic 模型 AnalysisRequest 中 algorithm 为 str 类型的要求。
//       timestamp: new Date().toISOString(), //当前时间戳，格式为ISO 8601
//       filename: uploadedFilename.value, //要处理的文件名
//       n_clusters: kValue.value, //用户自定义的K值
//       random_state: randomSeed.value, //用户自定义的随机种子
//       max_iter: maxIter.value, //用户自定义的最大迭代次数
//       n_neighbors: nNeighbors.value, // 【新增】传入谱聚类所需的参数
//       reduction: currentReduction.value //用户选择的降维算法
//     })
//     backendResponse.value=res.data //请求成功后，将后端返回的数据赋值给backendResponse。此时前端界面也会更新
//     console.log('后端返回数据:',res.data) //在控制台打印日志
//     await nextTick() //暂停当前代码的执行，直到vue完成对网页界面的更新（DOM元素渲染完成），然后再继续。这是因为我们要渲染的div被包裹在这个div里：<div v-if="backendResponse" class="success-box">，所以只有backendResponse赋值完毕、要渲染成散点图的div加载完毕之后，我们才能执行下面这句代码
//     if(res.data.data.plot_data){ //如果成功返回了plot_data，那么绘制散点图
//       renderChart(res.data.data.plot_data) //plot_data就是后端传来的存放每个样本对应的信息的那个列表
//     }
//   }
//   catch(error){ //捕获并处理请求过程中的错误
//     console.error('请求失败:',error) //在控制台打印日志
//     errorMessage.value='连接后端失败，请检查 FastAPI 是否启动并配置了 CORS。' //在前端界面显示错误提示
//   }
//   finally{ //无论请求成功还是失败，最终都要关闭加载状态，恢复按钮可用性；并且自动滚动到运行分析结果区域
//     isLoading.value=false
//     if(resultsAreaRef.value){ //防御性检查：确保DOM元素存在
//       resultsAreaRef.value.scrollIntoView({ behavior:'smooth',block:'start' }) //'smooth'表示平滑滚动效果，不是瞬间跳转；'start'表示将目标元素的顶部对齐到可视区域的顶部
//     }
//   }
// }

////定义事件处理函数，监听PCA/t-SNE/UMAP按钮的click事件，用户点击按钮时触发
//const switchReduction= (method)=>{
//  if(currentReduction.value===method) return //如果用户点击的是当前已经选中的降维算法，则不进行任何操作
//  currentReduction.value=method //更新用户选择的降维算法
//  runAnalysis() //直接重新运行分析
//}

const switchReduction = async (method) => {
  if (currentReduction.value === method) return
  currentReduction.value = method

  // 切换降维只需重新调 /api/analysis，不用重跑聚类
  isLoading.value = true
  try {
    const res = await axios.post('/api/analysis', {
      session_id: sessionId.value,
      reduction: currentReduction.value,
      random_state: randomSeed.value,
    })
    backendResponse.value = res.data
    await nextTick()
    if (res.data.data.plot_data) {
      renderChart(res.data.data.plot_data)
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '降维切换失败。'
  } finally {
    isLoading.value = false
  }
}

// 【修改】临床数据的上传与监听
const uploadClinicalFile = async () => {
  if(!clinicalFile.value) return

  const formData = new FormData()
  formData.append('files', clinicalFile.value)
  formData.append('data_format', clinicalDataFormat.value)
  formData.append('file_type', 'clinical')
  formData.append('session_id', sessionId.value) // 【新增】同属于一个Session

  clinicalUploadStatus.value = "正在上传临床数据..."
  try {
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    clinicalUploadStatus.value = `✅ 临床数据就绪: ${res.data.original_filename}`
    isClinicalUploaded.value = true
  } catch(error) {
    clinicalUploadStatus.value = `❌ 错误: ${error.response?.data?.detail || "上传失败"}`
    isClinicalUploaded.value = false
    throw error
  }
}

const handleClinicalFileChange = (event) => {
  const file = event.target.files[0]
  if(file){
    clinicalFile.value = file
    clinicalUploadStatus.value = '文件已选择，将在运行时自动上传。'
    isClinicalUploaded.value = false // 撤销已上传状态
  }
}

const handleClinicalFormatChange = () => {
  if(clinicalFile.value){
    clinicalUploadStatus.value = '临床格式已变更，将在运行时重新解析。'
    isClinicalUploaded.value = false
  }
}

// //临床数据上传函数
// const uploadClinicalFile= async ()=>{
//   if(!clinicalFile.value) return

//   const formData=new FormData()
//   formData.append('files',clinicalFile.value)
//   formData.append('data_format',clinicalDataFormat.value) //加入用户选择的临床数据格式
//   formData.append('file_type','clinical') //告诉后端这是临床数据，不要检查纯数字

//   try{
//     clinicalUploadStatus.value="正在上传临床数据..."
//     const res=await axios.post('/api/upload',formData,{
//       headers:{
//         'Content-Type': 'multipart/form-data'
//       }
//     })
//     clinicalUploadStatus.value=`✅ 上传成功: ${res.data.original_filename}`
//     clinicalFilename.value=res.data.filename // 保存后端返回的临时文件名
//   }
//   catch(error){
//     console.error('上传失败:', error)
//     if(error.response?.data?.detail){
//       clinicalUploadStatus.value=`❌ 错误: ${error.response.data.detail}`
//     }
//     else{
//       clinicalUploadStatus.value="❌ 上传失败"
//     }
//     clinicalFilename.value=''
//   }
// }

// //监听临床文件选择
// const handleClinicalFileChange= (event)=>{
//   const file=event.target.files[0]
//   if(file){
//     clinicalFile.value=file
//     uploadClinicalFile() //选完文件自动上传
//   }
// }

// //定义事件处理函数，监听临床数据格式选择复选框的change事件，用户改变选项时触发【【【【【或许可以考虑把这个if换掉？
// const handleClinicalFormatChange= ()=>{
//   if(clinicalFile.value){ //判断用户是否已经选中了输入文件，如果是，那么说明用户想用新格式重新解析这个文件；如果不是，那么不需要任何操作
//     console.log("临床数据格式已变更，正在重新解析...")
//     uploadFile() //此时需要重新触发uploadFile函数
//   }
// }

const runSurvivalAnalysis = async () => {
  if(!clinicalFile.value){
    alert("请先选择临床数据！")
    return
  }
  if(!backendResponse.value || !backendResponse.value.data.plot_data){
    alert("请先运行聚类分析！")
    return
  }

  isSurvivalLoading.value = true
  try {
    // 【拦截上传】
    if(!isClinicalUploaded.value) {
      await uploadClinicalFile()
    }

    const plotData = backendResponse.value.data.plot_data
    const sampleNames = plotData.map(item => item.name)
    const clusterLabels = plotData.map(item => item.cluster)

    const res = await axios.post('/api/survival_analysis',{
      session_id: sessionId.value, // 【修改】
      sample: sampleNames,
      labels: clusterLabels
    })

    survivalResult.value = res.data
    await nextTick()
    renderSurvivalChart(res.data.km_data)
    if(survivalAreaRef.value){ 
      survivalAreaRef.value.scrollIntoView({ behavior:'smooth', block:'start' })
    }
  } catch(error) {
    alert("生存分析失败: " + (error.response?.data?.detail || error.message))
  } finally {
    isSurvivalLoading.value = false
  }
}

// //生存分析运行函数
// const runSurvivalAnalysis= async ()=>{
//   if(!clinicalFilename.value){
//     alert("请先上传包含 OS 和 OS.time 的临床数据！")
//     return
//   }
//   // 确保之前的聚类分析已经跑完了，有结果了
//   if(!backendResponse.value || !backendResponse.value.data.plot_data){
//     alert("请先运行聚类分析！")
//     return
//   }

//   isSurvivalLoading.value = true
//   try{
//     // 从之前的聚类结果中提取样本名和标签
//     // plot_data 里的每一项都有 { name: "Sample1", cluster: 0, ... }
//     const plotData = backendResponse.value.data.plot_data
//     const sampleNames = plotData.map(item => item.name)
//     const clusterLabels = plotData.map(item => item.cluster)

//     // 发送请求给后端
//     const res=await axios.post('/api/survival_analysis',{
//       clinical_filename: clinicalFilename.value,
//       sample: sampleNames,
//       labels: clusterLabels
//     })

//     survivalResult.value=res.data

//     // 等待 DOM 更新后绘制 KM 曲线
//     await nextTick()
//     renderSurvivalChart(res.data.km_data)
//     //自动滚动到运行分析结果区域
//     if(survivalAreaRef.value){ //防御性检查：确保DOM元素存在
//       survivalAreaRef.value.scrollIntoView({ behavior:'smooth',block:'start' })
//     }
//   }
//   catch(error){
//     console.error("生存分析失败:", error)
//     alert("生存分析失败: " + (error.response?.data?.detail || str(error)))
//   }
//   finally{
//     isSurvivalLoading.value=false
//   }
// }

//绘制生存曲线（也使用echarts）
const renderSurvivalChart= (kmData)=>{
  if(!survivalChartRef.value) return //防御性检查
  //检查是否已存在实例，若存在则销毁
  const existingInstance=echarts.getInstanceByDom(survivalChartRef.value)
  if(existingInstance){
    existingInstance.dispose()
  }
  const myChart=echarts.init(survivalChartRef.value) //初始化echarts实例，绑定到对应div上
  const colorPalette=['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf'] //定义一套Plotly风格的默认色板 //这里的话就不推荐让echarts自动分配颜色了，因为我感觉不好看（），所以我们来定义一个色板，手动指定color

  const series=[] //用来存放生存曲线和删失点的配置
  kmData.forEach((group,index)=>{ //遍历后端返回的每一组数据。index是当前循环的索引（比如0、1、2）
    const groupColor=colorPalette[index % colorPalette.length] //设置当前组的颜色（循环使用我们上面定义的色板）
    //生存曲线的配置
    series.push({
      name: group.name, //该生存曲线的名称，用于图例显示
      type: 'line', //选择类型为线图
      step: 'end', //设置为阶梯状曲线
      data: group.times.map((t,i)=>[t,group.probs[i]]), //[后端传来的时间轴,后端传来的生存概率]
      symbol: 'circle', //数据点的形状：实心圆
      symbolSize: 10, //数据点的大小
      showSymbol: true, //显示数据点。之后我们会实现平时数据点透明度为0，高亮时为1
      itemStyle: {
        color: groupColor, //数据点和图例的颜色
        opacity: 0 //平时数据点透明度为0
      },
      emphasis: { //高亮时的样式
        itemStyle: { //高亮时数据点的样式（不包括图例，图例还是使用默认样式）
          opacity: 1 //高亮时数据点透明度为1
        }
      },
      lineStyle: {
        width: 2, //生存曲线的线条宽度
        color: groupColor //生存曲线的线条颜色
      }
    })
    //删失点的配置
    const censoredData=[] //用来存放后端传来的删失点的坐标
    if(group.censored_times){
      group.censored_times.forEach((t,i)=>{
        censoredData.push([t,group.censored_probs[i]]) //[删失点的OS.time,删失点对应的生存概率]
      })
    }
    if(censoredData.length>0){ //如果存在删失点
      series.push({
        name: group.name, //使用与生存曲线相同的名称。于是点击图例时，生存曲线和删失点会同时显示/隐藏
        type: 'scatter', //选择类型为散点图
        data: censoredData, //把我们刚才处理的censoredData数组传入这个图表
        symbol: 'rect', //删失点的形状：矩形
        symbolSize: [1,6], //设置矩形宽1像素，高6像素。于是看起来就像一条短竖线
        itemStyle: {
          color: groupColor, //删失点的颜色
          opacity: 0.7 //删失点的透明度
        },
        cursor: 'default', //这样就能鼠标悬停时不显示手指图标，避免用户误以为可以点击
      })
    }
  })

  //为图表设置选项
  myChart.setOption({
    series: series, //把我们刚才处理的series数组传入这个图表
    tooltip: { //鼠标悬停提示框配置
      trigger: 'item', //鼠标悬停在数据点上时触发
      triggerOn: 'none', //不使用echarts自带的鼠标触发机制。之后我们会写个函数控制何时显示提示框
      formatter: function(params){
        return `${params.seriesName}<br/>Time: ${params.value[0]}<br/>Probability: ${params.value[1].toFixed(4)}` //params.value[0]是该数据点对应的时间轴；params.value[1]是该数据点对应的生存概率
      }
    },
    legend: { //图例配置
      orient: 'horizontal', //图例水平排列
      // type: 'scroll', //当图例过多超出宽度时，显示滚动箭头（如果图例超过14个再考虑开启这个）【【【【【我希望图例最多能显示两行，超过两行时再开启这个，并且开启这个时图例仍能最多显示两行
      bottom: '0%' //图例放在底部
    },
    xAxis: { //x轴配置
      type: 'value', //类型：数值轴
      name: 'Time (OS.time)', //x轴名称
      nameLocation: 'middle', //居中显示x轴名称
      nameGap: 30, //x轴名称与轴线的距离
      min: 0, //x轴最小值。这样就能让x轴从0开始
      splitLine: { show: false } //不显示垂直网格线
    },
    yAxis: { //y轴配置
      type: 'value',
      name: 'Survival Probability (OS)', //y轴名称
      nameLocation: 'middle',
      nameGap: 30,
      min: 0, //y轴最小值
      max: 1, //y轴最大值
      splitLine: { show: false } //不显示水平网格线
    }
  })

  //寻找并记录距离鼠标最近的那个数据点的信息
  myChart.getZr().on('mousemove',function(params){ //获取ZRender实例并监听整个画布的mousemove事件，这样就能拿到鼠标在画布上的像素坐标
    const pointInPixel=[params.offsetX,params.offsetY] //拿到鼠标在画布上的像素坐标
    let minDistance=Infinity //初始化最小距离为无穷大
    let nearestItem=null //存放距离鼠标最近的那个数据点的信息
    series.forEach((s,sIdx)=>{ //遍历生存曲线上的每一个数据点，以及每一个删失点
      if(s.type==='scatter') return //如果遍历到删失点，那么跳过 //这里不能用continue，只能用return。在.forEach中，return相当于普通循环中的continue
      s.data.forEach((d,dIdx)=>{
        const point=myChart.convertToPixel({ seriesIndex:sIdx },d) //使用convertToPixel（echarts提供的API），将[时间轴,生存概率]转换为屏幕上的物理像素坐标[px,py]
        if(point){
          //计算鼠标与该数据点之间的距离
          const dx=point[0]-pointInPixel[0]
          const dy=point[1]-pointInPixel[1]
          const distanceSquared=dx*dx+dy*dy //不需要开根号，因为这里只需要用到比大小，开不开根号结果一样
          if(distanceSquared<minDistance){ //如果距离比之前记录的最小距离还小
            minDistance=distanceSquared //更新最小距离
            nearestItem={
              seriesIndex: sIdx, //该数据点属于哪个系列 //你就先理解成“该数据点属于哪个簇”吧。实际上，series[0]、series[1]是Cluster 0的曲线、删失点；series[2]、series[3]是Cluster 1的曲线、删失点。这个series的0、1、2、3就是不同的系列
              dataIndex: dIdx, //该数据点是系列中的第几个数据
              distance: Math.sqrt(distanceSquared) //计算并存储鼠标与该数据点之间的真实距离
            }
          }
        }
      })
    })
    //于是我们就找到距离鼠标最近的那个数据点了。然后我们来做个判断，如果鼠标与该数据点之间的距离<100，那么高亮该数据点，并显示鼠标悬停提示框
    if(nearestItem && nearestItem.distance<100){
      myChart.dispatchAction({ type: 'downplay' }) //首先取消所有点的高亮状态，防止多个点同时高亮
      myChart.dispatchAction({
        type: 'highlight', //高亮该数据点
        seriesIndex: nearestItem.seriesIndex,
        dataIndex: nearestItem.dataIndex
      })
      myChart.dispatchAction({
        type: 'showTip', //显示鼠标悬停提示框
        seriesIndex: nearestItem.seriesIndex,
        dataIndex: nearestItem.dataIndex
      })
    }
    else{ //否则就说明鼠标离所有数据点都很远
      myChart.dispatchAction({ type: 'downplay' }) //首先取消所有点的高亮状态
      myChart.dispatchAction({ type: 'hideTip' }) //隐藏鼠标悬停提示框
    }
  })
}

//计算当前用户上传并设置了哪些组学类型，用于渲染下拉框
const uploadedOmicsTypes = computed(() => {
  if (!omicsFileConfigs.value || omicsFileConfigs.value.length === 0) return []
  // 提取用户在UI上给各个文件选的类型，并去重
  const types = [...new Set(omicsFileConfigs.value.map(c => c.type))]
  
  // 如果包含了多种组学，那么多增加一个“全部拼接”的选项，并使用 push 把它放在数组最后面
  if (types.length > 1) {
    types.push('All (Concatenated)')
  }
  return types
})

//运行差异分析【【【【【待修改
const runDifferentialAnalysis= async ()=>{
  // if(!uploadedFilename.value || !backendResponse.value?.data?.plot_data){
  //   alert("请先完成 [2. 算法选择] 和 [3. 运行分析] 得到聚类结果！")
  //   return
  // }
  // 修改这里：直接检查 selectedFiles 是否为空，或者聚类结果是否存在即可
  if(omicsFileConfigs.value.length === 0 || !backendResponse.value?.data?.plot_data){
    alert("请先完成 [2. 算法选择] 和 [3. 运行分析] 得到聚类结果！")
    return
  }

  // 👈 【新增】确保用户选了具体的组学类型
  if(!selectedDiffOmicsType.value) {
    // 自动赋一个默认值（取第一个可用的组学）
    if(uploadedOmicsTypes.value.length > 0) {
      selectedDiffOmicsType.value = uploadedOmicsTypes.value[0]
    } else {
      alert("无可用的组学数据类型！")
      return
    }
  }

  isDiffLoading.value=true
  diffErrorMessage.value=''
  diffResult.value=null //清空旧结果

  try{
    //从聚类结果中提取样本名和标签
    const plotData=backendResponse.value.data.plot_data
    const sampleNames=plotData.map(item=>item.name)
    const clusterLabels=plotData.map(item=>item.cluster)

    const res=await axios.post('/api/differential_analysis',{
      session_id: sessionId.value, // 【修改】
      omics_type: selectedDiffOmicsType.value, // 👈 【新增】把用户选择的组学名发给后端
      // omics_filename: uploadedFilename.value, // 使用之前上传的组学文件
      sample: sampleNames,
      labels: clusterLabels
    })

    diffResult.value=res.data
    //默认选中第一个存在的簇进行火山图展示
    const clusters=Object.keys(res.data.volcano_data).map(Number)
    if(clusters.length>0) selectedVolcanoCluster.value = clusters[0]

    await nextTick() //等待 DOM 出现
    
    //绘制火山图
    renderVolcanoPlot()
    //绘制热图
    renderHeatmapPlot(res.data.heatmap_data)

    //自动滚动到差异分析结果区域
    if(diffAnalysisAreaRef.value){
      diffAnalysisAreaRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
  catch(error){
    console.error("差异分析失败:", error)
    diffErrorMessage.value="分析失败: " + (error.response?.data?.detail || error.message)
  }
  finally{
    isDiffLoading.value=false
  }
}

//监听火山图下拉框变化，重新绘制火山图【【【【【待修改
const handleVolcanoClusterChange= ()=>{
  renderVolcanoPlot()
}

//绘制火山图【【【【【待修改
const renderVolcanoPlot= ()=>{
  if(!volcanoChartRef.value || !diffResult.value) return

  //获取当前选中簇的数据
  const clusterId=selectedVolcanoCluster.value
  const data=diffResult.value.volcano_data[clusterId]
  if(!data) return

  const myChart=echarts.init(volcanoChartRef.value)

  // 区分显著和不显著的点，用于着色
  // 阈值：P < 0.05 (-log10P > 1.3), |LogFC| > 0.5
  const significantUp=[]   // 上调显著 (红)
  const significantDown=[] // 下调显著 (蓝)
  const notSignificant=[]  // 不显著 (灰)

  data.forEach(item =>{
    // item: {gene, logFC, t_pvalue, negLog10P}
    // ECharts scatter data: [x, y, geneName]
    const point = [item.logFC, item.negLog10P, item.gene]
    
    if(item.t_pvalue<0.05 && item.logFC>0.5){
      significantUp.push(point)
    }
    else if(item.t_pvalue<0.05 && item.logFC<-0.5){
      significantDown.push(point)
    }
    else{
      notSignificant.push(point)
    }
  })

  myChart.setOption({
    title: { 
      text: `Cluster ${clusterId} vs Others`, 
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params)=>{
        return `<b>${params.data[2]}</b><br/>LogFC: ${params.data[0].toFixed(3)}<br/>-Log10(P): ${params.data[1].toFixed(3)}`
      }
    },
    xAxis: { name: 'Log2 Fold Change', nameLocation: 'middle', nameGap: 25 },
    yAxis: { name: '-Log10(P-value)', nameLocation: 'middle', nameGap: 30 },
    series: [
      {
        name: 'Up-regulated',
        type: 'scatter',
        symbolSize: 6,
        itemStyle: { color: '#FF4757', opacity: 0.8 }, // 红色
        data: significantUp
      },
      {
        name: 'Down-regulated',
        type: 'scatter',
        symbolSize: 6,
        itemStyle: { color: '#1E90FF', opacity: 0.8 }, // 蓝色
        data: significantDown
      },
      {
        name: 'Not Significant',
        type: 'scatter',
        symbolSize: 4,
        itemStyle: { color: '#d1d5db', opacity: 0.5 }, // 灰色
        data: notSignificant
      }
    ]
  })
}

//绘制差异基因热图【【【【【待修改
const renderHeatmapPlot= (heatmapData)=>{
  if(!heatmapChartRef.value) return

  const myChart = echarts.init(heatmapChartRef.value)
  myChart.dispose() // 销毁旧实例，防止缓存干扰
  const newChart = echarts.init(heatmapChartRef.value)

  const samples = heatmapData.samples       // X轴: 样本名 (已排序)
  const genes = heatmapData.genes           // Y轴: 基因名
  const rawData = heatmapData.values        // 数据: [sample_idx, gene_idx, value]
  const labels = heatmapData.sample_labels  // 样本对应的簇标签 (用于顶部注释条)

  // 1. 计算簇的边界，用于画分割线 (MarkLine)
  const markLines = []
  let currentLabel = labels[0]

  // 遍历寻找标签变化的位置
  for (let i = 1; i < labels.length; i++) {
    if (labels[i] !== currentLabel) {
      // 在 i-0.5 的位置画线（即两个格子中间）
      markLines.push({ xAxis: i - 0.5 }) 
      currentLabel = labels[i]
    }
  }

  // 2. 准备顶部注释条的数据
  // ECharts 热图数据格式: [x, y, value]
  // 这里 y 只有一行 (0)
  const clusterBarData = labels.map((label, index) => {
    return [index, 0, label]
  })

  // 3. 配置项
  const option = {
    // 使用两个 Grid：Grid 0 是顶部的簇分类条，Grid 1 是主热图
    grid: [
      {
        id: 'top_bar',   // 顶部注释条
        height: '20px',  // 分类条高度
        top: '50px',     // 距离顶部距离
        left: '25%',     // 左边距 (给基因名留空间) //为了注释条、图片、分隔线对齐，这里要大一点给基因名留空间
        right: '5%'
      },
      {
        id: 'main_map',  // 主热图
        top: '75px',     // 主热图紧贴分类条下方 (50px + 20px + 5px间隙)// 紧贴顶部条 (60 + 20 + 5px间隙)
        bottom: '50px',
        left: '25%', //为了对齐，必须和上面一样
        right: '5%'
      }
    ],
    tooltip: {
      position: 'top',
      formatter: (params) => {
        // 自定义提示内容
        if (params.seriesIndex === 0) { // 鼠标在分类条上
          return `Sample: <b>${samples[params.data[0]]}</b><br/>Cluster: ${params.data[2]}`
        }
        else { // 鼠标在热图上
          const sampleName = samples[params.data[0]]
          const geneName = genes[params.data[1]]
          const val = params.data[2].toFixed(3)
          return `Gene: <b>${geneName}</b><br/>Sample: ${sampleName}<br/>Z-Score: ${val}`
        }
      }
    },
    // 定义两个 X 轴 (对应两个 Grid)
    xAxis: [
      { // Top Axis (分类条)
        type: 'category',
        data: samples,
        gridIndex: 0,
        axisLabel: { show: false }, // 不显示文字，太挤了
        axisTick: { show: false },
        axisLine: { show: false },
        splitLine: { show: false } // 只要色块，不要线
      },
      { // Bottom Axis (主热图)
        type: 'category',
        data: samples,
        gridIndex: 1,
        axisLabel: { show: false }, // 样本太多通常不显示名，靠Tooltip
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    // 定义两个 Y 轴
    yAxis: [
      { // Top Axis (分类条标签)
        type: 'category',
        data: ['Cluster'], // 显示 "Cluster" 字样
        gridIndex: 0,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontWeight: 'bold' }
      },
      { // Bottom Axis (基因名)
        type: 'category',
        data: genes,
        gridIndex: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { 
          fontSize: 10,
          interval: 0 // 强制显示所有基因名
        }, 
        splitLine: { show: false }
      }
    ],
    // 两个 VisualMap (图例映射)
    visualMap: [
      { // 1. 针对分类条 (离散型)
        type: 'piecewise', // 分段型图例
        seriesIndex: 0,    // 绑定到第一个系列 (Cluster Bar)
        categories: [...new Set(labels)].sort(), // 获取所有簇ID
        orient: 'horizontal',
        top: 0,
        right: 10,
        dimension: 2, // 使用数据中的第3列(index=2)作为映射依据
        inRange: {
          color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'] // ECharts 经典配色
        },
        text: ['Cluster ID'], // 图例标题
        itemWidth: 15,
        itemHeight: 15
      },
      { // 2. 针对主热图 (连续型)
        type: 'continuous',
        seriesIndex: 1,   // 绑定到第二个系列 (Main Heatmap)
        min: -2,          // Z-score 范围通常在 -2 到 2 之间好看
        max: 2,
        calculable: true, // 显示拖拽手柄
        orient: 'horizontal',
        top: 0,
        left: 'center',
        inRange: {
          // 经典的蓝-白-红配色 (Blue=Low, White=Zero, Red=High)
          color: ['#313695', '#4575b4', '#e0f3f8', '#fee090', '#f46d43', '#a50026']
        },
        text: ['High Exp', 'Low Exp'], // 图例两端的文字
        dimension: 2
      }
    ],
    series: [
      { // 系列1: 顶部簇分类条
        name: 'Cluster Annotation',
        type: 'heatmap',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: clusterBarData,
        label: { show: false },
        itemStyle: {
          borderColor: '#fff', // 色块间微小白边
          borderWidth: 0.5
        }
      },
      { // 系列2: 主基因热图
        name: 'Gene Expression',
        type: 'heatmap',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: rawData,
        itemStyle: {
          borderWidth: 0 // 基因像素点之间不要边框，看起来更连贯
        },
        // [关键] 添加簇分割线
        markLine: {
          symbol: ['none', 'none'], // 线两端不要箭头
          label: { show: false },
          silent: true, // 鼠标悬停不触发交互
          lineStyle: {
            color: '#000', // 黑色分割线
            type: 'dashed',
            width: 1,      // 线宽
            opacity: 1 // 不透明
          },
          data: markLines // 刚才计算出的边界位置
        }
      }
    ]
  }

  newChart.setOption(option)
}

// *********************************************
// [修改] 运行富集分析函数
// type 参数决定是跑 'GO' 还是 'KEGG'
const runEnrichmentAnalysis = async (type) => {
  // 1. 前置检查：必须先有差异分析的结果，因为我们要用到火山图里的数据
  if (!diffResult.value || !diffResult.value.volcano_data) {
    alert("请先运行步骤 4 的差异分析！我们需要差异基因列表才能做富集分析。")
    return
  }

  isEnrichmentLoading.value = true // 开启加载动画
  enrichmentType.value = type // 记录当前点击的是 GO 还是 KEGG
  enrichmentResult.value = null // 清空旧的图表数据，防止切换时闪烁

  try {
    const clusterGenesDict = {} // 新增：用于存放所有簇的显著上调基因字典

    // 2. 遍历火山图的所有簇数据，提取每个簇特有的显著上调基因
    for (const [clusterId, clusterData] of Object.entries(diffResult.value.volcano_data)) {
      // 筛选逻辑：P < 0.05 且 LogFC > 0.5 (代表在该簇中显著高表达的基因)
      const geneList = clusterData
        .filter(item => item.t_pvalue < 0.05 && item.logFC > 0.5)
        .map(item => item.gene) // 只提取基因名称字符串
      
      clusterGenesDict[clusterId] = geneList // 存入对应簇的键值对中
    }

    // 3. 发送请求给后端，把所有簇的基因字典一次性发过去
    const res = await axios.post('/api/enrichment_analysis', {
      cluster_genes: clusterGenesDict,
      database: type // 传入 'GO' 或 'KEGG'，后端去判断对应哪个文件
    })

    // 4. 处理返回结果
    if (res.data.status === 'success') {
      enrichmentResult.value = res.data.data // 保存包含所有簇结果的字典
      
      // 默认选中第一个存在的簇（将键名转为数字以便在下拉框中正确匹配）
      const clusters = Object.keys(res.data.data).map(Number)
      if(clusters.length > 0) {
        selectedEnrichmentCluster.value = clusters[0]
      }

      await nextTick() // 等待 Vue 完成 DOM 更新
      renderEnrichmentChart() // 绘制当前选中簇的图表
      // *********************************************
      // [修改] 调用绘制全簇气泡图的函数。去除了原有的传参，因为该函数内部会直接遍历读取所有簇的数据 enrichmentResult.value
      renderEnrichmentBubbleChart() 
      // *********************************************
      
      // 自动平滑滚动到显示区域
      if (enrichmentAreaRef.value) {
        enrichmentAreaRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    } else {
      alert(res.data.message)
    }

  } catch (error) {
    console.error("富集分析失败:", error)
    alert("富集分析失败: " + (error.response?.data?.detail || error.message))
  } finally {
    isEnrichmentLoading.value = false // 结束加载动画
  }
}

// [新增] 监听富集分析下拉框变化，重新绘制富集图
const handleEnrichmentClusterChange = () => {
  renderEnrichmentChart() // 当用户在下拉框选了其他簇时，直接用已缓存的数据重新画图
}

// [修改] 绘制富集分析条形图
const renderEnrichmentChart = () => {
  // 防御性检查：确保 DOM 存在且有数据
  if (!enrichmentChartRef.value || !enrichmentResult.value) return
  
  const clusterId = selectedEnrichmentCluster.value // 获取用户当前在下拉框里选择的簇
  const data = enrichmentResult.value[clusterId] // 从字典中提取对应簇的画图数据
  
  // 如果该簇没有数据或者空列表，显示提示文字
  if (!data || data.length === 0) {
    const myChart = echarts.init(enrichmentChartRef.value)
    myChart.clear() // 清空画布
    myChart.setOption({
      title: { 
        text: `Cluster ${clusterId} 未找到显著富集的通路 (基因数量可能不足)`, 
        left: 'center', top: 'center', textStyle: { color: '#888', fontWeight: 'normal' }
      }
    })
    return
  }

  const myChart = echarts.init(enrichmentChartRef.value)
  myChart.dispose() // 销毁旧实例，防止图表重叠
  const newChart = echarts.init(enrichmentChartRef.value)

  // *********************************************
  // [修改] 准备数据：为了符合PDF从上到下 BP -> CC -> MF 的顺序
  let plotData = []
  if (enrichmentType.value === 'GO') {
    // ECharts 是从下往上画的，所以数组的末尾会在图表的顶部。
    // 我们希望顶上是 BP，中间 CC，底下 MF。所以定义一个排序权重，MF在最前（画在最底下），CC居中，BP最后（画在最顶上）
    const order = { 'MF': 1, 'CC': 2, 'BP': 3 }
    // 复制数组并排序
    plotData = [...data].sort((a, b) => order[a.Category] - order[b.Category])
  } else {
    // KEGG的话按显著性排序，最显著的放顶部即可（数据已经在后端排过序，这里直接反转）
    plotData = [...data].reverse() 
  }
  // *********************************************
  
  // 处理通路名称，太长的话截断并加上省略号，防止挤压图表区域
  const terms = plotData.map(item => {
    const name = item.Term.split(' (GO')[0] // 去掉尾巴上的GO编号
    return name.length > 40 ? name.substring(0, 40) + '...' : name
  })

  // *********************************************
  // [修改] 根据当前数据库类型，配置统一的系列(series)和图例
  let seriesConfig = []
  let xAxisName = 'Gene Number' // GO 和 KEGG 统一使用基因数量作为 X 轴

  // 动态确定当前需要展示的分类和颜色
  let categories = []
  let colorMap = {}

  if (enrichmentType.value === 'GO') {
    categories = ['BP', 'CC', 'MF']
    colorMap = { 'BP': '#6fc3a1', 'CC': '#8fa5d2', 'MF': '#fb9570' } // GO 的专属颜色
  } else {
    categories = ['KEGG']
    colorMap = { 'KEGG': '#3498db' } // KEGG 的专属颜色（使用蓝色系呼应按钮颜色）
  }

  // 统一开启图例
  let legendConfig = {
    show: true,
    data: categories, // 动态使用 ['BP', 'CC', 'MF'] 或 ['KEGG']
    orient: 'vertical', // 垂直排列
    right: '2%', // 靠右放
    top: 'center' // 垂直居中
  }

  // 统一生成 series (利用循环：GO 循环3次，KEGG 循环1次)
  categories.forEach((cat) => {
    seriesConfig.push({
      name: cat,
      type: 'bar',
      barGap: '-100%', // 核心代码：让同一行的柱子互相重叠（主要针对GO，KEGG写了也不受影响）
      // 如果属于当前分类，则填入基因数量；否则填入空值('-')，ECharts 遇到空值会跳过渲染
      data: plotData.map(item => item.Category === cat ? item.Gene_Count : '-'),
      itemStyle: { 
        color: colorMap[cat],
        barBorderRadius: [0, 5, 5, 0] // 柱子右侧统一加一点圆角更好看
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params) => params.value !== '-' ? params.value : '' // 只在有数值的地方显示具体的基因数
      }
    })
  })
  // *********************************************

  const option = {
    title: {
      text: `${enrichmentType.value} Enrichment (Cluster ${clusterId})`, // 标题动态显示当前正在看的簇
      left: 'center',
      textStyle: { fontSize: 16 }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        // *********************************************
        // [修改] 提取悬停时的数据，无论怎么拆分系列，下标对齐原始 plotData
        const index = params[0].dataIndex
        const item = plotData[index]
        return `
          <b>${item.Term}</b><br/>
          P-value: ${item.P_value.toExponential(2)}<br/>
        `
        // *********************************************
      }
    },
    // *********************************************
    // [修改] 引入动态配好的图例
    legend: legendConfig,
    // *********************************************
    grid: {
      left: '35%', // 调整左侧留出空间给通路名称
      right: '12%', // 右侧留点空间给图例和基因数量文字
      bottom: '10%',
      top: '15%'
    },
    xAxis: {
      type: 'value',
      name: xAxisName, // 使用动态计算的 X 轴名称
      nameLocation: 'middle',
      nameGap: 25
    },
    yAxis: {
      type: 'category',
      data: terms,
      axisLabel: {
        interval: 0, // 强制显示所有的标签文字
        fontSize: 11,
        width: 250, // 限制最大宽度
        overflow: 'truncate' // 超过宽度就截断
      }
    },
    // *********************************************
    // [修改] 使用动态生成的 series 配置
    series: seriesConfig
    // *********************************************
  }

  newChart.setOption(option)
}

// *********************************************
// [修改] 绘制全簇通路富集气泡图（支持两种视图模式切换）
const renderEnrichmentBubbleChart = () => {
  if (!enrichmentBubbleChartRef.value || !enrichmentResult.value) return // 防御性检查

  const myChart = echarts.init(enrichmentBubbleChartRef.value)
  myChart.dispose() // 销毁旧实例，防止多次点击导致图表缓存或重叠干扰
  const newChart = echarts.init(enrichmentBubbleChartRef.value) 

  // 1. 获取所有的 Cluster ID 并排序
  const clusters = Object.keys(enrichmentResult.value).map(Number).sort() 

  // 2. 提取所有的通路名称 (Term)，用于生成气泡图的 Y 轴
  const allTermsSet = new Set() 
  clusters.forEach(cid => { 
    enrichmentResult.value[cid].forEach(item => { 
      let name = item.Term.split(' (GO')[0] 
      if (name.length > 50) name = name.substring(0, 50) + '...' 
      allTermsSet.add(name) 
    })
  })
  // 逆序排列，这样 ECharts 在从下往上画 Y 轴时，最先出现的显著通路会展示在图表最上方
  const allTerms = Array.from(allTermsSet).reverse()

  // *********************************************
  // [修改开始] 根据用户选中的模式，分别构建 ECharts 需要的 Series、X轴、Y轴、图例和网格配置
  let scatterSeries = []
  let xAxisOption = {}
  let yAxisOption = {}
  let legendOption = null // 专门留给模式2（按基因数）的图例
  let minP = 1, maxP = 0 

  if (bubbleChartMode.value === 'combined') {
    // === 模式 1: 按簇平铺 (复刻 Combined_KEGG_enrichment.pdf) ===
    
    const scatterData = []
    // 为了让点在网格线上，且外围有边距，给数组头尾增加一个空字符串
    const displayClusters = ['', ...clusters.map(String), '']
    const displayTerms = ['', ...allTerms, '']

    clusters.forEach((cid, xIdx) => { 
      enrichmentResult.value[cid].forEach(item => {
        let name = item.Term.split(' (GO')[0] 
        if (name.length > 50) name = name.substring(0, 50) + '...'
        const yIdx = allTerms.indexOf(name) 
        const pVal = item.Adjusted_P || item.P_value

        if (pVal < minP) minP = pVal
        if (pVal > maxP) maxP = pVal

        // ECharts Scatter 数据格式: [X轴, Y轴, pVal, geneCount, name, clusterId]
        scatterData.push([
          xIdx + 1,       // X轴坐标 (避开头部占位符)
          yIdx + 1,       // Y轴坐标 (避开头部占位符)
          pVal,           
          item.Gene_Count,
          name,           
          cid             
        ])
      })
    })

    // 模式1只需单个 Series 包含所有点
    scatterSeries = [{
      name: 'Enrichment Bubble', 
      type: 'scatter', 
      data: scatterData, 
      itemStyle: { opacity: 0.9, borderColor: 'transparent' }
    }]

    // 模式1的坐标轴是类别型 (Category)，对应簇ID和通路名
    xAxisOption = { 
      type: 'category',
      data: displayClusters,
      boundaryGap: false, // 关闭留白，让点压在网格线上
      name: 'Cluster', 
      nameLocation: 'middle', 
      nameGap: 30, 
      nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' }, 
      axisLine: { show: false }, 
      axisTick: { show: true, alignWithLabel: true, inside: false, lineStyle: { color: '#000' } }, 
      axisLabel: { color: '#000', fontSize: 12, interval: 0, formatter: (val) => val === '' ? '' : val },
      splitLine: { show: true, lineStyle: { type: 'solid', color: '#eaeaea' } }
    }
    
    yAxisOption = { 
      type: 'category',
      data: displayTerms,
      boundaryGap: false,
      name: enrichmentType.value === 'GO' ? 'GO Pathways' : 'KEGG Pathways',
      nameLocation: 'middle',
      nameGap: 220, 
      nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' },
      axisLine: { show: false },
      axisTick: { show: true, alignWithLabel: true, inside: false, lineStyle: { color: '#000' } },
      axisLabel: { color: '#000', fontSize: 12, interval: 0, formatter: (val) => val === '' ? '' : val }, 
      splitLine: { show: true, lineStyle: { type: 'solid', color: '#eaeaea' } }
    }

  } else {
    // === 模式 2: 按基因数分布 (复刻单簇 PDF 的效果，并通过图例切换) ===
    
    const legendData = []

    // 遍历每一个簇，将其作为一个独立的 Series 处理，这样 ECharts 的图例才能做到单独点击切换隐藏
    clusters.forEach(cid => {
      const clusterData = []
      
      enrichmentResult.value[cid].forEach(item => {
        let name = item.Term.split(' (GO')[0]
        if (name.length > 50) name = name.substring(0, 50) + '...'
        const pVal = item.Adjusted_P || item.P_value

        if (pVal < minP) minP = pVal
        if (pVal > maxP) maxP = pVal

        // 依然保持 [X轴, Y轴, pVal, geneCount, name, cid] 的结构，但 X 轴变成了基因数，Y 轴直接放字符串
        clusterData.push([
          item.Gene_Count, // X 轴变为具体的数值 (基因数)
          name,            // Y 轴可以直接接受 Category 类型的字符串名称
          pVal,
          item.Gene_Count,
          name,
          cid
        ])
      })

      // 将该簇作为独立的图表系列压入数组
      scatterSeries.push({
        name: `Cluster ${cid}`, // 这将显示在图例上
        type: 'scatter',
        data: clusterData,
        itemStyle: { opacity: 0.9, borderColor: 'transparent' }
      })
      // 将图例名称加入图例数组
      legendData.push(`Cluster ${cid}`)
    })

    // 激活原生图例组件，允许用户点击隐藏/显示某个簇
    legendOption = {
      data: legendData,
      orient: 'vertical',
      right: '15%',
      top: '5%',
      textStyle: { fontWeight: 'bold', color: '#000' }
    }

    // 模式2的 X 轴是数值型 (Value)
    xAxisOption = {
      type: 'value',
      name: 'Gene Number',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' },
      axisLine: { show: true, lineStyle: { color: '#000' } },
      axisTick: { show: true, lineStyle: { color: '#000' } },
      axisLabel: { color: '#000', fontSize: 12 },
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#eaeaea' } } // 模拟单簇PDF通常用的虚线
    }

    // 模式2的 Y 轴是普通的类别型，不需要补首尾空字符
    yAxisOption = {
      type: 'category',
      data: allTerms,
      name: enrichmentType.value === 'GO' ? 'GO Pathways' : 'KEGG Pathways',
      nameLocation: 'middle',
      nameGap: 220,
      nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' },
      axisLine: { show: false },
      axisTick: { show: true, alignWithLabel: true, inside: false, lineStyle: { color: '#000' } },
      axisLabel: { color: '#000', fontSize: 12, interval: 0 },
      splitLine: { show: true, lineStyle: { type: 'solid', color: '#eaeaea' } }
    }
  }
  // [修改结束]
  // *********************************************

  if (maxP < 0.05) maxP = 0.05

  const option = {
    title: {
      text: `${enrichmentType.value} Pathway Enrichment - All Clusters`, 
      left: 'center', 
      textStyle: { fontSize: 16, fontFamily: 'Arial', fontWeight: 'bold', color: '#000' }
    },
    // *********************************************
    // [修改] 如果存在图例（模式2），则将其加入配置中
    legend: legendOption ? legendOption : undefined,
    // *********************************************
    tooltip: { 
      trigger: 'item',
      formatter: (params) => { 
        // 这里的解包对两种模式的数据结构是完全兼容的
        const d = params.data
        return `<b>${d[4]}</b><br/>Cluster: ${d[5]}<br/>p.adjust: ${d[2].toExponential(3)}<br/>Gene Count: ${d[3]}`
      }
    },
    grid: { 
      show: true,               
      borderColor: '#000',      
      borderWidth: 1,           
      left: '25%',              
      // *********************************************
      // [修改] 根据模式动态分配右侧边距，模式2的图例可能会更宽
      right: bubbleChartMode.value === 'combined' ? '15%' : '25%',
      // ********************************************* bottom: '10%',
      top: '12%'
    },
    // *********************************************
    // [修改] 引用前面处理好的动态坐标轴和Series
    xAxis: xAxisOption,
    yAxis: yAxisOption,
    // *********************************************
    visualMap: [ 
      {
        type: 'continuous', 
        dimension: 2, 
        min: minP, 
        max: maxP, 
        inverse: true, 
        orient: 'vertical', 
        top: '20%', 
        right: '2%', 
        inRange: {
          color: ['#ff0000', '#0000ff'] 
        },
        text: ['p.adjust', ''], 
        textStyle: { fontWeight: 'bold', color: '#000' },
        calculable: false, 
        itemWidth: 15,
        itemHeight: 100, 
        formatter: (value) => {
          return value < 0.001 ? value.toExponential(2) : value.toFixed(2)
        }
      },
      {
        type: 'piecewise', 
        dimension: 3, 
        orient: 'vertical', 
        bottom: '15%', 
        right: '2%', 
        splitNumber: 3, 
        inRange: {
          symbolSize: [8, 20] 
        },
        text: ['\nGene Count', ''], 
        textStyle: { fontWeight: 'bold', color: '#000' },
        itemSymbol: 'circle',
        itemGap: 15 
      }
    ],
    // *********************************************
    // [修改] 引用动态生成的系列数组
    series: scatterSeries
    // *********************************************
  }

  newChart.setOption(option) 
}

// *********************************************
// [新增] 运行测试模式（参数敏感性分析）的函数
const runParameterSearch = async () => {
  if(omicsFileConfigs.value.length === 0 || !clinicalFile.value) {
    alert("测试模式需要计算 P-value，请确保已选择组学数据和临床数据！")
    return
  }
  // // 防御性检查：测试模式依赖组学数据进行聚类，依赖临床数据计算生存 P 值，必须都有
  // if(!uploadedFilename.value || !clinicalFilename.value) {
  //   alert("测试模式需要计算 P-value，请确保已上传组学数据和临床数据！")
  //   return
  // }
  // ======================== 修改代码 ========================
  // 为什么要这么写：与普通运行分析同理，针对测试模式下的算法请求，同样基于数组 length 属性进行边界检查，拦截空选与多选行为。
  if(selectedAlgorithm.value.length === 0){
    alert("请先选择至少一种算法！")
    return
  }
  if(selectedAlgorithm.value.length > 1){
    alert("测试模式暂时不能多选算法，请只选择一种！")
    return
  }

  isPsLoading.value = true // 开启加载状态
  psResult.value = null // 清空旧结果

  try {
    // // 将前端绑定的逗号分隔字符串（如 "2,3,4"）分割成数组，并转换为纯数字列表
    // const n_clusters_arr = testNClusters.value.split(',').map(Number)
    // const max_iter_arr = testMaxIter.value.split(',').map(Number)
    // 【双重拦截上传】
    if (!isOmicsUploaded.value) await uploadFile()
    if (!isClinicalUploaded.value) await uploadClinicalFile()

    // 【修改】根据所选算法动态构建测试的 param_grid 和默认坐标轴
    let paramGridObj = {}
    if(selectedAlgorithm.value[0] === 'K-means') {
      paramGridObj = {
        "n_clusters": testNClusters.value.split(',').map(Number),
        "max_iter": testMaxIter.value.split(',').map(Number)
      }
      psParam1.value = 'n_clusters'
      psParam2.value = 'max_iter'
    }
    else if (selectedAlgorithm.value[0] === 'Spectral Clustering') {
      paramGridObj = {
        "n_clusters": testNClusters.value.split(',').map(Number),
        "n_neighbors": testNNeighbors.value.split(',').map(Number)
      }
      psParam1.value = 'n_clusters'
      psParam2.value = 'n_neighbors'
    }
    else if (selectedAlgorithm.value[0] === 'NEMO') {
      paramGridObj = {
        "n_clusters": testNClusters.value.split(',').map(Number)
      }
      psParam1.value = 'n_clusters'
      psParam2.value = '' // NEMO 只有一个主要参数，留空以绘制 2D 折线图
    }
    else if (selectedAlgorithm.value[0] === 'SNF') {
      paramGridObj = {
        "n_clusters": testNClusters.value.split(',').map(Number),
        "n_neighbors": testNNeighbors.value.split(',').map(Number)
      }
      psParam1.value = 'n_clusters'
      psParam2.value = 'n_neighbors'
    }

    // 发送 POST 请求到后端的测试模式接口
    const res = await axios.post('/api/parameter_search', {
      algorithm: selectedAlgorithm.value[0], // 当前算法名 // 为什么要这么写：同样使用索引 [0] 提取选中的算法名称作为字符串数据格式传递，满足后端 ParameterSearchRequest 接口规范。
      session_id: sessionId.value, // 【修改】
      // omics_filename: uploadedFilename.value, // 上传好的组学文件名
      // clinical_filename: clinicalFilename.value, // 上传好的临床文件名
      param_grid: paramGridObj, // 【修改】传入动态构建的网格字典
      // param_grid: { // 构建需要测试的参数网格字典传给后端
      //   "n_clusters": n_clusters_arr,
      //   "max_iter": max_iter_arr
      // },
      random_state: randomSeed.value // 传入随机种子
    })

    psResult.value = res.data // 将后端结果赋值给响应式变量，触发视图更新
    await nextTick() // 等待 Vue 重新渲染 DOM 容器出现
    renderPsChart() // 调用绘图函数渲染 2D 或 3D 图表
  } catch (error) {
    console.error("参数搜索失败:", error)
    alert("测试模式运行失败: " + (error.response?.data?.detail || error.message))
  } finally {
    isPsLoading.value = false // 无论成功失败，关闭加载状态
  }
}

// [新增] 绘制参数敏感性分析图表的函数
const renderPsChart = () => {
  // 防御性检查：确保 DOM 和 数据存在
  if (!psChartRef.value || !psResult.value) return

  const myChart = echarts.init(psChartRef.value)
  myChart.dispose() // 销毁之前的 ECharts 实例，防止画布重叠污染
  const newChart = echarts.init(psChartRef.value)

  const all_results = psResult.value.all_results // 提取包含所有测试组合及得分的数组
  const p1 = psParam1.value // 用户选择的 X 轴参数
  const p2 = psParam2.value // 用户选择的 Y 轴参数

  // 场景 1：用户选择了两个不相同的参数，绘制 3D 曲面图（对应上传的 PDF 效果）
  if (p1 && p2 && p1 !== p2) {
    // 将数据转换成 ECharts 3D surface 要求的格式：[[x, y, z], [x, y, z]...]
    const data = all_results.map(item => [
      item.params[p1], // X轴坐标
      item.params[p2], // Y轴坐标
      item.score       // Z轴坐标（这里是 -Log10 P-value）
    ])

    newChart.setOption({
      tooltip: {}, // 开启鼠标悬停提示框
      // visualMap 配置颜色映射，用来让高低不同的 Z 轴值显示冷暖色彩变化
      visualMap: {
        show: false, // 隐藏图例以节省空间
        min: Math.min(...data.map(d => d[2])), // 数据中的最小得分
        max: Math.max(...data.map(d => d[2])), // 数据中的最大得分
        inRange: {
          color: ['#313695', '#4575b4', '#e0f3f8', '#fee090', '#f46d43', '#a50026'] // 使用渐变色（蓝到红）来模拟热力高度
        }
      },
      xAxis3D: { type: 'value', name: p1 }, // 3D X轴配置
      yAxis3D: { type: 'value', name: p2 }, // 3D Y轴配置
      zAxis3D: { type: 'value', name: '-Log10(P)' }, // 3D Z轴配置
      grid3D: {
        viewControl: { projection: 'perspective' } // 使用透视投影视角，让曲面更立体
      },
      series: [{
        type: 'surface', // 关键参数：指定图表类型为 3D 曲面图（依赖 echarts-gl）
        data: data,
        // wireframe: show: true 控制是否显示曲面上的网格线，复刻 PDF 中网格布的效果
        wireframe: { show: true, lineStyle: { color: 'rgba(0,0,0,0.3)', width: 1 } } 
      }]
    })
  } 
  // 场景 2：用户只选择了一个参数（或把两个参数选成一样的了），降维绘制 2D 折线图
  else if (p1) {
    // 使用 Set 提取该参数的唯一值，并从小到大排序作为 X 轴刻度
    const unique_x = [...new Set(all_results.map(item => item.params[p1]))].sort((a,b)=>a-b)
    
    // 如果有多个组合（比如测试了K和MaxIter，但图表只选了K），我们取同一个 K 下最大的得分代表它的最佳潜力
    const y_data = unique_x.map(x => {
      const matched = all_results.filter(item => item.params[p1] === x)
      return Math.max(...matched.map(m => m.score)) // 求该参数值下的最大得分
    })

    newChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: unique_x, name: p1, nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: '-Log10(P-value)', nameLocation: 'middle', nameGap: 40 },
      series: [{
        type: 'line', // 使用普通 2D 折线图
        data: y_data,
        smooth: true, // 让线条平滑曲线过渡
        lineStyle: { width: 3 }
      }]
    })
  }
}
// *********************************************
</script>





<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <div class="logo">
          InferenceDeck
        </div>
        <nav class="app-nav">
          <button @click="activeTab = 'Home'" :class="{ active: activeTab === 'Home' }">Home</button>
          <button @click="activeTab = 'Analysis'" :class="{ active: activeTab === 'Analysis' }">Analysis</button>
          <button @click="activeTab = 'Resources'" :class="{ active: activeTab === 'Resources' }">Resources</button>
          <button @click="activeTab = 'Help'" :class="{ active: activeTab === 'Help' }">Help</button>
        </nav>
      </div>
    </header>

    <main class="main-content">
      <div v-if="activeTab === 'Home'" class="hero-section">
        <div class="hero-content">
          <h1>多组学癌症亚型分析平台</h1>
          <p>基于前沿算法与多组学数据，快速、精准识别癌症分子亚型</p>
          <button class="action-btn primary large" @click="activeTab = 'Analysis'">开始分析之旅</button>
        </div>
      </div>

      <div v-else class="analysis-dashboard">

        <div class="test-mode-switch" :class="{ 'is-active': isCustomEvalMode }" style="margin: 0 auto 24px auto; max-width: 450px;">
        <!-- <div class="test-mode-switch" :class="{ 'is-active': isCustomEvalMode }" style="margin-bottom: 24px; max-width: 450px;"> -->
          <label class="switch-container">
            <input type="checkbox" v-model="isCustomEvalMode" />
            <span class="slider round"></span>
          </label>
          <div class="switch-info">
            <strong>我想测试自己的算法</strong>
            <span>需要上传聚类结果和特征矩阵</span>
          </div>
        </div>

        <div class="config-grid">
          
          <div class="config-card">
            <div class="card-header">
              <span class="icon">📂</span>
              <h3>1. 数据上传</h3>
            </div>
            <div class="card-body">
              
              <div class="upload-section">
                <h4>🧬 组学数据 <span class="badge required">111</span></h4>
                <div class="format-toggles">
                  <label class="toggle-label" :class="{ 'is-checked': omicsIsRowSample }">
                    <input type="checkbox" v-model="omicsIsRowSample" @change="handleFormatChange" />
                    行代表特征, 列代表病人
                  </label>
                  <label class="toggle-label" :class="{ 'is-checked': omicsHasHeader }">
                    <input type="checkbox" v-model="omicsHasHeader" @change="handleFormatChange" />
                    包含表头行
                  </label>
                  <label class="toggle-label" :class="{ 'is-checked': omicsHasIndex }">
                    <input type="checkbox" v-model="omicsHasIndex" @change="handleFormatChange" />
                    包含索引列
                  </label>
                </div>
                
                <div class="code-preview">
                  <div class="preview-header">CSV 格式预览</div>
                  <pre>{{ exampleText }}</pre>
                </div>

                <div class="file-drop-zone">
                  <input type="file" @change="handleFileChange" multiple class="file-input" id="omics-file"/>
                  <label for="omics-file" class="file-label">
                    <span class="upload-text">选择或拖入组学文件 (支持多选)</span>
                    <small>如果是多个文件，平台将自动取病人交集；如果是多个同一组学类型的文件，平台还将自动按特征列拼接</small>
                  </label>
                </div>
                <div v-if="omicsFileConfigs.length > 0" class="file-config-list mt-3">
                  <div v-for="config in omicsFileConfigs" :key="config.id" class="file-config-item">
                    <span class="file-name" :title="config.originalName">📄 {{ config.originalName }}</span>
                    <select v-model="config.type" @change="handleFormatChange" class="ui-select mini config-select">
                      <option v-for="type in omicsTypes" :key="type" :value="type">{{ type }}</option>
                    </select>
                  </div>
                </div>
                <div class="status-msg" :class="{ 'is-error': uploadStatus.startsWith('❌'), 'is-success': uploadStatus.startsWith('✅') }" v-show="uploadStatus">
                  {{ uploadStatus }}
                </div>
              </div>

              <hr class="divider" />

              <div class="upload-section">
                <h4>🏥 临床数据 <span class="badge optional">222</span></h4>
                <div class="format-toggles">
                  <label class="toggle-label" :class="{ 'is-checked': clinicalIsRowSample }">
                    <input type="checkbox" v-model="clinicalIsRowSample" @change="handleClinicalFormatChange" />
                    行代表特征, 列代表病人
                  </label>
                  <label class="toggle-label" :class="{ 'is-checked': clinicalHasHeader }">
                    <input type="checkbox" v-model="clinicalHasHeader" @change="handleClinicalFormatChange" />
                    包含表头行
                  </label>
                  <label class="toggle-label" :class="{ 'is-checked': clinicalHasIndex }">
                    <input type="checkbox" v-model="clinicalHasIndex" @change="handleClinicalFormatChange" />
                    包含索引列
                  </label>
                </div>
                
                <div class="code-preview">
                  <div class="preview-header">CSV 格式预览</div>
                  <pre>{{ clinicalExampleText }}</pre>
                </div>

                <div class="file-drop-zone">
                  <input type="file" @change="handleClinicalFileChange" class="file-input" id="clinical-file"/>
                  <label for="clinical-file" class="file-label">
                    <span class="upload-text">点击选择临床文件</span>
                    <small>需包含 OS 和 OS.time</small>
                  </label>
                </div>
                <div class="status-msg" :class="{ 'is-error': clinicalUploadStatus.startsWith('❌'), 'is-success': clinicalUploadStatus.startsWith('✅') }" v-show="clinicalUploadStatus">
                  {{ clinicalUploadStatus }}
                </div>
              </div>

            </div>
          </div>

          <div class="config-card" v-if="!isCustomEvalMode">
            <div class="card-header">
              <span class="icon">⚙️</span>
              <h3>2. 算法选择</h3>
            </div>
            <div class="card-body">
              <div class="test-mode-switch" :class="{ 'is-active': isTestMode }">
                <label class="switch-container">
                  <input type="checkbox" v-model="isTestMode" />
                  <span class="slider round"></span>
                </label>
                <div class="switch-info">
                  <strong>开启测试模式</strong>
                  <span>执行参数敏感性分析</span>
                </div>
              </div>

              <div class="algo-list">
                <h4 class="section-subtitle">可用聚类算法</h4>
                <label 
                  v-for="algo in algorithms" 
                  :key="algo" 
                  class="algo-item"
                  :class="{ 'is-selected': selectedAlgorithm.includes(algo) }"
                >
                  <input type="checkbox" v-model="selectedAlgorithm" :value="algo" />
                  <span class="algo-name">{{ algo }}</span>
                  <span class="check-icon" v-if="selectedAlgorithm.includes(algo)">✓</span>
                </label>
              </div>
            </div>
          </div>

          <div class="config-card" v-if="!isCustomEvalMode">
            <div class="card-header">
              <span class="icon">🎛️</span>
              <h3>3. 参数配置</h3>
            </div>
            <div class="card-body">
              
              <div v-if="selectedAlgorithm.length === 0" class="empty-state">
                <span class="empty-icon">👈</span>
                <p>请先在左侧选择一种算法</p>
              </div>

              <div v-else class="params-container">
                <template v-if="!isTestMode">
                  <div v-if="selectedAlgorithm.includes('K-means')" class="param-group">
                    <h4 class="algo-badge">K-means 参数</h4>
                    <div class="input-field">
                      <label>聚类簇数 (K值)</label>
                      <input type="number" v-model="kValue" />
                    </div>
                    <div class="input-field">
                      <label>随机种子 (-1表示None)</label>
                      <input type="number" v-model="randomSeed" />
                    </div>
                    <div class="input-field">
                      <label>最大迭代</label>
                      <input type="number" v-model="maxIter" />
                    </div>
                  </div>

                  <div v-if="selectedAlgorithm.includes('Spectral Clustering')" class="param-group">
                    <h4 class="algo-badge">Spectral Clustering 参数</h4>
                    <div class="input-field">
                      <label>聚类簇数 (K值)</label>
                      <input type="number" v-model="kValue" />
                    </div>
                    <div class="input-field">
                      <label>邻居数 (n_neighbors)</label>
                      <input type="number" v-model="nNeighbors" />
                    </div>
                    <div class="input-field">
                      <label>随机种子 (-1表示None)</label>
                      <input type="number" v-model="randomSeed" />
                    </div>
                  </div>

                  <div v-if="selectedAlgorithm.includes('NEMO')" class="param-group">
                    <h4 class="algo-badge">NEMO 参数</h4>
                    <div class="input-field">
                      <label>聚类簇数 (K值)</label>
                      <input type="number" v-model="kValue" />
                    </div>
                  </div>

                  <div v-if="selectedAlgorithm.includes('SNF')" class="param-group">
                    <h4 class="algo-badge">SNF 参数</h4>
                    <div class="input-field">
                      <label>聚类簇数 (K值)</label>
                      <input type="number" v-model="kValue" />
                    </div>
                    <div class="input-field">
                      <label>构建KNN网络邻居数 (K)</label>
                      <input type="number" v-model="nNeighbors" />
                    </div>
                  </div>
                </template>

                <template v-else>
                  <div class="alert-box warning">
                    ⚠️ 测试模式需利用临床文件计算P-value，请确保已上传。
                  </div>

                  <div v-if="selectedAlgorithm.includes('K-means')" class="param-group test-params">
                    <h4 class="algo-badge">K-means 测试范围</h4>
                    <div class="input-field">
                      <label>聚类簇数范围 (逗号分隔)</label>
                      <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" />
                    </div>
                    <div class="input-field">
                      <label>最大迭代范围 (逗号分隔)</label>
                      <input type="text" v-model="testMaxIter" placeholder="如: 100,200,300" />
                    </div>
                    <div class="input-field">
                      <label>随机种子</label>
                      <input type="number" v-model="randomSeed" />
                    </div>
                  </div>

                  <div v-if="selectedAlgorithm.includes('Spectral Clustering')" class="param-group test-params">
                    <h4 class="algo-badge">Spectral Clustering 测试范围</h4>
                    <div class="input-field">
                      <label>聚类簇数范围 (逗号分隔)</label>
                      <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" />
                    </div>
                    <div class="input-field">
                      <label>邻居数范围 (逗号分隔)</label>
                      <input type="text" v-model="testNNeighbors" placeholder="如: 5,10,15" />
                    </div>
                    <div class="input-field">
                      <label>随机种子</label>
                      <input type="number" v-model="randomSeed" />
                    </div>
                  </div>

                  <div v-if="selectedAlgorithm.includes('NEMO')" class="param-group test-params">
                    <h4 class="algo-badge">NEMO 测试范围</h4>
                    <div class="input-field">
                      <label>聚类簇数范围 (逗号分隔)</label>
                      <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" />
                    </div>
                    <div class="input-field">
                      <label>随机种子</label>
                      <input type="number" v-model="randomSeed" />
                    </div>
                  </div>

                  <div v-if="selectedAlgorithm.includes('SNF')" class="param-group test-params">
                    <h4 class="algo-badge">SNF 测试范围</h4>
                    <div class="input-field">
                      <label>聚类簇数范围 (逗号分隔)</label>
                      <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" />
                    </div>
                    <div class="input-field">
                      <label>邻居数范围 (逗号分隔)</label>
                      <input type="text" v-model="testNNeighbors" placeholder="如: 10,20,30" />
                    </div>
                    <div class="input-field">
                      <label>随机种子</label>
                      <input type="number" v-model="randomSeed" />
                    </div>
                  </div>
                </template>
              </div>

            </div>
          </div>

          <div class="config-card" v-if="isCustomEvalMode">
            <div class="card-header">
              <span class="icon">📥</span>
              <h3>2. 结果数据上传</h3>
            </div>
            <div class="card-body">
              <div class="upload-section">
                <h4>📊 聚类结果与特征矩阵 <span class="badge required">333</span></h4>
                <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.6;">
                  请把你上传的组学数据作为输入，用你自己的算法，生成一个CSV/Excel文件：<br>
                  1.从左到右分别是<br>
                  <strong>病人名称</strong>（索引列）、<br>
                  <strong>聚类结果</strong>（第2列）、<br>
                  <strong>融合后的特征矩阵</strong>（第3列及之后）。<br>
                  2.行代表病人，列代表特征。有表头行、索引列。
                </p>
                
                <div class="file-drop-zone">
                  <input type="file" @change="handleCustomEvalFileChange" class="file-input" accept=".csv, .xlsx, .xls"/>
                  <label class="file-label">
                    <span class="upload-text">点击选择结果数据文件</span>
                  </label>
                </div>
                <div class="status-msg" :class="{ 'is-success': customEvalUploadStatus }" v-show="customEvalUploadStatus">
                  {{ customEvalUploadStatus }}
                </div>
              </div>
            </div>
          </div>

        </div>

        <div class="action-center">
          <button v-if="!isTestMode" @click="runAnalysis" :disabled="isLoading" class="run-btn primary-btn">
            <span class="btn-content">
              <span v-if="isLoading" class="spinner"></span>
              {{ isLoading ? '分析运行中...' : '🚀 启动聚类分析 (Run Analysis)' }}
            </span>
          </button>
          
          <button v-else @click="runParameterSearch" :disabled="isPsLoading" class="run-btn danger-btn">
            <span class="btn-content">
              <span v-if="isPsLoading" class="spinner"></span>
              {{ isPsLoading ? '搜索测试中...' : '🎯 运行参数敏感性搜索' }}
            </span>
          </button>
        </div>

        <div v-if="errorMessage" class="global-error">
          <span class="icon">❌</span> {{ errorMessage }}
        </div>

        <div v-if="isTestMode && psResult" class="results-container test-results fade-in">
          <div class="result-header test-header">
            <h3>🔬 参数敏感性分析结果 (Parameter Search)</h3>
          </div>
          <div class="result-body">
            <div class="best-params-card">
              <div class="bpc-icon">🏆</div>
              <div class="bpc-content">
                <h4>最优参数组合</h4>
                <div class="bpc-details">
                  <span class="bpc-tag"><strong>参数:</strong> {{ psResult.best_params }}</span>
                  <span class="bpc-tag highlight"><strong>-Log10(P):</strong> {{ psResult.best_score.toFixed(4) }}</span>
                </div>
                <p class="bpc-hint">得分越高，代表该参数组合下聚类生成的生存差异越显著。</p>
              </div>
            </div>
            
            <div class="chart-panel">
              <div class="chart-toolbar">
                <div class="toolbar-title">📈 参数敏感性分布图</div>
                <div class="toolbar-actions">
                  <div class="select-group">
                    <label>X轴:</label>
                    <select v-model="psParam1" @change="renderPsChart" class="ui-select">
                      <option value="n_clusters">K值 (n_clusters)</option>
                      <option value="max_iter">最大迭代 (max_iter)</option>
                      <option value="n_neighbors">邻居数 (谱聚类)</option>
                    </select>
                  </div>
                  <div class="select-group">
                    <label>Y轴:</label>
                    <select v-model="psParam2" @change="renderPsChart" class="ui-select">
                      <option value="">无 (绘制2D折线图)</option>
                      <option value="n_clusters">K值 (n_clusters)</option>
                      <option value="max_iter">最大迭代 (max_iter)</option>
                      <option value="n_neighbors">邻居数 (谱聚类)</option>
                    </select>
                  </div>
                </div>
              </div>
              <div ref="psChartRef" class="echart-wrapper"></div>
            </div>
          </div>
        </div>

        <div v-if="!isTestMode && backendResponse" class="results-container flow-results fade-in" ref="resultsAreaRef">
          
          <div class="result-block clustering-block">
            <div class="block-header">
              <h3><span class="step-num">A</span> 聚类效果评估与降维可视化</h3>
            </div>
            <div class="block-body">
              <div class="alert-box warning" style="margin-bottom: 20px;">
                ⚠️ <strong>提示：</strong>在与组学/临床数据取交集时，有 <strong>{{ backendResponse.data.lost_samples }}</strong> 个病人因无法完全对齐而被系统丢弃。
              </div>
              <div v-if="backendResponse.data.metrics" class="metrics-row">
                <div class="metric-widget">
                  <div class="mw-title">Silhouette Score</div>
                  <div class="mw-value">{{ backendResponse.data.metrics.silhouette ?? 'N/A' }}</div>
                  <div class="mw-desc">轮廓系数 ↑</div>
                </div>
                <div class="metric-widget">
                  <div class="mw-title">Calinski-Harabasz</div>
                  <div class="mw-value">{{ backendResponse.data.metrics.calinski ?? 'N/A' }}</div>
                  <div class="mw-desc">CH 指数 ↑</div>
                </div>
                <div class="metric-widget">
                  <div class="mw-title">Davies-Bouldin</div>
                  <div class="mw-value">{{ backendResponse.data.metrics.davies ?? 'N/A' }}</div>
                  <div class="mw-desc">DB 指数 ↓</div>
                </div>
                <div class="metric-widget">
                  <div class="mw-title">Dunn Index</div>
                  <div class="mw-value">{{ backendResponse.data.metrics.dunn ?? 'N/A' }}</div>
                  <div class="mw-desc">Dunn 指数 ↑</div>
                </div>
                <div class="metric-widget">
                  <div class="mw-title">Xie-Beni</div>
                  <div class="mw-value">{{ backendResponse.data.metrics.xb ?? 'N/A' }}</div>
                  <div class="mw-desc">XB 指数 ↓</div>
                </div>
                <div class="metric-widget">
                  <div class="mw-title">S_Dbw</div>
                  <div class="mw-value">{{ backendResponse.data.metrics.s_dbw ?? 'N/A' }}</div>
                  <div class="mw-desc">S_Dbw 指数 ↓</div>
                </div>
              </div>

              <div class="chart-panel">
                <div class="chart-toolbar">
                  <div class="toolbar-title">🎨 样本聚类分布</div>
                  <div class="toolbar-actions">
                    <div class="button-group">
                      <button @click="switchReduction('PCA')" :class="{ active: currentReduction==='PCA' }" :disabled="isLoading">PCA</button>
                      <button @click="switchReduction('t-SNE')" :class="{ active: currentReduction==='t-SNE' }" :disabled="isLoading">t-SNE</button>
                      <button @click="switchReduction('UMAP')" :class="{ active: currentReduction==='UMAP' }" :disabled="isLoading">UMAP</button>
                    </div>
                  </div>
                </div>
                <div ref="chartRef" class="echart-wrapper"></div>
              </div>
            </div>
          </div>

          <div class="result-block diff-block" ref="diffAnalysisAreaRef">
            <div class="block-header diff-color">
              <h3><span class="step-num">B</span> 差异表达分析 (Differential Expression)</h3>

              <div class="mini-btn-group" style="display: flex; gap: 12px; align-items: center;">
                <select v-model="selectedDiffOmicsType" class="ui-select mini" style="min-width: 120px;">
                  <option value="" disabled>请选择组学层</option>
                  <option v-for="type in uploadedOmicsTypes" :key="type" :value="type">{{ type }}</option>
                </select>

                <button @click="runDifferentialAnalysis" :disabled="isDiffLoading" class="mini-run-btn diff-btn">
                  {{ isDiffLoading ? '分析中...' : '运行差异分析' }}
                </button>
              </div>

            </div>
            <div class="block-body">
              <p class="block-desc">基于聚类结果执行 One-vs-Rest 差异基因计算，鉴定出每个亚型的特异性高表达基因。</p>
              
              <div v-if="diffErrorMessage" class="alert-box error">{{ diffErrorMessage }}</div>

              <div v-if="diffResult" class="diff-charts-grid fade-in">
                <div class="chart-panel">
                  <div class="chart-toolbar">
                    <div class="toolbar-title">🌋 差异火山图</div>
                    <select v-model="selectedVolcanoCluster" @change="handleVolcanoClusterChange" class="ui-select mini">
                      <option v-for="cid in Object.keys(diffResult.volcano_data)" :key="cid" :value="Number(cid)">Cluster {{ cid }}</option>
                    </select>
                  </div>
                  <div ref="volcanoChartRef" class="echart-wrapper"></div>
                </div>

                <div class="chart-panel">
                  <div class="chart-toolbar">
                    <div class="toolbar-title">🔥 差异基因热图 (Top 10)</div>
                  </div>
                  <div ref="heatmapChartRef" class="echart-wrapper"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="result-block enrich-block" v-if="diffResult" ref="enrichmentAreaRef">
            <div class="block-header enrich-color">
              <h3><span class="step-num">C</span> 功能富集分析 (Enrichment Analysis)</h3>
              <div class="mini-btn-group">
                <button @click="runEnrichmentAnalysis('GO')" :disabled="isEnrichmentLoading" class="mini-run-btn go-btn">
                  {{ (isEnrichmentLoading && enrichmentType==='GO') ? '查询中...' : '运行 GO' }}
                </button>
                <button @click="runEnrichmentAnalysis('KEGG')" :disabled="isEnrichmentLoading" class="mini-run-btn kegg-btn">
                  {{ (isEnrichmentLoading && enrichmentType==='KEGG') ? '查询中...' : '运行 KEGG' }}
                </button>
              </div>
            </div>
            <div class="block-body">
              <p class="block-desc">针对各个簇的显著上调基因（P<0.05, LogFC>0.5），在数据库中查找显著富集的生物学通路。</p>

              <div v-if="enrichmentResult" class="enrichment-charts fade-in">
                <div class="chart-panel">
                  <div class="chart-toolbar">
                    <div class="toolbar-title">📊 单簇富集条形图</div>
                    <select v-model="selectedEnrichmentCluster" @change="handleEnrichmentClusterChange" class="ui-select mini">
                      <option v-for="cid in Object.keys(enrichmentResult)" :key="cid" :value="Number(cid)">Cluster {{ cid }}</option>
                    </select>
                  </div>
                  <div ref="enrichmentChartRef" class="echart-wrapper"></div>
                </div>

                <div class="chart-panel mt-4">
                  <div class="chart-toolbar">
                    <div class="toolbar-title">🎈 全簇通路富集气泡图</div>
                    <div class="toolbar-actions radio-toggles">
                      <label class="radio-label">
                        <input type="radio" v-model="bubbleChartMode" value="combined" @change="renderEnrichmentBubbleChart"> 按簇平铺
                      </label>
                      <label class="radio-label">
                        <input type="radio" v-model="bubbleChartMode" value="by_gene" @change="renderEnrichmentBubbleChart"> 按基因分布
                      </label>
                    </div>
                  </div>
                  <div ref="enrichmentBubbleChartRef" class="echart-wrapper"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="result-block survival-block" ref="survivalAreaRef">
            <div class="block-header survival-color">
              <h3><span class="step-num">D</span> 临床预后生存分析 (Survival Analysis)</h3>
              <button @click="runSurvivalAnalysis" :disabled="isSurvivalLoading" class="mini-run-btn survival-btn">
                {{ isSurvivalLoading ? '计算中...' : '绘制 KM 曲线' }}
              </button>
            </div>
            <div class="block-body">
              <p class="block-desc">基于临床数据 (OS & OS.time) 评估不同分子亚型的预后差异。</p>
              
              <div v-if="survivalResult" class="survival-charts fade-in">
                <div class="alert-box warning" style="margin-bottom: 20px;">
                  ⚠️ <strong>提示：</strong>有 <strong>{{ survivalResult.lost_samples }}</strong> 个已聚类的病人因缺少临床数据，在计算生存曲线时被丢弃。
                </div>
                <div class="p-value-banner" :class="{ 'is-significant': survivalResult.p_value < 0.05 }">
                  <span class="banner-title">Log-Rank P-value:</span>
                  <span class="banner-val">{{ survivalResult.p_value < 0.0001 ? survivalResult.p_value.toExponential(4) : survivalResult.p_value.toFixed(4) }}</span>
                  <span class="banner-tag" v-if="survivalResult.p_value < 0.05">显著差异 ✨</span>
                </div>
                <div class="chart-panel mt-4">
                  <div ref="survivalChartRef" class="echart-wrapper"></div>
                </div>
              </div>
            </div>
          </div>

        </div>

      </div>
    </main>
  </div>
</template>





<style>
body{ /*默认情况下绝大多数浏览器都会给HTML的<body>标签自动加上8px的外边距。所以如果不写这段代码，网页四周就会出现一圈空白*/
  margin: 0;
  padding: 0;
}
</style>

<style scoped>
/* ================== CSS 变量定义 (全局主题) ================== */
.app-container {
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --secondary: #3b82f6;
  --danger: #ef4444;
  --danger-hover: #dc2626;
  --success: #10b981;
  --warning: #f59e0b;
  
  --bg-page: #f8fafc;
  --bg-card: #ffffff;
  --bg-hover: #f1f5f9;
  
  --text-main: #0f172a;
  --text-regular: #334155;
  --text-muted: #64748b;
  
  --border-light: #e2e8f0;
  --border-focus: #93c5fd;
  
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  
  --radius-md: 8px;
  --radius-lg: 12px;

  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--text-main);
  background-color: var(--bg-page);
  min-height: 100vh;
  padding-bottom: 60px;
}

/* ================== 通用动画 ================== */
.fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ================== 导航栏 ================== */
.app-header {
  background-color: var(--bg-card);
  border-bottom: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-content {
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.logo {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.app-nav {
  display: flex;
  gap: 8px;
}
.app-nav button {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 15px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}
.app-nav button:hover {
  background-color: var(--bg-hover);
  color: var(--text-main);
}
.app-nav button.active {
  background-color: #eef2ff;
  color: var(--primary);
}

/* ================== 页面框架 ================== */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
}

.hero-section {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  text-align: center;
}
.hero-content h1 {
  font-size: 3rem;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 16px;
}
.hero-content p {
  font-size: 1.2rem;
  color: var(--text-muted);
  margin-bottom: 32px;
}

.dashboard-header {
  margin: 40px 0 32px 0;
}
.dashboard-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px 0;
}
.dashboard-header p {
  color: var(--text-muted);
  margin: 0;
}

/* ================== 配置网格 (三大栏) ================== */
.config-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 32px;
  align-items: start;
}

.config-card {
  background-color: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-header {
  background-color: var(--bg-page);
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  gap: 10px;
}
.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}
.card-body {
  padding: 20px;
  flex: 1;
}

/* ================== Column 1: 上传组件 ================== */
.upload-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}
.badge.required { background-color: #fee2e2; color: #b91c1c; }
.badge.optional { background-color: #f1f5f9; color: #475569; }

.format-toggles {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}
.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-regular);
  cursor: pointer;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  transition: all 0.2s;
}
.toggle-label:hover { border-color: var(--primary); }
.toggle-label.is-checked { background-color: #eef2ff; border-color: var(--primary); color: var(--primary); font-weight: 500;}
.toggle-label input { display: none; } /* 隐藏原生的丑陋checkbox，靠颜色区分 */

.code-preview {
  background-color: #1e293b;
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 16px;
}
.preview-header {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.code-preview pre {
  margin: 0;
  color: #f8fafc;
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
}

.file-drop-zone {
  position: relative;
  border: 2px dashed var(--border-light);
  border-radius: var(--radius-md);
  background-color: var(--bg-hover);
  transition: all 0.2s;
  text-align: center;
}
.file-drop-zone:hover {
  border-color: var(--primary);
  background-color: #eef2ff;
}
.file-input {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  top: 0; left: 0;
}
.file-label {
  display: flex;
  flex-direction: column;
  padding: 20px;
  pointer-events: none;
}
.upload-icon { font-size: 24px; margin-bottom: 4px; }
.upload-text { font-size: 14px; font-weight: 500; color: var(--text-main); }
.file-label small { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.status-msg {
  margin-top: 8px;
  font-size: 12px;
  padding: 8px;
  border-radius: var(--radius-md);
  word-break: break-all;
  white-space: pre-wrap; /* 👇 【新增】允许识别 \n 并正确换行 */
}
.status-msg.is-error { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.status-msg.is-success { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }

.divider {
  border: none;
  border-top: 1px dashed var(--border-light);
  margin: 24px 0;
}

/* ================== Column 2: 算法选择 ================== */
.test-mode-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  margin-bottom: 24px;
  transition: all 0.3s;
}
.test-mode-switch.is-active {
  background-color: #fef2f2;
  border-color: #fecaca;
}
.switch-container {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}
.switch-container input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #ccc; transition: .4s;
}
.slider:before {
  position: absolute; content: "";
  height: 18px; width: 18px; left: 3px; bottom: 3px;
  background-color: white; transition: .4s;
}
input:checked + .slider { background-color: var(--danger); }
input:checked + .slider:before { transform: translateX(20px); }
.slider.round { border-radius: 24px; }
.slider.round:before { border-radius: 50%; }

.switch-info strong { display: block; font-size: 14px; color: var(--text-main); }
.test-mode-switch.is-active .switch-info strong { color: var(--danger); }
.switch-info span { font-size: 12px; color: var(--text-muted); }

.section-subtitle {
  font-size: 13px; color: var(--text-muted);
  margin: 0 0 12px 0; text-transform: uppercase;
}

.algo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.algo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: all 0.2s;
}
.algo-item:hover { border-color: var(--secondary); background-color: var(--bg-hover); }
.algo-item.is-selected {
  border-color: var(--primary);
  background-color: #eef2ff;
}
.algo-item input { display: none; }
.algo-name { font-size: 14px; font-weight: 500; }
.check-icon { color: var(--primary); font-weight: bold; }

/* ================== Column 3: 参数配置 ================== */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; color: var(--text-muted); min-height: 200px;
}
.empty-icon { font-size: 32px; margin-bottom: 8px; opacity: 0.5; }

.params-container {
  display: flex; flex-direction: column; gap: 20px;
}
.param-group {
  background: var(--bg-hover); padding: 16px; border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}
.param-group.test-params { background: #fff7ed; border-color: #ffedd5; }
.algo-badge {
  margin: 0 0 16px 0; font-size: 14px; color: var(--primary); font-weight: 600;
  border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 8px;
}
.test-params .algo-badge { color: var(--warning); }

.input-field { margin-bottom: 12px; }
.input-field:last-child { margin-bottom: 0; }
.input-field label {
  display: block; font-size: 12px; color: var(--text-regular); margin-bottom: 6px;
}
.input-field input {
  width: 100%; padding: 8px 12px; border: 1px solid var(--border-light);
  border-radius: var(--radius-md); font-size: 13px; color: var(--text-main);
  transition: all 0.2s; box-sizing: border-box;
}
.input-field input:focus {
  outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.alert-box {
  padding: 12px; border-radius: var(--radius-md); font-size: 13px; margin-bottom: 16px;
}
.alert-box.warning { background-color: #fffbeb; color: #b45309; border: 1px solid #fef3c7; }
.alert-box.error { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }


/* ================== 操作按钮区 ================== */
.action-center {
  display: flex; justify-content: center; margin: 40px 0;
}
.run-btn {
  border: none; border-radius: 30px; font-size: 16px; font-weight: 600;
  padding: 16px 40px; cursor: pointer; transition: all 0.3s;
  box-shadow: var(--shadow-md); color: white;
}
.run-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.run-btn:disabled { opacity: 0.6; cursor: not-allowed; box-shadow: none; transform: none; }

.primary-btn { background: linear-gradient(135deg, var(--primary), var(--secondary)); }
.danger-btn { background: linear-gradient(135deg, var(--danger), #f59e0b); }
.mini-run-btn {
  border: none; border-radius: var(--radius-md); font-size: 13px; font-weight: 500;
  padding: 8px 16px; cursor: pointer; transition: all 0.2s; color: white;
}
.mini-run-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-content { display: flex; align-items: center; gap: 8px; }
.spinner {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%; border-top-color: #fff; animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 全局错误 */
.global-error {
  background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c;
  padding: 16px; border-radius: var(--radius-lg); margin-bottom: 32px;
  display: flex; align-items: center; gap: 12px; font-weight: 500;
}

/* ================== 结果展示区块统一样式 ================== */
.results-container {
  display: flex; flex-direction: column; gap: 32px;
}
.result-block {
  background: var(--bg-card); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md); overflow: hidden; border: 1px solid var(--border-light);
}
.block-header {
  padding: 16px 24px; border-bottom: 1px solid var(--border-light);
  display: flex; justify-content: space-between; align-items: center;
}
.block-header h3 { margin: 0; font-size: 18px; display: flex; align-items: center; gap: 12px; }
.step-num {
  background: var(--text-main); color: white; width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px; font-size: 14px; font-weight: bold;
}
.block-body { padding: 24px; }
.block-desc { color: var(--text-muted); font-size: 14px; margin: 0 0 20px 0; }

/* 头部特征色 */
.diff-color { background: #faf5ff; border-bottom-color: #e9d5ff; }
.diff-color h3 { color: #7e22ce; }
.diff-color .step-num { background: #7e22ce; }
.diff-btn { background: #9333ea; }

.enrich-color { background: #f0fdf4; border-bottom-color: #bbf7d0; }
.enrich-color h3 { color: #15803d; }
.enrich-color .step-num { background: #15803d; }
.go-btn { background: #059669; }
.kegg-btn { background: #0284c7; }

.survival-color { background: #fffbeb; border-bottom-color: #fde68a; }
.survival-color h3 { color: #b45309; }
.survival-color .step-num { background: #b45309; }
.survival-btn { background: #d97706; }

/* ================== 图表与面板通用容器 ================== */
.chart-panel {
  border: 1px solid var(--border-light); border-radius: var(--radius-lg);
  background: var(--bg-card); overflow: hidden;
}
.mt-4 { margin-top: 24px; }
.chart-toolbar {
  background: var(--bg-hover); padding: 12px 20px;
  border-bottom: 1px solid var(--border-light);
  display: flex; justify-content: space-between; align-items: center;
}
.toolbar-title { font-weight: 600; font-size: 14px; color: var(--text-regular); }
.toolbar-actions { display: flex; gap: 16px; align-items: center; }

.ui-select {
  padding: 6px 32px 6px 12px; border: 1px solid var(--border-light);
  border-radius: var(--radius-md); font-size: 13px; background-color: #fff;
  cursor: pointer; outline: none; transition: border-color 0.2s;
}
.ui-select:focus { border-color: var(--primary); }

.button-group {
  display: inline-flex; border-radius: var(--radius-md); overflow: hidden;
  border: 1px solid var(--border-light);
}
.button-group button {
  background: #fff; border: none; padding: 6px 16px; font-size: 13px;
  color: var(--text-muted); cursor: pointer; border-right: 1px solid var(--border-light);
  transition: all 0.2s;
}
.button-group button:last-child { border-right: none; }
.button-group button:hover { background: var(--bg-hover); }
.button-group button.active { background: var(--primary); color: white; font-weight: 500;}

.echart-wrapper {
  width: 100%; height: 500px; /* 图表基础高度 */
}

/* ================== 特殊组件样式 ================== */
/* KPI 指标卡片 */
.metrics-row {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px;
}
.metric-widget {
  flex: 1; background: var(--bg-page); padding: 20px;
  border-radius: var(--radius-lg); border: 1px solid var(--border-light);
  text-align: center;
}
.mw-title { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;}
.mw-value { font-size: 28px; font-weight: 800; color: var(--primary); margin: 8px 0; }
.mw-desc { font-size: 12px; color: var(--text-regular); }

/* 差异网格 */
.diff-charts-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
}
@media (max-width: 1100px) {
  .diff-charts-grid { grid-template-columns: 1fr; }
}

/* Radio Toggles */
.radio-toggles { display: flex; gap: 16px; }
.radio-label {
  font-size: 13px; color: var(--text-regular); cursor: pointer;
  display: flex; align-items: center; gap: 6px;
}

/* P-value Banner */
.p-value-banner {
  background: var(--bg-hover); padding: 20px; border-radius: var(--radius-md);
  text-align: center; border: 1px solid var(--border-light);
}
.p-value-banner.is-significant { background: #fffbeb; border-color: #fde68a; }
.banner-title { font-size: 16px; color: var(--text-muted); margin-right: 12px;}
.banner-val { font-size: 24px; font-weight: 800; color: var(--text-main); }
.banner-tag { margin-left: 12px; background: #f59e0b; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;}

/* 测试模式最佳参数卡片 */
.best-params-card {
  display: flex; gap: 16px; background: #fff7ed; border: 1px solid #ffedd5;
  padding: 24px; border-radius: var(--radius-lg); margin-bottom: 24px;
}
.bpc-icon { font-size: 32px; }
.bpc-content h4 { margin: 0 0 12px 0; font-size: 18px; color: #9a3412; }
.bpc-details { display: flex; gap: 20px; margin-bottom: 8px; }
.bpc-tag { font-size: 15px; color: #c2410c; }
.bpc-tag.highlight { font-weight: bold; color: var(--danger); }
.bpc-hint { margin: 0; font-size: 13px; color: #fdba74; }

/* ================== 新增：组学文件列表配置样式 ================== */
.mt-3 {
  margin-top: 16px;
}
.file-config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file-config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-hover);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}
.file-name {
  font-size: 13px;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60%;
}
.config-select {
  width: 140px;
  padding: 4px 8px;
}
</style>