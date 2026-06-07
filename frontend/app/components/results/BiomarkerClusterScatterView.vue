<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useBiomarkerScatter } from '~/composables/domain/useBiomarkerScatter'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const { diffResult } = useDifferential()
const { sessionId } = useSession()
const { enabledCharts } = useResultSelection()
const {
  biomarkerSvg, biomarkerGene, selectedBiomarkerCluster,
  renderBiomarkerScatter,
} = useBiomarkerScatter()

const downloadParams = computed(() => ({
  session_id: sessionId.value,
  cluster_id: selectedBiomarkerCluster.value,
}))
</script>

<template>
  <div v-if="diffResult && enabledCharts.biomarkerClusterScatter" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">
        生物标志物簇散点图
        <span v-if="biomarkerGene" class="text-slate-500 font-normal">
          - {{ biomarkerGene }}(cluster{{ selectedBiomarkerCluster }})
        </span>
      </div>
      <div class="flex items-center gap-3">
        <select v-model.number="selectedBiomarkerCluster" @change="renderBiomarkerScatter" class="chart-select">
          <option v-for="cid in diffResult.clusters" :key="cid" :value="cid">Cluster {{ cid }}</option>
        </select>
        <ResultsPlotDownloadButton plot-type="biomarker_cluster_scatter" :params="downloadParams" filename-prefix="biomarker_cluster_scatter" />
      </div>
    </div>
    <div class="svg-chart" v-html="biomarkerSvg" />
  </div>
</template>
