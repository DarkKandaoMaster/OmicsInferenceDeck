<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { isTestMode, psResult } = useAlgorithmState()
const { backendResponse } = useAnalysisActions()

const resultsAreaRef = ref<HTMLElement | null>(null)

// 当结果出现时自动滚动
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
  <div v-if="backendResponse || psResult" ref="resultsAreaRef" class="flex flex-col gap-8 animate-[fadeIn_0.4s_ease-out_forwards]">
    <!-- 测试模式结果 -->
    <ResultsParameterView v-if="isTestMode && psResult" />

    <!-- 常规分析结果 -->
    <template v-if="!isTestMode && backendResponse">
      <ResultsEvaluationMetrics />
      <ResultsClusteringView />
      <ResultsDifferentialView />
      <ResultsEnrichmentView />
      <ResultsSurvivalView />
    </template>
  </div>
</template>

<style>
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
