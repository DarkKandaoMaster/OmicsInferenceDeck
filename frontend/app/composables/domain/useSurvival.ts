import { runSurvival } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useDataState } from '~/composables/domain/useDataState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const survivalResult = ref<any>(null)
const isSurvivalLoading = ref(false)

export function useSurvival() {
  const { sessionId } = useSession()
  const { clinicalFile, isClinicalUploaded, doUploadClinical } = useDataState()
  const { backendResponse } = useAnalysisActions()

  async function runSurvivalAnalysis() {
    if (!clinicalFile.value) { alert('请先选择临床数据！'); return }
    if (!backendResponse.value || !backendResponse.value.data.plot_data) { alert('请先运行聚类分析！'); return }

    isSurvivalLoading.value = true
    try {
      if (!isClinicalUploaded.value) await doUploadClinical(sessionId.value)

      const plotData = backendResponse.value.data.plot_data
      const sampleNames = plotData.map((item: any) => item.name)
      const clusterLabels = plotData.map((item: any) => item.cluster)

      const res = await runSurvival({
        session_id: sessionId.value,
        sample: sampleNames,
        labels: clusterLabels,
      })

      survivalResult.value = res.data
    } catch (error: any) {
      alert('生存分析失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      isSurvivalLoading.value = false
    }
  }

  return {
    survivalResult, isSurvivalLoading,
    runSurvivalAnalysis,
  }
}
