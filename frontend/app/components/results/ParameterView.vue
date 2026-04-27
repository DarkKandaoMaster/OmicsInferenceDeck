<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { renderParameterSurface } from '~/utils/api'

const { sessionId } = useSession()
const { psResult, psParam1, psParam2 } = useAlgorithmState()

const paramNames = computed(() => psResult.value?.param_names || [])
const downloadParams = computed(() => ({
  session_id: sessionId.value,
  x_param: psParam1.value,
  y_param: psParam2.value || undefined,
}))

async function updateParameterPlot() {
  if (!psResult.value || !psParam1.value) return
  const res = await renderParameterSurface({
    session_id: sessionId.value,
    x_param: psParam1.value,
    y_param: psParam2.value || undefined,
  })
  psResult.value = { ...psResult.value, plot_svg: res.data.svg, x_param: psParam1.value, y_param: psParam2.value }
}

watch([psParam1, psParam2], () => {
  if (psResult.value) updateParameterPlot()
})
</script>

<template>
  <div v-if="psResult" class="result-card col-span-2">
    <div class="result-card-header">
      <div>
        <div class="result-card-title">Parameter Sensitivity</div>
        <div class="mt-1 text-sm text-slate-600">
          Best parameters: <span class="font-bold text-slate-900">{{ psResult.best_params }}</span>
          <span class="ml-4">-Log10(P): <span class="font-bold text-red-600">{{ psResult.best_score.toFixed(4) }}</span></span>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <label class="text-xs text-slate-500">X</label>
        <select v-model="psParam1" class="chart-select">
          <option v-for="name in paramNames" :key="name" :value="name">{{ name }}</option>
        </select>
        <label class="text-xs text-slate-500">Y</label>
        <select v-model="psParam2" class="chart-select">
          <option value="">2D curve</option>
          <option v-for="name in paramNames" :key="name" :value="name">{{ name }}</option>
        </select>
        <ResultsPlotDownloadButton plot-type="parameter_surface" :params="downloadParams" filename-prefix="parameter_surface" />
      </div>
    </div>
    <div class="svg-chart" v-html="psResult.plot_svg" />
  </div>
</template>
