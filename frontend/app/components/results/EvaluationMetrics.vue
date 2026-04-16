<script setup lang="ts">
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { backendResponse } = useAnalysisActions()
</script>

<template>
  <div v-if="backendResponse?.data?.metrics" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200">
      <h3 class="m-0 text-lg flex items-center gap-3">
        <span class="bg-slate-900 text-white w-6 h-6 flex items-center justify-center rounded-md text-sm font-bold">A</span>
        聚类效果评估与降维可视化
      </h3>
    </div>
    <div class="p-6">
      <div v-if="backendResponse.data.lost_samples" class="bg-amber-50 border border-amber-200 text-amber-700 p-3 rounded-lg text-[13px] mb-5">
        ⚠️ <strong>提示：</strong>在与组学/临床数据取交集时，有 <strong>{{ backendResponse.data.lost_samples }}</strong> 个病人因无法完全对齐而被系统丢弃。
      </div>
      <div class="grid grid-cols-3 gap-5">
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 text-center">
          <div class="text-xs text-slate-500 uppercase tracking-wider">Silhouette Score</div>
          <div class="text-3xl font-extrabold text-primary my-2">{{ backendResponse.data.metrics.silhouette ?? 'N/A' }}</div>
          <div class="text-xs text-slate-700">轮廓系数 ↑</div>
        </div>
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 text-center">
          <div class="text-xs text-slate-500 uppercase tracking-wider">Calinski-Harabasz</div>
          <div class="text-3xl font-extrabold text-primary my-2">{{ backendResponse.data.metrics.calinski ?? 'N/A' }}</div>
          <div class="text-xs text-slate-700">CH 指数 ↑</div>
        </div>
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 text-center">
          <div class="text-xs text-slate-500 uppercase tracking-wider">Davies-Bouldin</div>
          <div class="text-3xl font-extrabold text-primary my-2">{{ backendResponse.data.metrics.davies ?? 'N/A' }}</div>
          <div class="text-xs text-slate-700">DB 指数 ↓</div>
        </div>
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 text-center">
          <div class="text-xs text-slate-500 uppercase tracking-wider">Dunn Index</div>
          <div class="text-3xl font-extrabold text-primary my-2">{{ backendResponse.data.metrics.dunn ?? 'N/A' }}</div>
          <div class="text-xs text-slate-700">Dunn 指数 ↑</div>
        </div>
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 text-center">
          <div class="text-xs text-slate-500 uppercase tracking-wider">Xie-Beni</div>
          <div class="text-3xl font-extrabold text-primary my-2">{{ backendResponse.data.metrics.xb ?? 'N/A' }}</div>
          <div class="text-xs text-slate-700">XB 指数 ↓</div>
        </div>
        <div class="bg-slate-50 p-5 rounded-xl border border-slate-200 text-center">
          <div class="text-xs text-slate-500 uppercase tracking-wider">S_Dbw</div>
          <div class="text-3xl font-extrabold text-primary my-2">{{ backendResponse.data.metrics.s_dbw ?? 'N/A' }}</div>
          <div class="text-xs text-slate-700">S_Dbw 指数 ↓</div>
        </div>
      </div>
    </div>
  </div>
</template>
