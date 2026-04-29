import { v4 as uuidv4 } from 'uuid'
import { uploadOmics, uploadClinical, uploadExpressionMatrix } from '~/utils/api'

// =================== 组学数据状态 ===================
const omicsFileConfigs = ref<Array<{ id: string; file: File; originalName: string; type: string }>>([])
const omicsTypes = ['CopyNumber', 'Methylation', 'miRNA', 'mRNA', 'Proteomics', 'RPPA', 'Unknown']
const isOmicsUploaded = ref(false)
const uploadStatus = ref('')

// =================== 临床数据状态 ===================
const clinicalFile = ref<File | null>(null)
const isClinicalUploaded = ref(false)
const clinicalUploadStatus = ref('')

// =================== mRNA 表达矩阵状态 ===================
const expressionMatrixFile = ref<File | null>(null)
const isExpressionMatrixUploaded = ref(false)
const expressionMatrixUploadStatus = ref('')

// =================== 自定义评估模式 ===================
const isCustomEvalMode = ref(false)
const customEvalFile = ref<File | null>(null)
const customEvalUploadStatus = ref('')

// =================== 组学数据格式 ===================
const omicsIsRowSample = ref(true)
const omicsHasHeader = ref(true)
const omicsHasIndex = ref(true)

// =================== 临床数据格式 ===================
const clinicalIsRowSample = ref(false)
const clinicalHasHeader = ref(true)
const clinicalHasIndex = ref(true)

// =================== mRNA 表达矩阵格式 ===================
const expressionMatrixIsRowSample = ref(true)
const expressionMatrixHasHeader = ref(true)
const expressionMatrixHasIndex = ref(true)

// =================== Computed ===================
const dataFormat = computed(() => {
  const p1 = omicsIsRowSample.value ? 'row_feature' : 'row_sample'
  const p2 = omicsHasHeader.value ? 'yes' : 'no'
  const p3 = omicsHasIndex.value ? 'yes' : 'no'
  return `${p1}_${p2}_${p3}`
})

const clinicalDataFormat = computed(() => {
  const p1 = clinicalIsRowSample.value ? 'row_feature' : 'row_sample'
  const p2 = clinicalHasHeader.value ? 'yes' : 'no'
  const p3 = clinicalHasIndex.value ? 'yes' : 'no'
  return `${p1}_${p2}_${p3}`
})

const expressionMatrixDataFormat = computed(() => {
  const p1 = expressionMatrixIsRowSample.value ? 'row_feature' : 'row_sample'
  const p2 = expressionMatrixHasHeader.value ? 'yes' : 'no'
  const p3 = expressionMatrixHasIndex.value ? 'yes' : 'no'
  return `${p1}_${p2}_${p3}`
})

const exampleText = computed(() => {
  switch (dataFormat.value) {
    case 'row_sample_yes_yes': return `,特征1,特征2,特征3,...\n病人1,11,12,13\n病人2,21,22,23\n病人3,31,32,33\n...`
    case 'row_sample_yes_no': return `特征1,特征2,特征3,...\n11,12,13\n21,22,23\n31,32,33\n...`
    case 'row_sample_no_yes': return `病人1,11,12,13,...\n病人2,21,22,23\n病人3,31,32,33\n...`
    case 'row_sample_no_no': return `11,12,13,...\n21,22,23\n31,32,33\n...`
    case 'row_feature_yes_yes': return `,病人1,病人2,病人3,...\n特征1,11,21,31\n特征2,12,22,32\n特征3,13,23,33\n...`
    case 'row_feature_yes_no': return `病人1,病人2,病人3,...\n11,21,31\n12,22,32\n13,23,33\n...`
    case 'row_feature_no_yes': return `特征1,11,21,31,...\n特征2,12,22,32\n特征3,13,23,33\n...`
    case 'row_feature_no_no': return `11,21,31,...\n12,22,32\n13,23,33\n...`
    default: return ''
  }
})

const clinicalExampleText = computed(() => {
  switch (clinicalDataFormat.value) {
    case 'row_sample_yes_yes': return `,OS,OS.time,特征3,...\n病人1,1,20,55\n病人2,0,45,60\n病人3,1,12,62\n...`
    case 'row_sample_yes_no': return `OS,OS.time,特征3,...\n1,20,55\n0,45,60\n1,12,62\n...`
    case 'row_sample_no_yes': return `病人1,1,20,55,...\n病人2,0,45,60\n病人3,1,12,62\n...`
    case 'row_sample_no_no': return `1,20,55,...\n0,45,60\n1,12,62\n...`
    case 'row_feature_yes_yes': return `,病人1,病人2,病人3,...\nOS,1,0,1\nOS.time,20,45,12\n特征3,55,60,62\n...`
    case 'row_feature_yes_no': return `病人1,病人2,病人3,...\n1,0,1\n20,45,12\n55,60,62\n...`
    case 'row_feature_no_yes': return `OS,1,0,1,...\nOS.time,20,45,12\n特征3,55,60,62\n...`
    case 'row_feature_no_no': return `1,0,1,...\n20,45,12\n55,60,62\n...`
    default: return ''
  }
})

