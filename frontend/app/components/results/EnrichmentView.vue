<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { renderEnrichmentBar, renderEnrichmentBubble } from '~/utils/api'

type Database = 'GO' | 'KEGG'

const {
  enrichmentResults, isEnrichmentLoading,
  selectedEnrichmentCluster, bubbleChartMode, enrichmentErrorMessage,
} = useEnrichment()
const { diffResult } = useDifferential()
const { sessionId } = useSession()
const { enabledCharts } = useResultSelection()

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
  }
}
function bubbleDownloadParams(db: Database) {
  return {
    session_id: sessionId.value,
    database: db,
    mode: bubbleChartMode.value,
  }
}

async function refreshBar(db: Database) {
  if (!enrichmentResults.value[db]) return
  const res = await renderEnrichmentBar({
    session_id: sessionId.value,
    database: db,
    cluster_id: selectedEnrichmentCluster.value,
  })
  enrichmentResults.value[db] = { ...enrichmentResults.value[db]!, bar_svg: res.data.svg }
}

async function refreshBubble(db: Database) {
  if (!enrichmentResults.value[db]) return
  const res = await renderEnrichmentBubble({
    session_id: sessionId.value,
    database: db,
    mode: bubbleChartMode.value,
  })
  enrichmentResults.value[db] = { ...enrichmentResults.value[db]!, bubble_svg: res.data.svg }
}

async function handleClusterChange() {
  await Promise.all(DATABASES.map(refreshBar))
}

async function handleBubbleModeChange() {
  await Promise.all(DATABASES.map(refreshBubble))
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
    <template v-for="db in DATABASES" :key="db">
      <template v-if="enrichmentResults[db]">
        <div v-if="enabledCharts.enrichBar" class="result-card">
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

        <div v-if="enabledCharts.enrichBubble" class="result-card">
          <div class="result-card-header">
            <div class="result-card-title">Enrichment Bubble Plot ({{ db }})</div>
            <div class="flex items-center gap-4 text-[13px] text-slate-700">
              <label class="flex items-center gap-1.5">
                <input type="radio" v-model="bubbleChartMode" value="combined" @change="handleBubbleModeChange" />
                Cluster
              </label>
              <label class="flex items-center gap-1.5">
                <input type="radio" v-model="bubbleChartMode" value="by_gene" @change="handleBubbleModeChange" />
                Gene count
              </label>
              <ResultsPlotDownloadButton plot-type="enrichment_bubble" :params="bubbleDownloadParams(db)" :filename-prefix="`enrichment_bubble_${db}`" :disabled="isEnrichmentLoading" />
            </div>
          </div>
          <div class="svg-chart" v-html="enrichmentResults[db]!.bubble_svg" />
        </div>
      </template>
    </template>
  </template>
</template>
