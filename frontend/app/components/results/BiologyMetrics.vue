<script setup lang="ts">
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { backendResponse } = useAnalysisActions()

const biologyMetrics = computed(() => backendResponse.value?.data?.biology_metrics)

function formatNumber(value: unknown, digits = 2) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 'N/A'
  return numberValue.toFixed(digits)
}

function formatPValue(value: unknown) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 'N/A'
  if (numberValue > 0 && numberValue < 0.0001) return numberValue.toExponential(2)
  return numberValue.toFixed(4)
}
</script>

<template>
  <div v-if="biologyMetrics" class="result-card mt-8">
    <div class="result-card-header">
      <div class="result-card-title">生物学机制指标评估</div>
    </div>

    <div v-if="biologyMetrics.error" class="p-5 text-sm text-red-700">
      {{ biologyMetrics.error }}
    </div>

    <div v-else class="p-6">
      <div class="grid grid-cols-3 gap-5 max-[900px]:grid-cols-2 max-[560px]:grid-cols-1">
        <div class="metric-card">
          <div class="metric-label">Significant Pathways</div>
          <div class="metric-value">{{ biologyMetrics.significant_pathway_count ?? 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Core Pathway Score</div>
          <div class="metric-value">{{ formatNumber(biologyMetrics.core_pathway_score) }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Database</div>
          <div class="metric-value">{{ biologyMetrics.database || 'N/A' }}</div>
        </div>
      </div>

      <div v-if="biologyMetrics.core_pathway" class="mt-6 overflow-x-auto border border-slate-200 rounded-lg">
        <table class="w-full min-w-[620px] border-collapse text-sm">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              <th class="px-4 py-3 text-left font-semibold">Core Pathway</th>
              <th class="px-4 py-3 text-left font-semibold">Cluster</th>
              <th class="px-4 py-3 text-left font-semibold">Category</th>
              <th class="px-4 py-3 text-left font-semibold">P-value</th>
              <th class="px-4 py-3 text-left font-semibold">Adjusted P</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-t border-slate-200">
              <td class="px-4 py-3 text-slate-800">{{ biologyMetrics.core_pathway }}</td>
              <td class="px-4 py-3 text-slate-600">{{ biologyMetrics.core_cluster ?? 'N/A' }}</td>
              <td class="px-4 py-3 text-slate-600">{{ biologyMetrics.core_category || 'N/A' }}</td>
              <td class="px-4 py-3 font-semibold text-slate-900">{{ formatPValue(biologyMetrics.core_p_value) }}</td>
              <td class="px-4 py-3 font-semibold text-slate-900">{{ formatPValue(biologyMetrics.core_adjusted_p) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
