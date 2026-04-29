<script setup lang="ts">
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { backendResponse } = useAnalysisActions()

const awaMetrics = computed(() => backendResponse.value?.data?.awa_metrics)
const components = computed(() => awaMetrics.value?.components || {})

const componentRows = computed(() => [
  { key: 'silhouette', label: 'Silhouette' },
  { key: 'calinski_harabasz', label: 'Calinski-Harabasz' },
  { key: 'dunn', label: 'Dunn Index' },
  { key: 'log_rank_test', label: 'Log-Rank Test' },
  { key: 'enriched_clinical_parameters', label: 'ECP' },
  { key: 'significant_pathways', label: 'Significant Pathways' },
  { key: 'core_pathway_score', label: 'Core Pathway Score' },
])

function formatNumber(value: unknown, digits = 2) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 'N/A'
  return numberValue.toFixed(digits)
}
</script>

<template>
  <div v-if="awaMetrics" class="result-card mt-8">
    <div class="result-card-header">
      <div class="result-card-title">综合指标评估（AWA / 3D-AWA）</div>
    </div>

    <div v-if="awaMetrics.error" class="p-5 text-sm text-red-700">
      {{ awaMetrics.error }}
    </div>

    <div v-else class="p-6">
      <div class="grid grid-cols-2 gap-5 max-[560px]:grid-cols-1">
        <div class="metric-card">
          <div class="metric-label">AWA</div>
          <div class="metric-value">{{ formatNumber(awaMetrics.awa) }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">3D-AWA</div>
          <div class="metric-value">{{ formatNumber(awaMetrics.three_d_awa) }}</div>
        </div>
      </div>

      <div class="mt-6 overflow-x-auto border border-slate-200 rounded-lg">
        <table class="w-full min-w-[620px] border-collapse text-sm">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 text-left font-semibold">Component</th>
              <th class="px-4 py-3 text-left font-semibold">Normalized Score</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in componentRows" :key="row.key" class="border-t border-slate-200">
              <td class="px-4 py-3 text-slate-800">{{ row.label }}</td>
              <td class="px-4 py-3 font-semibold text-slate-900">{{ formatNumber(components[row.key]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
