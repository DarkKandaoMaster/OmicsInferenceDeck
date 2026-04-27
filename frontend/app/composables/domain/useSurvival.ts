import { runSurvival } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useDataState } from '~/composables/domain/useDataState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const survivalResult = ref<any>(null)
const isSurvivalLoading = ref(false)
const survivalErrorMessage = ref('')

export function useSurvival() {
  const { sessionId } = useSession()
  const { clinicalFile, isClinicalUploaded, doUploadClinical } = useDataState()
  const { backendResponse } = useAnalysisActions()

  async function runSurvivalAnalysis(options: { silent?: boolean } = {}) {
    if (!clinicalFile.value) {
      survivalResult.value = null
      survivalErrorMessage.value = ''
      if (!options.silent) alert('请先选择临床数据。')
      return
    }
    if (!backendResponse.value || !backendResponse.value.data.metrics) {
      if (!options.silent) alert('请先运行聚类分析。')
      return
    }

    isSurvivalLoading.value = true
    survivalErrorMessage.value = ''
    survivalResult.value = null
    try {
      if (!isClinicalUploaded.value) await doUploadClinical(sessionId.value)

      const res = await runSurvival({
        session_id: sessionId.value,
      })

      survivalResult.value = res.data
    } catch (error: any) {
      survivalErrorMessage.value = '生存分析失败: ' + (error.response?.data?.detail || error.message)
      if (!options.silent) alert(survivalErrorMessage.value)
    } finally {
      isSurvivalLoading.value = false
    }
  }

  return {
    survivalResult, isSurvivalLoading, survivalErrorMessage,
    runSurvivalAnalysis,
  }
}
