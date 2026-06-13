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
  selectedEnrichmentCluster, selectedGeneCountCluster,
} = useEnrichment()
const { diffResult } = useDifferential()
const { sessionId } = useSession()
const { displayedCharts } = useResultSelection()
const { displayedCancerSubtype } = useAlgorithmState()

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
    dataset: displayedCancerSubtype.value,
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
    dataset: displayedCancerSubtype.value,
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
  <template v-if="diffResult && hasAnyResult">
    <!-- GO/KEGG条形图 -->
    <template v-for="db in DATABASES" :key="`bar-${db}`">
      <div
        v-if="enrichmentResults[db] && (db === 'GO' ? displayedCharts.enrichBarGO : displayedCharts.enrichBarKEGG)"
        class="result-card"
      >
        <div class="result-card-header">
          <div class="result-card-title">{{ db }}富集分析条形图</div>
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

    <!-- GO/KEGG气泡图 - Cluster -->
    <template v-for="db in DATABASES" :key="`bubble-cluster-${db}`">
      <div
        v-if="enrichmentResults[db] && (db === 'GO' ? displayedCharts.enrichBubbleGO : displayedCharts.enrichBubbleKEGG)"
        class="result-card"
      >
        <div class="result-card-header">
          <div class="result-card-title">{{ db }}富集分析气泡图 - All Clusters</div>
          <ResultsPlotDownloadButton plot-type="enrichment_bubble" :params="bubbleClusterDownloadParams(db)" :filename-prefix="`enrichment_bubble_cluster_${db}`" :disabled="isEnrichmentLoading" />
        </div>
        <div class="svg-chart" v-html="enrichmentResults[db]!.bubble_cluster_svg" />
      </div>
    </template>

    <!-- GO/KEGG气泡图 - Gene Count -->
    <template v-for="db in DATABASES" :key="`bubble-gene-${db}`">
      <div
        v-if="enrichmentResults[db] && (db === 'GO' ? displayedCharts.enrichBubbleGO : displayedCharts.enrichBubbleKEGG)"
        class="result-card"
      >
        <div class="result-card-header">
          <div class="result-card-title">{{ db }}富集分析气泡图 - Gene Count</div>
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
