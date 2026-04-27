<script setup lang="ts">
import { useUIState } from '~/composables/core/useUIState'
import { useSession } from '~/composables/core/useSession'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { isLoading } = useUIState()
const { currentReduction, randomSeed } = useAlgorithmState()
const { backendResponse, switchReduction } = useAnalysisActions()
const { sessionId } = useSession()

const clusterSvg = computed(() => backendResponse.value?.data?.plots?.cluster_scatter || '')
const downloadParams = computed(() => ({
  session_id: sessionId.value,
  reduction: currentReduction.value,
  random_state: randomSeed.value,
}))
</script>

<template>
  <div v-if="clusterSvg" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">Cluster Scatter</div>
      <div class="flex items-center gap-3">
        <div class="inline-flex rounded-lg overflow-hidden border border-slate-200">
          <button @click="switchReduction('PCA')" :class="currentReduction === 'PCA' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isLoading" class="chart-toggle">PCA</button>
          <button @click="switchReduction('t-SNE')" :class="currentReduction === 't-SNE' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isLoading" class="chart-toggle">t-SNE</button>
          <button @click="switchReduction('UMAP')" :class="currentReduction === 'UMAP' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isLoading" class="chart-toggle">UMAP</button>
        </div>
        <ResultsPlotDownloadButton plot-type="cluster_scatter" :params="downloadParams" filename-prefix="cluster_scatter" :disabled="isLoading" />
      </div>
    </div>
    <div class="svg-chart" v-html="clusterSvg" />
  </div>
</template>
