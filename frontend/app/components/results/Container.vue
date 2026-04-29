<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { isTestMode, psResult } = useAlgorithmState()
const { backendResponse } = useAnalysisActions()

const resultsAreaRef = ref<HTMLElement | null>(null)

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
  <div v-if="backendResponse || psResult" ref="resultsAreaRef" class="animate-[fadeIn_0.4s_ease-out_forwards]">
    <div v-if="isTestMode && psResult" class="results-grid">
      <ResultsParameterView />
    </div>

    <template v-if="!isTestMode && backendResponse">
      <ResultsEvaluationMetrics />
      <ResultsClinicalMetrics />
      <ResultsBiologyMetrics />
      <ResultsAwaMetrics />
      <div class="results-grid mt-8">
        <ResultsClusteringView />
        <ResultsDifferentialView />
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
