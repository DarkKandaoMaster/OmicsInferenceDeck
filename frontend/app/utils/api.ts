import http from './http'

/** 上传组学/临床数据 */
export function uploadOmics(formData: FormData) {
  return http.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 上传临床数据 (复用同一接口，file_type 区分) */
export function uploadClinical(formData: FormData) {
  return http.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 运行聚类算法 */
export function runAlgorithm(params: {
  algorithm: string
  timestamp: string
  session_id: string
  n_clusters: number
  random_state: number
  max_iter: number
  n_neighbors: number
}) {
  return http.post('/run', params)
}

/** 计算指标 + 降维可视化 */
export function runAnalysis(params: {
  session_id: string
  reduction: string
  random_state: number
}) {
  return http.post('/analysis', params)
}

/** 自定义评估：解析结果文件 */
export function evaluateCustom(formData: FormData) {
  return http.post('/evaluate_custom', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 差异表达分析 */
export function runDifferential(params: {
  session_id: string
  omics_type: string
  sample: string[]
  labels: number[]
}) {
  return http.post('/differential_analysis', params)
}

/** 富集分析 */
export function runEnrichment(params: {
  cluster_genes: Record<string, string[]>
  database: string
}) {
  return http.post('/enrichment_analysis', params)
}

/** 生存分析 */
export function runSurvival(params: {
  session_id: string
  sample: string[]
  labels: number[]
}) {
  return http.post('/survival_analysis', params)
}

/** 参数敏感性搜索 */
export function runParameterSearch(params: {
  algorithm: string
  session_id: string
  param_grid: Record<string, number[]>
  random_state: number
}) {
  return http.post('/parameter_search', params)
}

/** 会话清理 (使用 beacon，不走 axios) */
export function cleanupSession(sessionId: string) {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  navigator.sendBeacon('/api/cleanup', formData)
}
