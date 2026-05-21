<script setup lang="ts">
import { useDataState } from '~/composables/domain/useDataState'
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'

const { isCustomEvalMode } = useDataState()
const { errorMessage } = useUIState()
const { isTestMode } = useAlgorithmState()

const chartOptions = ['聚类散点图', '生存曲线', '参数曲面', '差异火山图', '差异热图', '富集图']
const metricOptions = ['AWA', '聚类一致性', '临床关联', '生物学相关性', '生存 P-value']

watch(isCustomEvalMode, (enabled) => {
  if (enabled) isTestMode.value = false
})
</script>

<template>
  <div class="mx-auto flex max-w-7xl flex-col gap-6">
    <section class="mx-auto grid w-full max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
      <label
        class="flex min-h-[74px] cursor-pointer items-center justify-between rounded-lg border bg-white px-5 py-4 shadow-sm transition-all hover:border-primary"
        :class="isCustomEvalMode ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-800'"
      >
        <input v-model="isCustomEvalMode" type="radio" :value="true" class="sr-only" />
        <span class="text-sm font-semibold">我想测试自己的算法</span>
        <span class="h-4 w-4 rounded-full border" :class="isCustomEvalMode ? 'border-primary bg-primary' : 'border-slate-300'" />
      </label>

      <label
        class="flex min-h-[74px] cursor-pointer items-center justify-between rounded-lg border bg-white px-5 py-4 shadow-sm transition-all hover:border-primary"
        :class="!isCustomEvalMode ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-800'"
      >
        <input v-model="isCustomEvalMode" type="radio" :value="false" class="sr-only" />
        <span class="text-sm font-semibold">我想测试平台内置算法</span>
        <span class="h-4 w-4 rounded-full border" :class="!isCustomEvalMode ? 'border-primary bg-primary' : 'border-slate-300'" />
      </label>
    </section>

    <section class="mx-auto grid w-full max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
      <label class="flex min-h-[64px] cursor-default items-center justify-between rounded-lg border border-primary bg-indigo-50 px-5 py-4 text-primary shadow-sm">
        <span class="text-sm font-semibold">我想测试无监督学习</span>
        <span class="text-xs font-medium">已选择</span>
      </label>

      <label class="flex min-h-[64px] cursor-not-allowed items-center justify-between rounded-lg border border-slate-200 bg-slate-100 px-5 py-4 text-slate-400">
        <input type="radio" disabled class="sr-only" />
        <span class="text-sm font-semibold">我想测试监督学习（暂未开放）</span>
        <span class="text-xs font-medium">禁用</span>
      </label>
    </section>

    <AnalysisDataUpload />

    <AnalysisAlgorithmSelect />

    <section class="mx-auto w-full max-w-5xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-base font-semibold text-slate-900">3. 结果内容</h3>
        <p class="mt-1 text-xs text-slate-500">图表和数学指标暂不支持单独选择，点击运行后会生成全部可用内容。</p>
      </div>

      <div class="grid grid-cols-1 gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)]">
        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">选择要绘制的图表</h4>
          <div class="grid grid-cols-2 gap-2">
            <label v-for="option in chartOptions" :key="option" class="flex cursor-not-allowed items-center gap-2 rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-[13px] text-slate-400">
              <input type="checkbox" checked disabled class="h-4 w-4" />
              <span>{{ option }}</span>
            </label>
          </div>
        </div>

        <div class="h-px bg-slate-200 lg:h-auto lg:w-px" />

        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">选择要计算的数学指标</h4>
          <div class="grid grid-cols-2 gap-2">
            <label v-for="option in metricOptions" :key="option" class="flex cursor-not-allowed items-center gap-2 rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-[13px] text-slate-400">
              <input type="checkbox" checked disabled class="h-4 w-4" />
              <span>{{ option }}</span>
            </label>
          </div>
        </div>
      </div>
    </section>

    <AnalysisActions />

    <div v-if="errorMessage" class="mx-auto mb-2 flex w-full max-w-5xl items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 font-medium text-red-700">
      <span>{{ errorMessage }}</span>
    </div>

    <ResultsContainer />
  </div>
</template>
