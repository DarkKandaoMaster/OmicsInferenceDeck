<script setup lang="ts">
import { useDataState } from '~/composables/domain/useDataState'
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const { isCustomEvalMode } = useDataState()
const { isLoading, errorMessage } = useUIState()
const { isTestMode, isPsLoading } = useAlgorithmState()
const { enabledMetrics, enabledCharts, metricOptions, chartOptions } = useResultSelection()

const isBusy = computed(() => isLoading.value || isPsLoading.value)

watch(isCustomEvalMode, (enabled) => {
  if (enabled) isTestMode.value = false
})
</script>

<template>
  <fieldset :disabled="isBusy" class="mx-auto flex max-w-7xl flex-col gap-6 min-w-0 border-0 p-0 m-0">
    <AnalysisModeSelector v-model:is-custom-eval-mode="isCustomEvalMode" />

    <AnalysisDataUpload />

    <AnalysisAlgorithmSelect />

    <section class="mx-auto w-full max-w-4xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-base font-semibold text-slate-900">3. 选择想展示的结果</h3>
        <p class="mt-1 text-xs text-slate-500">取消勾选后将跳过对应的后端计算，节省运行时间。</p>
      </div>

      <div class="grid grid-cols-1 gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)]">
        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">选择要计算的数学指标</h4>
          <div class="grid grid-cols-2 gap-2">
            <label
              v-for="option in metricOptions"
              :key="option.key"
              class="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-700 transition hover:bg-slate-50"
            >
              <input v-model="enabledMetrics[option.key]" type="checkbox" class="h-4 w-4" />
              <span>{{ option.label }}</span>
            </label>
          </div>
        </div>

        <div class="h-px bg-slate-200 lg:h-auto lg:w-px" />

        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">选择要绘制的图表</h4>
          <div class="grid grid-cols-2 gap-2">
            <label
              v-for="option in chartOptions"
              :key="option.key"
              class="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-700 transition hover:bg-slate-50"
            >
              <input v-model="enabledCharts[option.key]" type="checkbox" class="h-4 w-4" />
              <span>{{ option.label }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="border-t border-slate-100 bg-slate-50/50 px-5 py-3 text-[12px] leading-relaxed text-slate-500">
        依赖关系： 综合得分 依赖 聚类内部质量指标、临床关联指标、生物学相关性指标； 生物学相关性指标 依赖 任一富集分析图； 富集分析图 依赖 任一差异分析图。 勾选下游会自动勾选其全部上游；当某组上游全部取消勾选时，依赖它的下游也会自动取消勾选。
      </div>
    </section>

    <AnalysisActions />

    <div v-if="errorMessage" class="mx-auto mb-2 flex w-full max-w-5xl items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 font-medium text-red-700">
      <span>{{ errorMessage }}</span>
    </div>

    <ResultsContainer />
  </fieldset>
</template>
