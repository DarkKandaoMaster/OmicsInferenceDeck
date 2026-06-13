<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const { inputReduction, isInputReductionLoading, randomSeed } = useAlgorithmState()
const { backendResponse, switchInputReduction } = useAnalysisActions()
const { sessionId } = useSession()
const { displayedCharts } = useResultSelection()

const inputClusterSvg = computed(() => backendResponse.value?.data?.plots?.input_cluster_scatter || '')
const downloadParams = computed(() => ({
  session_id: sessionId.value,
  reduction: inputReduction.value,
  random_state: randomSeed.value,
}))
</script>

<template>
  <div v-if="displayedCharts.inputClusterScatter && inputClusterSvg" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">聚类前散点图</div>
      <div class="flex items-center gap-3">
        <div class="inline-flex rounded-lg overflow-hidden border border-slate-200">
          <button @click="switchInputReduction('PCA')" :class="inputReduction === 'PCA' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isInputReductionLoading" class="chart-toggle">PCA</button>
          <button @click="switchInputReduction('t-SNE')" :class="inputReduction === 't-SNE' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isInputReductionLoading" class="chart-toggle">t-SNE</button>
          <button @click="switchInputReduction('UMAP')" :class="inputReduction === 'UMAP' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isInputReductionLoading" class="chart-toggle">UMAP</button>
        </div>
        <ResultsPlotDownloadButton plot-type="input_cluster_scatter" :params="downloadParams" filename-prefix="input_cluster_scatter" :disabled="isInputReductionLoading" />
      </div>
    </div>
    <div class="svg-chart" v-html="inputClusterSvg" />
  </div>
</template>
