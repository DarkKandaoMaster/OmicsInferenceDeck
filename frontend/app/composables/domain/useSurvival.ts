import { runSurvival } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useAnalysisLog } from '~/composables/core/useAnalysisLog'
import { useDataState } from '~/composables/domain/useDataState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const survivalResult = ref<any>(null)
const isSurvivalLoading = ref(false)
const survivalErrorMessage = ref('')

export function useSurvival() {
  const { sessionId } = useSession()
  const { clinicalFile, isClinicalUploaded, doUploadClinical } = useDataState()
  const { clusteringDone } = useAnalysisActions()
  const { startStep, finishStep, failStep, appendLog, extractError } = useAnalysisLog()

  async function runSurvivalAnalysis(options: { silent?: boolean, isStale?: () => boolean } = {}) {
    if (!clinicalFile.value) {
      survivalResult.value = null
      survivalErrorMessage.value = ''
      if (!options.silent) alert('请先选择临床数据。')
      return
    }
    if (!clusteringDone.value) {
      if (!options.silent) alert('请先运行聚类分析。')
      return
    }

    if (options.isStale?.()) return

    isSurvivalLoading.value = true
    survivalErrorMessage.value = ''
    survivalResult.value = null
    const step = startStep('正在计算 Log-Rank P 值与 KM 生存曲线…')
    try {
      if (!isClinicalUploaded.value) await doUploadClinical(sessionId.value)
      if (options.isStale?.()) return

      const res = await runSurvival({
        session_id: sessionId.value,
      })
      if (options.isStale?.()) return   // 停止：丢弃结果，不写 result/finishStep

      survivalResult.value = res.data
      finishStep(step, '✅ 生存分析完成')
      // 被排除样本提示：仅在生存真正跑完时追加一次（琥珀色警告行）。
      const lost = res.data?.lost_samples
      appendLog(
        lost
          ? `${lost} clustered samples were excluded because clinical data was missing.`
          : 'No clustered samples were excluded.',
        'warning',
      )
    } catch (error: any) {
      survivalErrorMessage.value = '生存分析失败: ' + (error.response?.data?.detail || error.message)
      failStep(step, '❌ 生存分析失败: ' + extractError(error))
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
