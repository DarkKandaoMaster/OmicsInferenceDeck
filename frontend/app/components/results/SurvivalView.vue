<script setup lang="ts">
import { useSession } from '~/composables/core/useSession'
import { useSurvival } from '~/composables/domain/useSurvival'
import { formatPValue } from '~/utils/formatters'

const { survivalResult, isSurvivalLoading, survivalErrorMessage } = useSurvival()
const { sessionId } = useSession()

const downloadParams = computed(() => ({
  session_id: sessionId.value,
}))
</script>

<template>
  <div v-if="isSurvivalLoading" class="result-card">
    <div class="p-5 text-sm text-slate-600">Calculating Log-Rank P-value and KM survival curve...</div>
  </div>

  <div v-else-if="survivalErrorMessage" class="result-card">
    <div class="p-5 text-sm text-red-700">{{ survivalErrorMessage }}</div>
  </div>

  <div v-else-if="survivalResult" class="result-card">
    <div class="result-card-header">
      <div class="result-card-title">Survival Curve</div>
      <div class="flex items-center gap-3 text-sm text-slate-600">
        <span>
          Log-Rank P-value:
          <span class="font-bold text-slate-900">{{ survivalResult.p_value ? formatPValue(survivalResult.p_value) : 'N/A' }}</span>
        </span>
        <ResultsPlotDownloadButton plot-type="survival_curve" :params="downloadParams" filename-prefix="survival_curve" />
      </div>
    </div>
    <div v-if="survivalResult.lost_samples" class="mx-5 mt-4 bg-amber-50 border border-amber-200 text-amber-700 p-3 rounded-lg text-[13px]">
      {{ survivalResult.lost_samples }} clustered samples were excluded because clinical data was missing.
    </div>
    <div class="svg-chart" v-html="survivalResult.survival_svg" />
  </div>
</template>
