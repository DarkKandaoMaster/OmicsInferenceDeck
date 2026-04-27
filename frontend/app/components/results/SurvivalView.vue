<script setup lang="ts">
import { useSurvival } from '~/composables/domain/useSurvival'
import { formatPValue } from '~/utils/formatters'

const { survivalResult, isSurvivalLoading, survivalErrorMessage } = useSurvival()
</script>

<template>
  <div v-if="isSurvivalLoading" class="result-card">
    <div class="p-5 text-sm text-slate-600">正在计算 Log-Rank P-value 与 KM 生存曲线...</div>
  </div>

  <div v-else-if="survivalErrorMessage" class="result-card">
    <div class="p-5 text-sm text-red-700">{{ survivalErrorMessage }}</div>
  </div>

  <div v-else-if="survivalResult" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">生存曲线</div>
      <div class="text-sm text-slate-600">
        Log-Rank P-value:
        <span class="font-bold text-slate-900">{{ survivalResult.p_value ? formatPValue(survivalResult.p_value) : 'N/A' }}</span>
      </div>
    </div>
    <div v-if="survivalResult.lost_samples" class="mx-5 mt-4 bg-amber-50 border border-amber-200 text-amber-700 p-3 rounded-lg text-[13px]">
      {{ survivalResult.lost_samples }} 个已聚类样本因缺少临床数据未参与生存分析。
    </div>
    <div class="svg-chart" v-html="survivalResult.survival_svg" />
  </div>
</template>
