<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { renderEnrichmentBar, renderEnrichmentBubble } from '~/utils/api'

const {
  enrichmentResult, isEnrichmentLoading, enrichmentType,
  selectedEnrichmentCluster, bubbleChartMode, enrichmentErrorMessage,
  runEnrichmentAnalysis,
} = useEnrichment()
const { diffResult } = useDifferential()
const { sessionId } = useSession()

const activeDatabase = computed(() => enrichmentResult.value?.database || enrichmentType.value || 'GO')
const barDownloadParams = computed(() => ({
  session_id: sessionId.value,
  database: activeDatabase.value,
  cluster_id: selectedEnrichmentCluster.value,
}))
const bubbleDownloadParams = computed(() => ({
  session_id: sessionId.value,
  database: activeDatabase.value,
  mode: bubbleChartMode.value,
}))

async function handleEnrichmentTypeChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  await runEnrichmentAnalysis(value, { silent: true })
}

async function handleClusterChange() {
  if (!enrichmentResult.value) return
  const res = await renderEnrichmentBar({
    session_id: sessionId.value,
    database: activeDatabase.value,
    cluster_id: selectedEnrichmentCluster.value,
  })
  enrichmentResult.value = { ...enrichmentResult.value, bar_svg: res.data.svg }
}

async function handleBubbleModeChange() {
  if (!enrichmentResult.value) return
  const res = await renderEnrichmentBubble({
    session_id: sessionId.value,
    database: activeDatabase.value,
    mode: bubbleChartMode.value,
  })
  enrichmentResult.value = { ...enrichmentResult.value, bubble_svg: res.data.svg }
}
</script>

<template>
  <div v-if="diffResult && isEnrichmentLoading" class="result-card col-span-2">
    <div class="p-5 text-sm text-slate-600">Querying {{ enrichmentType || 'GO' }} enrichment results...</div>
  </div>

  <div v-if="diffResult && enrichmentErrorMessage" class="result-card col-span-2">
    <div class="p-5 text-sm text-red-700">{{ enrichmentErrorMessage }}</div>
  </div>

  <template v-if="diffResult && enrichmentResult">
    <div class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">Enrichment Bar Plot</div>
        <div class="flex items-center gap-3">
          <select :value="activeDatabase" @change="handleEnrichmentTypeChange" :disabled="isEnrichmentLoading" class="chart-select">
            <option value="GO">GO</option>
            <option value="KEGG">KEGG</option>
          </select>
          <select v-model.number="selectedEnrichmentCluster" @change="handleClusterChange" class="chart-select">
            <option v-for="cid in enrichmentResult.clusters" :key="cid" :value="cid">Cluster {{ cid }}</option>
          </select>
          <ResultsPlotDownloadButton plot-type="enrichment_bar" :params="barDownloadParams" filename-prefix="enrichment_bar" :disabled="isEnrichmentLoading" />
        </div>
      </div>
      <div class="svg-chart" v-html="enrichmentResult.bar_svg" />
    </div>

    <div class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">Enrichment Bubble Plot</div>
        <div class="flex items-center gap-4 text-[13px] text-slate-700">
          <label class="flex items-center gap-1.5">
            <input type="radio" v-model="bubbleChartMode" value="combined" @change="handleBubbleModeChange" />
            Cluster
          </label>
          <label class="flex items-center gap-1.5">
            <input type="radio" v-model="bubbleChartMode" value="by_gene" @change="handleBubbleModeChange" />
            Gene count
          </label>
          <ResultsPlotDownloadButton plot-type="enrichment_bubble" :params="bubbleDownloadParams" filename-prefix="enrichment_bubble" :disabled="isEnrichmentLoading" />
        </div>
      </div>
      <div class="svg-chart" v-html="enrichmentResult.bubble_svg" />
    </div>
  </template>
</template>
