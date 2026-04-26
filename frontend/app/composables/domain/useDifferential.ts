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
  const { omicsFileConfigs, uploadedOmicsTypes } = useDataState()
  const { backendResponse } = useAnalysisActions()

  async function runDifferentialAnalysis(options: { silent?: boolean } = {}) {
    if (omicsFileConfigs.value.length === 0 || !backendResponse.value?.data?.plot_data) {
      if (!options.silent) alert('请先完成 [2. 算法选择] 和 [3. 运行分析] 得到聚类结果！')
      return
    }

    if (!selectedDiffOmicsType.value) {
      if (uploadedOmicsTypes.value.length > 0) {
        selectedDiffOmicsType.value = uploadedOmicsTypes.value[0]!
      } else {
        if (!options.silent) alert('无可用的组学数据类型！')
        return
      }
    }

    isDiffLoading.value = true
    diffErrorMessage.value = ''
    diffResult.value = null

    try {
      const plotData = backendResponse.value.data.plot_data
      const sampleNames = plotData.map((item: any) => item.name)
      const clusterLabels = plotData.map((item: any) => item.cluster)

      const res = await runDifferential({
        session_id: sessionId.value,
        omics_type: selectedDiffOmicsType.value,
        sample: sampleNames,
        labels: clusterLabels,
      })

      diffResult.value = res.data
      const clusters = Object.keys(res.data.volcano_data).map(Number)
      if (clusters.length > 0) selectedVolcanoCluster.value = clusters[0] as number
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
