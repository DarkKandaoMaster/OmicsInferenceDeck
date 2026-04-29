import { runDifferential } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useDataState } from '~/composables/domain/useDataState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const diffResult = ref<any>(null)
const isDiffLoading = ref(false)
const selectedVolcanoCluster = ref(0)
const selectedDiffOmicsType = ref('')
const diffErrorMessage = ref('')

export function useDifferential() {
  const { sessionId } = useSession()
  const { omicsFileConfigs, differentialOmicsTypes, expressionMatrixType, isExpressionMatrixUploaded } = useDataState()
  const { backendResponse } = useAnalysisActions()

  async function runDifferentialAnalysis(options: { silent?: boolean } = {}) {
    const hasDifferentialInput = omicsFileConfigs.value.length > 0 || isExpressionMatrixUploaded.value
    if (!hasDifferentialInput || !backendResponse.value?.data?.metrics) {
      if (!options.silent) alert('请先完成算法分析，得到聚类结果。')
      return
    }

    if (!selectedDiffOmicsType.value) {
      if (differentialOmicsTypes.value.length > 0) {
        selectedDiffOmicsType.value = isExpressionMatrixUploaded.value
          ? expressionMatrixType
          : differentialOmicsTypes.value[0]!
      } else {
        if (!options.silent) alert('没有可用的组学数据类型。')
        return
      }
    } else if (!differentialOmicsTypes.value.includes(selectedDiffOmicsType.value)) {
      selectedDiffOmicsType.value = isExpressionMatrixUploaded.value
        ? expressionMatrixType
        : (differentialOmicsTypes.value[0] || '')
    }

    isDiffLoading.value = true
    diffErrorMessage.value = ''
    diffResult.value = null

    try {
      const res = await runDifferential({
        session_id: sessionId.value,
        omics_type: selectedDiffOmicsType.value,
      })

      diffResult.value = res.data
      const clusters = res.data.clusters || []
      if (clusters.length > 0) selectedVolcanoCluster.value = res.data.selected_cluster ?? clusters[0]
    } catch (error: any) {
      diffErrorMessage.value = '分析失败: ' + (error.response?.data?.detail || error.message)
    } finally {
      isDiffLoading.value = false
    }
  }

  return {
    diffResult, isDiffLoading, selectedVolcanoCluster,
    selectedDiffOmicsType, diffErrorMessage,
    runDifferentialAnalysis,
  }
}
