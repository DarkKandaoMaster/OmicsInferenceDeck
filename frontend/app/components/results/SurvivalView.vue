<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useSurvival } from '~/composables/domain/useSurvival'
import { useResultSelection } from '~/composables/domain/useResultSelection'
import { formatPValue } from '~/utils/formatters'

const { survivalResult, survivalErrorMessage } = useSurvival()
const { sessionId } = useSession()
const { enabledCharts } = useResultSelection()

const downloadParams = computed(() => ({
  session_id: sessionId.value,
}))
</script>

<template>
  <template v-if="enabledCharts.survival">
    <div v-if="survivalResult" class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">生存曲线</div>
        <div class="flex items-center gap-3 text-sm text-slate-600">
          <span>
            Log-Rank P-value:
            <span class="font-bold text-slate-900">{{ survivalResult.p_value ? formatPValue(survivalResult.p_value) : 'N/A' }}</span>
          </span>
          <ResultsPlotDownloadButton plot-type="survival_curve" :params="downloadParams" filename-prefix="survival_curve" />
        </div>
      </div>
      <div class="svg-chart" v-html="survivalResult.survival_svg" />
    </div>

    <div v-else class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">生存曲线</div>
      </div>
      <div class="result-placeholder min-h-[420px]">
        <div class="text-sm font-medium text-slate-500">暂无生存曲线</div>
        <div class="text-xs text-slate-400">
          {{ survivalErrorMessage || '未能生成生存曲线，请确认已上传临床数据并完成聚类分析。' }}
        </div>
      </div>
    </div>
  </template>
</template>