/** 当前已上传文件对应的组学类型列表（去重 + 可选拼接 All） */
const expressionMatrixExampleText = computed(() => {
  switch (expressionMatrixDataFormat.value) {
    case 'row_sample_yes_yes': return `,GeneA,GeneB,GeneC,...\nTCGA-XX-0001-01A,11,12,13\nTCGA-XX-0001-11A,21,22,23\nTCGA-XX-0002-01A,31,32,33\n...`
    case 'row_sample_yes_no': return `GeneA,GeneB,GeneC,...\n11,12,13\n21,22,23\n31,32,33\n...`
    case 'row_sample_no_yes': return `TCGA-XX-0001-01A,11,12,13,...\nTCGA-XX-0001-11A,21,22,23\nTCGA-XX-0002-01A,31,32,33\n...`
    case 'row_sample_no_no': return `11,12,13,...\n21,22,23\n31,32,33\n...`
    case 'row_feature_yes_yes': return `id\tTCGA-XX-0001-01A\tTCGA-XX-0001-11A\tTCGA-XX-0002-01A\nGeneA\t11\t21\t31\nGeneB\t12\t22\t32\nGeneC\t13\t23\t33\n...`
    case 'row_feature_yes_no': return `TCGA-XX-0001-01A\tTCGA-XX-0001-11A\tTCGA-XX-0002-01A\n11\t21\t31\n12\t22\t32\n13\t23\t33\n...`
    case 'row_feature_no_yes': return `GeneA\t11\t21\t31\nGeneB\t12\t22\t32\nGeneC\t13\t23\t33\n...`
    case 'row_feature_no_no': return `11\t21\t31\n12\t22\t32\n13\t23\t33\n...`
    default: return ''
  }
})

const uploadedOmicsTypes = computed(() => {
  if (!omicsFileConfigs.value || omicsFileConfigs.value.length === 0) return []
  const types = [...new Set(omicsFileConfigs.value.map(c => c.type))]
  if (types.length > 1) types.push('All (Concatenated)')
  return types
})

const expressionMatrixType = 'mRNA Expression Matrix'

const differentialOmicsTypes = computed(() => {
  const types = [...uploadedOmicsTypes.value]
  if (expressionMatrixFile.value || isExpressionMatrixUploaded.value) {
    return [expressionMatrixType, ...types]
  }
  return types
})

