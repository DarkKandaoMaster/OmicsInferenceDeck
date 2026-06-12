<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { useDataState } from '~/composables/domain/useDataState'

const { isTestMode, psResult } = useAlgorithmState()
const { isCustomEvalMode, isCustomEvalTestMode } = useDataState()
const { backendResponse, resultsVisible } = useAnalysisActions()
const { diffResult } = useDifferential()
const { enrichmentResult } = useEnrichment()
const { enabledMetrics, enabledCharts } = useResultSelection()

const hasAnyMetricsVisible = computed(() => {
  const data = backendResponse.value?.data
  if (!data) return false
  if (enabledMetrics.cluster && data.metrics) return true
  // 临床指标即使没产出，也显示占位卡片，因此勾选即算“可见”
  if (enabledMetrics.clinical) return true
  if (enabledMetrics.biology && data.biology_metrics_by_db) return true
  if (enabledMetrics.awa && data.awa_metrics_by_db) return true
  return false
})

const hasAnyChartsVisible = computed(() => {
  const data = backendResponse.value?.data
  if (!data) return false
  if (enabledCharts.inputClusterScatter && data.plots?.input_cluster_scatter) return true
  if (enabledCharts.predClusterScatter && data.plots?.pred_cluster_scatter) return true
  if ((enabledCharts.diffVolcano || enabledCharts.diffHeatmap) && diffResult.value) return true
  if (enabledCharts.biomarkerClusterScatter && diffResult.value) return true
  if ((enabledCharts.enrichBarGO || enabledCharts.enrichBarKEGG || enabledCharts.enrichBubbleGO || enabledCharts.enrichBubbleKEGG) && diffResult.value && enrichmentResult.value) return true
  // 生存曲线即使没产出，也显示占位卡片，因此勾选即算“可见”
  if (enabledCharts.survival) return true
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
        <ResultsDifferentialView />
        <ResultsBiomarkerClusterScatterView />
        <ResultsSurvivalView />
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
