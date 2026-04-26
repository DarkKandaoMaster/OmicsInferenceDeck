import { runEnrichment } from '~/utils/api'
import { useDifferential } from '~/composables/domain/useDifferential'

const enrichmentResult = ref<Record<string, any[]> | null>(null)
const isEnrichmentLoading = ref(false)
const enrichmentType = ref('')
const selectedEnrichmentCluster = ref(0)
const bubbleChartMode = ref<'combined' | 'by_gene'>('combined')
const enrichmentErrorMessage = ref('')

export function useEnrichment() {
  const { diffResult } = useDifferential()

  async function runEnrichmentAnalysis(type: string, options: { silent?: boolean } = {}) {
    if (!diffResult.value || !diffResult.value.volcano_data) {
      if (!options.silent) alert('请先运行步骤 4 的差异分析！我们需要差异基因列表才能做富集分析。')
      return
    }

    isEnrichmentLoading.value = true
    enrichmentType.value = type
    enrichmentResult.value = null
    enrichmentErrorMessage.value = ''

    try {
      const clusterGenesDict: Record<string, string[]> = {}

      for (const [clusterId, clusterData] of Object.entries(diffResult.value.volcano_data)) {
        const geneList = (clusterData as any[])
          .filter((item: any) => item.t_pvalue < 0.05 && item.logFC > 0.5)
          .map((item: any) => item.gene)
        clusterGenesDict[clusterId] = geneList
      }

      const res = await runEnrichment({
        cluster_genes: clusterGenesDict,
        database: type,
      })

      if (res.data.status === 'success') {
        enrichmentResult.value = res.data.data
        const clusters = Object.keys(res.data.data).map(Number)
        if (clusters.length > 0) selectedEnrichmentCluster.value = clusters[0]!
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