export function useDataState() {
  // ---- 组学数据操作 ----

  /** 上传组学数据到后端 */
  async function doUploadOmics(sessionId: string) {
    if (omicsFileConfigs.value.length === 0) return

    const formData = new FormData()
    const mapping: Record<string, string> = {}
    for (const config of omicsFileConfigs.value) {
      formData.append('files', config.file, config.id)
      mapping[config.id] = config.type
    }
    formData.append('omics_mapping', JSON.stringify(mapping))
    formData.append('data_format', dataFormat.value)
    formData.append('file_type', 'omics')
    formData.append('session_id', sessionId)

    uploadStatus.value = '正在上传组学数据...'
    try {
      const res = await uploadOmics(formData)
      uploadStatus.value = `✅ 组学数据就绪: ${omicsFileConfigs.value.map(c => c.originalName).join(' + ')}\n⚠️ 提示：这些数据有 ${res.data.lost_samples} 个病人无法对齐，计算时会忽略这些病人`
      isOmicsUploaded.value = true
    } catch (error: any) {
      uploadStatus.value = `❌ 数据不合规: ${error.response?.data?.detail || '上传失败'}`
      isOmicsUploaded.value = false
      throw error
    }
  }

  /** 上传临床数据到后端 */
  async function doUploadClinical(sessionId: string) {
    if (!clinicalFile.value) return

    const formData = new FormData()
    formData.append('files', clinicalFile.value)
    formData.append('data_format', clinicalDataFormat.value)
    formData.append('file_type', 'clinical')
    formData.append('session_id', sessionId)

    clinicalUploadStatus.value = '正在上传临床数据...'
    try {
      const res = await uploadClinical(formData)
      clinicalUploadStatus.value = `✅ 临床数据就绪: ${res.data.original_filename}`
      isClinicalUploaded.value = true
    } catch (error: any) {
      clinicalUploadStatus.value = `❌ 错误: ${error.response?.data?.detail || '上传失败'}`
      isClinicalUploaded.value = false
      throw error
    }
  }

  /** 处理组学文件选择 */
  async function doUploadExpressionMatrix(sessionId: string) {
    if (!expressionMatrixFile.value) return

    const formData = new FormData()
    formData.append('file', expressionMatrixFile.value)
    formData.append('data_format', expressionMatrixDataFormat.value)
    formData.append('session_id', sessionId)

    expressionMatrixUploadStatus.value = '正在上传 mRNA 表达矩阵...'
    try {
      const res = await uploadExpressionMatrix(formData)
      expressionMatrixUploadStatus.value = `mRNA 表达矩阵已就绪: ${res.data.original_filename}\n${res.data.n_samples} 个样本，${res.data.n_features} 个基因`
      isExpressionMatrixUploaded.value = true
    } catch (error: any) {
      expressionMatrixUploadStatus.value = `mRNA 表达矩阵错误: ${error.response?.data?.detail || '上传失败'}`
      isExpressionMatrixUploaded.value = false
      throw error
    }
  }

  function handleFileChange(event: Event) {
    const files = Array.from((event.target as HTMLInputElement).files || [])
    if (files.length > 0) {
      omicsFileConfigs.value = files.map(f => ({
        id: uuidv4(),
        file: f,
        originalName: f.name,
        type: 'Unknown',
      }))
      uploadStatus.value = '文件已选择，将在运行时自动上传。'
      isOmicsUploaded.value = false
    } else {
      omicsFileConfigs.value = []
      uploadStatus.value = ''
    }
  }

  /** 组学格式变更标记 */
  function handleFormatChange() {
    if (omicsFileConfigs.value.length > 0) {
      uploadStatus.value = '格式已变更，将在运行时重新校验数据。'
      isOmicsUploaded.value = false
    }
  }

  /** 处理临床文件选择 */
  function handleExpressionMatrixFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (file) {
      expressionMatrixFile.value = file
      expressionMatrixUploadStatus.value = 'mRNA 表达矩阵已选择，将在运行分析时自动上传。'
      isExpressionMatrixUploaded.value = false
    } else {
      expressionMatrixFile.value = null
      expressionMatrixUploadStatus.value = ''
      isExpressionMatrixUploaded.value = false
    }
  }

  function handleExpressionMatrixFormatChange() {
    if (expressionMatrixFile.value) {
      expressionMatrixUploadStatus.value = 'mRNA 表达矩阵格式已变更，将在运行分析时重新解析。'
      isExpressionMatrixUploaded.value = false
    }
  }

  function handleClinicalFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (file) {
      clinicalFile.value = file
      clinicalUploadStatus.value = '文件已选择，将在运行时自动上传。'
      isClinicalUploaded.value = false
    }
  }

  /** 临床格式变更标记 */
  function handleClinicalFormatChange() {
    if (clinicalFile.value) {
      clinicalUploadStatus.value = '临床格式已变更，将在运行时重新解析。'
      isClinicalUploaded.value = false
    }
  }

  /** 处理自定义评估文件选择 */
  function handleCustomEvalFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (file) {
      customEvalFile.value = file
      customEvalUploadStatus.value = '结果文件已选择，将在运行时自动提交评估。'
    } else {
      customEvalFile.value = null
      customEvalUploadStatus.value = ''
    }
  }

  return {
    // 组学状态
    omicsFileConfigs, omicsTypes, isOmicsUploaded, uploadStatus,
    // 临床状态
    clinicalFile, isClinicalUploaded, clinicalUploadStatus,
    expressionMatrixFile, isExpressionMatrixUploaded, expressionMatrixUploadStatus,
    // 自定义评估
    isCustomEvalMode, customEvalFile, customEvalUploadStatus,
    // 格式状态
    omicsIsRowSample, omicsHasHeader, omicsHasIndex,
    clinicalIsRowSample, clinicalHasHeader, clinicalHasIndex,
    expressionMatrixIsRowSample, expressionMatrixHasHeader, expressionMatrixHasIndex,
    // 计算属性
    dataFormat, clinicalDataFormat, expressionMatrixDataFormat,
    exampleText, clinicalExampleText, expressionMatrixExampleText,
    uploadedOmicsTypes, expressionMatrixType, differentialOmicsTypes,
    // 操作
    doUploadOmics, doUploadClinical, doUploadExpressionMatrix,
    handleFileChange, handleFormatChange,
    handleExpressionMatrixFileChange, handleExpressionMatrixFormatChange,
    handleClinicalFileChange, handleClinicalFormatChange,
    handleCustomEvalFileChange,
  }
}
