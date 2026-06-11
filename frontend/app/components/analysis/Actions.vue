<script setup lang="ts">
import { useAnalysisLog } from '~/composables/core/useAnalysisLog'
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useDataState } from '~/composables/domain/useDataState'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useSurvival } from '~/composables/domain/useSurvival'

const { isLoading } = useUIState()
const { isTestMode, isPsLoading } = useAlgorithmState()
const { runAnalysisFlow, runParameterSearchFlow, abortRun } = useAnalysisActions()
const { isCustomEvalMode, isCustomEvalTestMode } = useDataState()
const { logEntries } = useAnalysisLog()
const { isDiffLoading } = useDifferential()
const { isEnrichmentLoading } = useEnrichment()
const { isSurvivalLoading } = useSurvival()

// 运行中（标准分析或参数敏感性分析任一在跑）：按钮显示为红色「停止运行」。
const isRunning = computed(() => isLoading.value || isPsLoading.value)

// 停止：作废当前运行 + 标记日志，并立刻把结果面板里各下游分析的转圈也停掉。
function onTerminate() {
  abortRun()
  isDiffLoading.value = false
  isEnrichmentLoading.value = false
  isSurvivalLoading.value = false
}

// 两种模式各有一个“参数敏感性分析”开关：内置算法用 isTestMode，自己的算法用 isCustomEvalTestMode。
// 只要当前模式的开关打开，就展示“运行参数敏感性分析”按钮。
const isSensitivityMode = computed(() =>
  isCustomEvalMode.value ? isCustomEvalTestMode.value : isTestMode.value,
)

// 自己的算法模式的敏感性流程走 runAnalysisFlow（内部处理 .mat 上传），内置算法模式走 runParameterSearchFlow。
function runSensitivityFlow() {
  return isCustomEvalMode.value ? runAnalysisFlow() : runParameterSearchFlow()
}

// 日志滚动容器：每追加一行日志后，等 DOM 更新完再滚动到底部，让最新一行始终可见。
const logContainer = ref<HTMLElement | null>(null)
watch(
  () => logEntries.value.length,
  async () => {
    await nextTick()
    const el = logContainer.value
    if (el) el.scrollTop = el.scrollHeight
  },
)
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col items-center gap-3 py-4">
    <div class="flex justify-center">
      <!-- 运行中：统一显示红色「停止运行」按钮（可点击，立即复位） -->
      <button
        v-if="isRunning"
        @click="onTerminate"
        class="min-w-[220px] cursor-pointer rounded-full border-none bg-gradient-to-r from-red-500 to-red-600 px-10 py-3.5 text-base font-semibold text-white shadow-lg shadow-red-500/30 transition-all hover:from-red-600 hover:to-red-700"
      >
        <span class="flex items-center justify-center gap-2">⏹ 停止运行</span>
      </button>

      <button
        v-else-if="!isSensitivityMode"
        @click="runAnalysisFlow"
        class="min-w-[220px] cursor-pointer rounded-full border-none bg-gradient-to-r from-blue-500 to-indigo-600 px-10 py-3.5 text-base font-semibold text-white shadow-lg shadow-indigo-500/30 transition-all hover:from-blue-600 hover:to-indigo-700"
      >
        <span class="flex items-center justify-center gap-2">运行分析</span>
      </button>

      <button
        v-else
        @click="runSensitivityFlow"
        class="min-w-[220px] cursor-pointer rounded-full border-none bg-gradient-to-r from-amber-500 to-amber-600 px-10 py-3.5 text-base font-semibold text-white shadow-lg shadow-amber-500/30 transition-all hover:from-amber-600 hover:to-amber-700"
      >
        <span class="flex items-center justify-center gap-2">运行参数敏感性分析</span>
      </button>
    </div>

    <!-- 累积式运行日志：运行前为空（隐藏），点“运行分析”后逐行追加，已展示的行不清除 -->
    <div
      v-if="logEntries.length"
      ref="logContainer"
      class="mx-auto flex max-h-72 w-full max-w-3xl flex-col gap-2 overflow-y-auto"
    >
      <div
        v-for="entry in logEntries"
        :key="entry.id"
        class="flex items-start gap-2 whitespace-pre-wrap break-words rounded-lg border p-2 text-xs"
        :class="{
          'border-slate-200 bg-slate-50 text-slate-700': entry.level === 'progress',
          'border-green-200 bg-green-50 text-green-800': entry.level === 'success',
          'border-red-200 bg-red-50 text-red-700': entry.level === 'error',
          'border-amber-200 bg-amber-50 text-amber-700': entry.level === 'warning',
          'border-rose-200 bg-rose-50 text-rose-700': entry.level === 'terminated',
        }"
      >
        <span
          v-if="entry.level === 'progress'"
          class="mt-0.5 h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600"
        />
        <span>{{ entry.text }}</span>
      </div>
    </div>
  </div>
</template>
