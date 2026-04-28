<script setup lang="ts">
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { backendResponse } = useAnalysisActions()

const clinicalMetrics = computed(() => backendResponse.value?.data?.clinical_metrics)
const lrt = computed(() => clinicalMetrics.value?.lrt || {})
const ecp = computed(() => clinicalMetrics.value?.ecp || {})
const ecpRows = computed(() => (ecp.value?.results || []).slice(0, 8))

function formatPValue(value: unknown) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 'N/A'
  if (numberValue > 0 && numberValue < 0.0001) return numberValue.toExponential(2)
  return numberValue.toFixed(4)
}

function formatType(value: string) {
  return value === 'discrete' ? 'Discrete' : 'Numerical'
}
</script>

<template>
  <div v-if="clinicalMetrics" class="result-card mt-8">
    <div class="result-card-header">
      <div class="result-card-title">临床指标评估（LRT / ECP）</div>
    </div>

    <div v-if="clinicalMetrics.error" class="p-5 text-sm text-red-700">
      {{ clinicalMetrics.error }}
    </div>

    <div v-else class="p-6">
      <div class="grid grid-cols-3 gap-5 max-[900px]:grid-cols-2 max-[560px]:grid-cols-1">
        <div class="metric-card">
          <div class="metric-label">Log-Rank Test P-value</div>
          <div class="metric-value">{{ formatPValue(lrt.p_value) }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">ECP Significant Parameters</div>
          <div class="metric-value">{{ ecp.significant_count ?? 0 }} / {{ ecp.total_parameters ?? 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">ECP Min P-value</div>
          <div class="metric-value">{{ formatPValue(ecp.min_p_value) }}</div>
        </div>
      </div>

      <div v-if="ecpRows.length" class="mt-6 overflow-x-auto border border-slate-200 rounded-lg">
        <table class="w-full min-w-[620px] border-collapse text-sm">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 text-left font-semibold">Parameter</th>
              <th class="px-4 py-3 text-left font-semibold">Type</th>
              <th class="px-4 py-3 text-left font-semibold">Test</th>
              <th class="px-4 py-3 text-left font-semibold">P-value</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in ecpRows" :key="row.variable" class="border-t border-slate-200">
              <td class="px-4 py-3 text-slate-800">{{ row.label || row.variable }}</td>
              <td class="px-4 py-3 text-slate-600">{{ formatType(row.parameter_type) }}</td>
              <td class="px-4 py-3 text-slate-600">{{ row.test }}</td>
              <td class="px-4 py-3 font-semibold text-slate-900">{{ formatPValue(row.p_value) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
