<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDataState } from '~/composables/domain/useDataState'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { renderDifferentialVolcano } from '~/utils/api'

const {
  diffResult, isDiffLoading, selectedVolcanoCluster,
  selectedDiffOmicsType, diffErrorMessage,
  runDifferentialAnalysis,
} = useDifferential()
const { uploadedOmicsTypes } = useDataState()
const { sessionId } = useSession()
const { runEnrichmentAnalysis } = useEnrichment()

const volcanoDownloadParams = computed(() => ({
  session_id: sessionId.value,
  cluster_id: selectedVolcanoCluster.value,
}))
const heatmapDownloadParams = computed(() => ({
  session_id: sessionId.value,
}))

async function handleVolcanoClusterChange() {
  if (!diffResult.value) return
  const res = await renderDifferentialVolcano({
    session_id: sessionId.value,
    cluster_id: selectedVolcanoCluster.value,
  })
  diffResult.value = { ...diffResult.value, volcano_svg: res.data.svg }
}

async function handleOmicsTypeChange() {
  await runDifferentialAnalysis({ silent: true })
  if (diffResult.value?.clusters) await runEnrichmentAnalysis('GO', { silent: true })
}
</script>

<template>
  <div v-if="isDiffLoading" class="result-card col-span-2">
    <div class="p-5 text-sm text-slate-600">Calculating differential expression results...</div>
  </div>

  <div v-if="diffErrorMessage" class="result-card col-span-2">
    <div class="p-5 text-sm text-red-700">{{ diffErrorMessage }}</div>
  </div>

  <template v-if="diffResult">
    <div class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">Differential Volcano</div>
        <div class="flex items-center gap-3">
          <select v-model="selectedDiffOmicsType" @change="handleOmicsTypeChange" class="chart-select">
            <option value="" disabled>Select omics layer</option>
            <option v-for="type in uploadedOmicsTypes" :key="type" :value="type">{{ type }}</option>
          </select>
          <select v-model.number="selectedVolcanoCluster" @change="handleVolcanoClusterChange" class="chart-select">
            <option v-for="cid in diffResult.clusters" :key="cid" :value="cid">Cluster {{ cid }}</option>
          </select>
          <ResultsPlotDownloadButton plot-type="differential_volcano" :params="volcanoDownloadParams" filename-prefix="differential_volcano" />
        </div>
      </div>
      <div class="svg-chart" v-html="diffResult.volcano_svg" />
    </div>

    <div class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">Differential Heatmap</div>
        <ResultsPlotDownloadButton plot-type="differential_heatmap" :params="heatmapDownloadParams" filename-prefix="differential_heatmap" />
      </div>
      <div class="svg-chart" v-html="diffResult.heatmap_svg" />
    </div>
  </template>
</template>
