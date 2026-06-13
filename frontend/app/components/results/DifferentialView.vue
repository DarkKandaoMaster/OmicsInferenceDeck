<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useDataState } from '~/composables/domain/useDataState'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { renderDifferentialVolcano } from '~/utils/api'

const {
  diffResult, selectedVolcanoCluster,
  selectedDiffOmicsType,
  runDifferentialAnalysis,
} = useDifferential()
const { displayedDifferentialOmicsTypes } = useDataState()
const { sessionId } = useSession()
const { runEnrichmentAnalysis } = useEnrichment()
const { displayedCharts } = useResultSelection()

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
  // 原地更新而非整体替换 diffResult：替换会改变引用，触发 useBiomarkerScatter 中
  // watch(diffResult) 重绘生物标志物簇散点图（仅切换火山图簇时并不需要）。
  diffResult.value.volcano_svg = res.data.svg
}

async function handleOmicsTypeChange() {
  await runDifferentialAnalysis({ silent: true })
  if (diffResult.value?.clusters) await runEnrichmentAnalysis({ silent: true })
}
</script>

<template>
  <template v-if="diffResult">
    <div v-if="displayedCharts.diffVolcano" class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">差异火山图</div>
        <div class="flex items-center gap-3">
          <!-- 组学层选择下拉已注释：默认跑 mRNA Expression Matrix，逻辑层 runDifferentialAnalysis 会自动兜底默认组学层 -->
          <!-- <select v-model="selectedDiffOmicsType" @change="handleOmicsTypeChange" class="chart-select">
            <option value="" disabled>Select omics layer</option>
            <option v-for="type in displayedDifferentialOmicsTypes" :key="type" :value="type">{{ type }}</option>
          </select> -->
          <select v-model.number="selectedVolcanoCluster" @change="handleVolcanoClusterChange" class="chart-select">
            <option v-for="cid in diffResult.clusters" :key="cid" :value="cid">Cluster {{ cid }}</option>
          </select>
          <ResultsPlotDownloadButton plot-type="differential_volcano" :params="volcanoDownloadParams" filename-prefix="differential_volcano" />
        </div>
      </div>
      <div class="svg-chart" v-html="diffResult.volcano_svg" />
    </div>

    <div v-if="displayedCharts.diffHeatmap" class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">差异热图</div>
        <div class="flex items-center gap-3">
          <select v-if="!displayedCharts.diffVolcano" v-model="selectedDiffOmicsType" @change="handleOmicsTypeChange" class="chart-select">
            <option value="" disabled>Select omics layer</option>
            <option v-for="type in displayedDifferentialOmicsTypes" :key="type" :value="type">{{ type }}</option>
          </select>
          <ResultsPlotDownloadButton plot-type="differential_heatmap" :params="heatmapDownloadParams" filename-prefix="differential_heatmap" />
        </div>
      </div>
      <div class="svg-chart" v-html="diffResult.heatmap_svg" />
    </div>
  </template>
</template>
