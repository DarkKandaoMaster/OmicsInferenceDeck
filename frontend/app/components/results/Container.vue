<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { useDataState } from '~/composables/domain/useDataState'
import { useSurvival } from '~/composables/domain/useSurvival'

const { isTestMode, psResult } = useAlgorithmState()
const { isCustomEvalMode, isCustomEvalTestMode } = useDataState()
const { backendResponse, resultsVisible } = useAnalysisActions()
const { diffResult } = useDifferential()
const { enrichmentResult } = useEnrichment()
const { survivalResult, survivalErrorMessage } = useSurvival()
const { displayedMetrics, displayedCharts } = useResultSelection()

const hasAnyMetricsVisible = computed(() => {
  const data = backendResponse.value?.data
  if (!data) return false
  if (displayedMetrics.cluster && data.metrics) return true
  // 临床指标：仅当该步已产出数据（成功→图表，失败→{error} 占位）才算“可见”；未跑到则不显示占位
  if (displayedMetrics.clinical && data.clinical_metrics) return true
  if (displayedMetrics.biology && data.biology_metrics_by_db) return true
  if (displayedMetrics.awa && data.awa_metrics_by_db) return true
  return false
})

const hasAnyChartsVisible = computed(() => {
  const data = backendResponse.value?.data
  if (!data) return false
  if (displayedCharts.inputClusterScatter && data.plots?.input_cluster_scatter) return true
  if (displayedCharts.predClusterScatter && data.plots?.pred_cluster_scatter) return true
  if (displayedCharts.survival && (survivalResult || survivalErrorMessage)) return true
  if ((displayedCharts.diffVolcano || displayedCharts.diffHeatmap) && diffResult.value) return true
  if (displayedCharts.biomarkerClusterScatter && diffResult.value) return true
  if ((displayedCharts.enrichBarGO || displayedCharts.enrichBarKEGG || displayedCharts.enrichBubbleGO || displayedCharts.enrichBubbleKEGG) && diffResult.value && enrichmentResult.value) return true
  return false
})

const isParameterSensitivity = computed(
  () => isTestMode.value || (isCustomEvalMode.value && isCustomEvalTestMode.value),
)

const hasAnyVisibleResult = computed(() => {
  if (isParameterSensitivity.value) return !!psResult.value
  return hasAnyMetricsVisible.value || hasAnyChartsVisible.value
})
</script>

<template>
  <div v-if="resultsVisible && hasAnyVisibleResult" class="animate-[fadeIn_0.4s_ease-out_forwards]">
    <div v-if="isParameterSensitivity && psResult" class="results-grid">
      <ResultsParameterView />
    </div>

    <template v-if="!isParameterSensitivity && backendResponse">
      <ResultsEvaluationMetrics />
      <ResultsClinicalMetrics />
      <ResultsBiologyMetrics />
      <ResultsAwaMetrics />
      <div v-if="hasAnyChartsVisible" class="results-grid mt-8">
        <ResultsInputClusteringView />
        <ResultsClusteringView />
        <ResultsSurvivalView />
        <ResultsDifferentialView />
        <ResultsBiomarkerClusterScatterView />
        <ResultsEnrichmentView />
      </div>
    </template>
  </div>
</template>

<style>
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
