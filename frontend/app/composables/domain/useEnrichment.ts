import { runEnrichment } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'

type Database = 'GO' | 'KEGG'

type EnrichmentSlot = {
  database: string
  clusters: number[]
  selected_cluster: number
  bar_svg: string
  bubble_cluster_svg: string
  bubble_gene_svg: string
  n_terms: number
  [key: string]: any
}

const DATABASES: Database[] = ['GO', 'KEGG']

const enrichmentResults = ref<Record<Database, EnrichmentSlot | null>>({ GO: null, KEGG: null })
const isEnrichmentLoading = ref(false)
const selectedEnrichmentCluster = ref(0)
const enrichmentErrorMessage = ref('')

const enrichmentResult = computed<EnrichmentSlot | null>(() =>
  enrichmentResults.value.GO || enrichmentResults.value.KEGG,
)

export function useEnrichment() {
  const { sessionId } = useSession()
  const { diffResult } = useDifferential()
  const { selectedCancerSubtype } = useAlgorithmState()

  async function runEnrichmentAnalysis(options: { silent?: boolean } = {}) {
    if (!diffResult.value || !diffResult.value.clusters) {
      if (!options.silent) alert('请先运行差异分析。')
      return
    }

    isEnrichmentLoading.value = true
    enrichmentResults.value = { GO: null, KEGG: null }
    enrichmentErrorMessage.value = ''

    try {
      const settled = await Promise.allSettled(
        DATABASES.map(db => runEnrichment({ session_id: sessionId.value, database: db, dataset: selectedCancerSubtype.value })),
      )

      const errors: string[] = []
      let firstSelected: number | null = null

      settled.forEach((result, idx) => {
        const db = DATABASES[idx]!
        if (result.status === 'fulfilled') {
          const data = result.value.data
          if (data.status === 'success') {
            enrichmentResults.value[db] = data
            if (firstSelected === null) {
              const clusters = data.clusters || []
              if (clusters.length > 0) firstSelected = data.selected_cluster ?? clusters[0]
            }
          } else {
            errors.push(`${db}: ${data.message}`)
          }
        } else {
          const err = result.reason
          errors.push(`${db}: ${err?.response?.data?.detail || err?.message || 'request failed'}`)
        }
      })

      if (firstSelected !== null) selectedEnrichmentCluster.value = firstSelected

      const anySuccess = enrichmentResults.value.GO || enrichmentResults.value.KEGG
      if (!anySuccess) {
        const msg = '富集分析失败: ' + errors.join('; ')
        enrichmentErrorMessage.value = msg
        if (!options.silent) alert(msg)
      } else if (errors.length > 0) {
        enrichmentErrorMessage.value = errors.join('; ')
      }
    } finally {
      isEnrichmentLoading.value = false
    }
  }

  return {
    enrichmentResult, enrichmentResults, isEnrichmentLoading, enrichmentErrorMessage,
    selectedEnrichmentCluster,
    runEnrichmentAnalysis,
  }
}
