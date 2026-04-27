import { runEnrichment } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'

const enrichmentResult = ref<any>(null)
const isEnrichmentLoading = ref(false)
const enrichmentType = ref('')
const selectedEnrichmentCluster = ref(0)
const bubbleChartMode = ref<'combined' | 'by_gene'>('combined')
const enrichmentErrorMessage = ref('')

export function useEnrichment() {
  const { sessionId } = useSession()
  const { diffResult } = useDifferential()

  async function runEnrichmentAnalysis(type: string, options: { silent?: boolean } = {}) {
    if (!diffResult.value || !diffResult.value.clusters) {
      if (!options.silent) alert('请先运行差异分析。')
      return
    }

    isEnrichmentLoading.value = true
    enrichmentType.value = type
    enrichmentResult.value = null
    enrichmentErrorMessage.value = ''

    try {
      const res = await runEnrichment({
        session_id: sessionId.value,
        database: type,
      })

      if (res.data.status === 'success') {
        enrichmentResult.value = res.data
        const clusters = res.data.clusters || []
        if (clusters.length > 0) selectedEnrichmentCluster.value = res.data.selected_cluster ?? clusters[0]!
      } else {
        enrichmentErrorMessage.value = res.data.message
        if (!options.silent) alert(res.data.message)
      }
    } catch (error: any) {
      enrichmentErrorMessage.value = '富集分析失败: ' + (error.response?.data?.detail || error.message)
      if (!options.silent) alert(enrichmentErrorMessage.value)
    } finally {
      isEnrichmentLoading.value = false
    }
  }

  return {
    enrichmentResult, isEnrichmentLoading, enrichmentType, enrichmentErrorMessage,
    selectedEnrichmentCluster, bubbleChartMode,
    runEnrichmentAnalysis,
  }
}
