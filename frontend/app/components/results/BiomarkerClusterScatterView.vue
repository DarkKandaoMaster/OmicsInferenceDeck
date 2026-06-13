<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useBiomarkerScatter } from '~/composables/domain/useBiomarkerScatter'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const { diffResult } = useDifferential()
const { sessionId } = useSession()
const { displayedCharts } = useResultSelection()
const {
  biomarkerSvg, biomarkerGene, selectedBiomarkerCluster, selectedBiomarkerReduction,
  isBiomarkerLoading, renderBiomarkerScatter, switchBiomarkerReduction,
} = useBiomarkerScatter()

const downloadParams = computed(() => ({
  session_id: sessionId.value,
  cluster_id: selectedBiomarkerCluster.value,
  reduction: selectedBiomarkerReduction.value,
}))
</script>

<template>
  <div v-if="diffResult && displayedCharts.biomarkerClusterScatter" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">
        生物标志物簇散点图
      </div>
      <div class="flex items-center gap-3">
        <div class="inline-flex rounded-lg overflow-hidden border border-slate-200">
          <button @click="switchBiomarkerReduction('PCA')" :class="selectedBiomarkerReduction === 'PCA' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isBiomarkerLoading" class="chart-toggle">PCA</button>
          <button @click="switchBiomarkerReduction('t-SNE')" :class="selectedBiomarkerReduction === 't-SNE' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isBiomarkerLoading" class="chart-toggle">t-SNE</button>
          <button @click="switchBiomarkerReduction('UMAP')" :class="selectedBiomarkerReduction === 'UMAP' ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-100'" :disabled="isBiomarkerLoading" class="chart-toggle">UMAP</button>
        </div>
        <select v-model.number="selectedBiomarkerCluster" @change="renderBiomarkerScatter()" class="chart-select" :disabled="isBiomarkerLoading">
          <option v-for="cid in diffResult.clusters" :key="cid" :value="cid">Cluster {{ cid }}</option>
        </select>
        <ResultsPlotDownloadButton plot-type="biomarker_cluster_scatter" :params="downloadParams" filename-prefix="biomarker_cluster_scatter" :disabled="isBiomarkerLoading" />
      </div>
    </div>
    <div class="svg-chart" v-html="biomarkerSvg" />
  </div>
</template>
