<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useSurvival } from '~/composables/domain/useSurvival'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { useDataState } from '~/composables/domain/useDataState'

const { isTestMode, psResult } = useAlgorithmState()
const { isCustomEvalMode, isCustomEvalTestMode } = useDataState()
const { backendResponse } = useAnalysisActions()
const { diffResult } = useDifferential()
const { enrichmentResult } = useEnrichment()
const { survivalResult } = useSurvival()
const { enabledMetrics, enabledCharts } = useResultSelection()

const resultsAreaRef = ref<HTMLElement | null>(null)

const hasAnyMetricsVisible = computed(() => {
  const data = backendResponse.value?.data
  if (!data) return false
  if (enabledMetrics.cluster && data.metrics) return true
  if (enabledMetrics.clinical && data.clinical_metrics) return true
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
  if (enabledCharts.survival && survivalResult.value) return true
  return false
})

const isParameterSensitivity = computed(
  () => isTestMode.value || (isCustomEvalMode.value && isCustomEvalTestMode.value),
)

const hasAnyVisibleResult = computed(() => {
  if (isParameterSensitivity.value) return !!psResult.value
  return hasAnyMetricsVisible.value || hasAnyChartsVisible.value
})

watch(backendResponse, async (val) => {
  if (val) {
    await nextTick()
    resultsAreaRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
})

watch(psResult, async (val) => {
  if (val) {
    await nextTick()
    resultsAreaRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
})
</script>

<template>
  <div v-if="hasAnyVisibleResult" ref="resultsAreaRef" class="animate-[fadeIn_0.4s_ease-out_forwards]">
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
        <ResultsEnrichmentView />
        <ResultsSurvivalView />
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
