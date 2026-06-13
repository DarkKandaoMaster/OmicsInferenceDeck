<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const { predReduction, isPredReductionLoading } = useAlgorithmState()
const { backendResponse, switchPredReduction } = useAnalysisActions()
const { sessionId } = useSession()
const { displayedCharts } = useResultSelection()

const clusterSvg = computed(() => backendResponse.value?.data?.plots?.pred_cluster_scatter || '')
const downloadParams = computed(() => ({
  session_id: sessionId.value,
  reduction: predReduction.value,
}))
</script>

<template>
  <div v-if="displayedCharts.predClusterScatter && clusterSvg" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">聚类后散点图</div>
      <div class="flex items-center gap-3">
        <div class="inline-flex rounded-lg overflow-hidden border border-slate-200">
          <button @click="switchPredReduction('PCA')" :class="predReduction === 'PCA' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isPredReductionLoading" class="chart-toggle">PCA</button>
          <button @click="switchPredReduction('t-SNE')" :class="predReduction === 't-SNE' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isPredReductionLoading" class="chart-toggle">t-SNE</button>
          <button @click="switchPredReduction('UMAP')" :class="predReduction === 'UMAP' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isPredReductionLoading" class="chart-toggle">UMAP</button>
        </div>
        <ResultsPlotDownloadButton plot-type="pred_cluster_scatter" :params="downloadParams" filename-prefix="pred_cluster_scatter" :disabled="isPredReductionLoading" />
      </div>
    </div>
    <div class="svg-chart" v-html="clusterSvg" />
  </div>
</template>
