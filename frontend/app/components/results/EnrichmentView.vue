<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { renderEnrichmentBar, renderEnrichmentBubble } from '~/utils/api'

type Database = 'GO' | 'KEGG'

const {
  enrichmentResults, isEnrichmentLoading,
  selectedEnrichmentCluster, selectedGeneCountCluster, enrichmentErrorMessage,
} = useEnrichment()
const { diffResult } = useDifferential()
const { sessionId } = useSession()
const { enabledCharts } = useResultSelection()
const { selectedCancerSubtype } = useAlgorithmState()

const DATABASES: Database[] = ['GO', 'KEGG']

const clusterOptions = computed<number[]>(() => {
  const go = enrichmentResults.value.GO?.clusters || []
  const kegg = enrichmentResults.value.KEGG?.clusters || []
  const set = new Set<number>([...go, ...kegg])
  return Array.from(set).sort((a, b) => a - b)
})

const hasAnyResult = computed(() =>
  !!(enrichmentResults.value.GO || enrichmentResults.value.KEGG),
)

function barDownloadParams(db: Database) {
  return {
    session_id: sessionId.value,
    database: db,
    cluster_id: selectedEnrichmentCluster.value,
    dataset: selectedCancerSubtype.value,
  }
}
function bubbleClusterDownloadParams(db: Database) {
  return {
    session_id: sessionId.value,
    database: db,
    mode: 'combined' as const,
  }
}
function bubbleGeneDownloadParams(db: Database) {
  return {
    session_id: sessionId.value,
    database: db,
    mode: 'by_gene' as const,
    cluster_id: selectedGeneCountCluster.value,
  }
}

async function refreshBar(db: Database) {
  if (!enrichmentResults.value[db]) return
  const res = await renderEnrichmentBar({
    session_id: sessionId.value,
    database: db,
    cluster_id: selectedEnrichmentCluster.value,
    dataset: selectedCancerSubtype.value,
  })
  enrichmentResults.value[db] = { ...enrichmentResults.value[db]!, bar_svg: res.data.svg }
}

async function handleClusterChange() {
  await Promise.all(DATABASES.map(refreshBar))
}

async function refreshBubbleGene(db: Database) {
  if (!enrichmentResults.value[db]) return
  const res = await renderEnrichmentBubble({
    session_id: sessionId.value,
    database: db,
    mode: 'by_gene',
    cluster_id: selectedGeneCountCluster.value,
  })
  enrichmentResults.value[db] = { ...enrichmentResults.value[db]!, bubble_gene_svg: res.data.svg }
}

async function handleGeneCountChange() {
  await Promise.all(DATABASES.map(refreshBubbleGene))
}
</script>

<template>
  <div v-if="diffResult && isEnrichmentLoading" class="result-card col-span-2">
    <div class="p-5 text-sm text-slate-600">Querying GO + KEGG enrichment results...</div>
  </div>

  <div v-if="diffResult && enrichmentErrorMessage && !hasAnyResult" class="result-card col-span-2">
    <div class="p-5 text-sm text-red-700">{{ enrichmentErrorMessage }}</div>
  </div>

  <template v-if="diffResult && hasAnyResult">
    <!-- 1. 柱状图：GO、KEGG -->
    <template v-for="db in DATABASES" :key="`bar-${db}`">
      <div
        v-if="enrichmentResults[db] && (db === 'GO' ? enabledCharts.enrichBarGO : enabledCharts.enrichBarKEGG)"
        class="result-card"
      >
        <div class="result-card-header">
          <div class="result-card-title">Enrichment Bar Plot ({{ db }})</div>
          <div class="flex items-center gap-3">
            <select v-model.number="selectedEnrichmentCluster" @change="handleClusterChange" class="chart-select">
              <option v-for="cid in clusterOptions" :key="cid" :value="cid">Cluster {{ cid }}</option>
            </select>
            <ResultsPlotDownloadButton plot-type="enrichment_bar" :params="barDownloadParams(db)" :filename-prefix="`enrichment_bar_${db}`" :disabled="isEnrichmentLoading" />
          </div>
        </div>
        <div class="svg-chart" v-html="enrichmentResults[db]!.bar_svg" />
      </div>
    </template>

    <!-- 2. 气泡图-Cluster：GO、KEGG -->
    <template v-for="db in DATABASES" :key="`bubble-cluster-${db}`">
      <div
        v-if="enrichmentResults[db] && (db === 'GO' ? enabledCharts.enrichBubbleGO : enabledCharts.enrichBubbleKEGG)"
        class="result-card"
      >
        <div class="result-card-header">
          <div class="result-card-title">Enrichment Bubble Plot - Cluster ({{ db }})</div>
          <ResultsPlotDownloadButton plot-type="enrichment_bubble" :params="bubbleClusterDownloadParams(db)" :filename-prefix="`enrichment_bubble_cluster_${db}`" :disabled="isEnrichmentLoading" />
        </div>
        <div class="svg-chart" v-html="enrichmentResults[db]!.bubble_cluster_svg" />
      </div>
    </template>

    <!-- 3. 气泡图-Gene Count：GO、KEGG -->
    <template v-for="db in DATABASES" :key="`bubble-gene-${db}`">
      <div
        v-if="enrichmentResults[db] && (db === 'GO' ? enabledCharts.enrichBubbleGO : enabledCharts.enrichBubbleKEGG)"
        class="result-card"
      >
        <div class="result-card-header">
          <div class="result-card-title">Enrichment Bubble Plot - Gene Count ({{ db }})</div>
          <div class="flex items-center gap-3">
            <select v-model.number="selectedGeneCountCluster" @change="handleGeneCountChange" class="chart-select">
              <option v-for="cid in clusterOptions" :key="cid" :value="cid">Cluster {{ cid }}</option>
            </select>
            <ResultsPlotDownloadButton plot-type="enrichment_bubble" :params="bubbleGeneDownloadParams(db)" :filename-prefix="`enrichment_bubble_gene_${db}`" :disabled="isEnrichmentLoading" />
          </div>
        </div>
        <div class="svg-chart" v-html="enrichmentResults[db]!.bubble_gene_svg" />
      </div>
    </template>
  </template>
</template>
