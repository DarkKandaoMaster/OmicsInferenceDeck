<script setup lang="ts">
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { backendResponse } = useAnalysisActions()

const metrics = computed(() => backendResponse.value?.data?.metrics)
</script>

<template>
  <div v-if="metrics" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200">
      <h3 class="m-0 text-lg font-semibold">聚类效果评估</h3>
    </div>
    <div class="p-6">
      <div class="grid grid-cols-3 gap-5 max-[900px]:grid-cols-2 max-[560px]:grid-cols-1">
        <div class="metric-card">
          <div class="metric-label">Silhouette Score (Sample Avg)</div>
          <div class="metric-value">{{ metrics.silhouette ?? 'N/A' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Silhouette Score (Cluster Avg)</div>
          <div class="metric-value">{{ metrics.silhouette_cluster ?? 'N/A' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Calinski-Harabasz</div>
          <div class="metric-value">{{ metrics.calinski ?? 'N/A' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Davies-Bouldin</div>
          <div class="metric-value">{{ metrics.davies ?? 'N/A' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Dunn Index</div>
          <div class="metric-value">{{ metrics.dunn ?? 'N/A' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Xie-Beni</div>
          <div class="metric-value">{{ metrics.xb ?? 'N/A' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">S_Dbw</div>
          <div class="metric-value">{{ metrics.s_dbw ?? 'N/A' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
