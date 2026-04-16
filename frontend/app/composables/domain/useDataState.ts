import { v4 as uuidv4 } from 'uuid'
import { uploadOmics, uploadClinical } from '~/utils/api'

// =================== 组学数据状态 ===================
const omicsFileConfigs = ref<Array<{ id: string; file: File; originalName: string; type: string }>>([])
const omicsTypes = ['CopyNumber', 'Methylation', 'miRNA', 'mRNA', 'Proteomics', 'RPPA', 'Unknown']
const isOmicsUploaded = ref(false)
const uploadStatus = ref('')

// =================== 临床数据状态 ===================
const clinicalFile = ref<File | null>(null)
const isClinicalUploaded = ref(false)
const clinicalUploadStatus = ref('')

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
const uploadedOmicsTypes = computed(() => {
  if (!omicsFileConfigs.value || omicsFileConfigs.value.length === 0) return []
  const types = [...new Set(omicsFileConfigs.value.map(c => c.type))]
  if (types.length > 1) types.push('All (Concatenated)')
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
    // 自定义评估
    isCustomEvalMode, customEvalFile, customEvalUploadStatus,
    // 格式状态
    omicsIsRowSample, omicsHasHeader, omicsHasIndex,
    clinicalIsRowSample, clinicalHasHeader, clinicalHasIndex,
    // 计算属性
    dataFormat, clinicalDataFormat, exampleText, clinicalExampleText,
    uploadedOmicsTypes,
    // 操作
    doUploadOmics, doUploadClinical,
    handleFileChange, handleFormatChange,
    handleClinicalFileChange, handleClinicalFormatChange,
    handleCustomEvalFileChange,
  }
}
