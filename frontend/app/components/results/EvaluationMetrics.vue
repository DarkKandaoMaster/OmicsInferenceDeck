<script setup lang="ts">
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const { backendResponse } = useAnalysisActions()
const { enabledMetrics } = useResultSelection()

const metrics = computed(() => backendResponse.value?.data?.metrics)
const featureMatrixAvailable = computed(
  () => backendResponse.value?.data?.feature_matrix_available,
)
</script>

<template>
  <div v-if="enabledMetrics.cluster && metrics" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200">
      <h3 class="m-0 text-lg font-semibold">聚类内部质量指标</h3>
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

  <div v-else-if="enabledMetrics.cluster && !metrics && featureMatrixAvailable === false" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200">
      <h3 class="m-0 text-lg font-semibold">聚类内部质量指标</h3>
    </div>
    <div class="p-6">
      <div class="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <p class="m-0 leading-relaxed">
          未检测到融合后的特征矩阵，已跳过聚类内部质量指标。如需查看，请在上传结果文件时提供特征矩阵列（位于病人名称、聚类结果之后的数值列）。
        </p>
      </div>
    </div>
  </div>
</template>
