<script setup lang="ts">
import { useAnalysisLog } from '~/composables/core/useAnalysisLog'
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useDataState } from '~/composables/domain/useDataState'

const { isLoading } = useUIState()
const { isTestMode, isPsLoading } = useAlgorithmState()
const { runAnalysisFlow, runParameterSearchFlow } = useAnalysisActions()
const { isCustomEvalMode, isCustomEvalTestMode } = useDataState()
const { logEntries } = useAnalysisLog()

// 两种模式各有一个“参数敏感性分析”开关：内置算法用 isTestMode，自己的算法用 isCustomEvalTestMode。
// 只要当前模式的开关打开，就展示“运行参数敏感性分析”按钮。
const isSensitivityMode = computed(() =>
  isCustomEvalMode.value ? isCustomEvalTestMode.value : isTestMode.value,
)

// 自己的算法模式的敏感性流程走 runAnalysisFlow（内部处理 .mat 上传），内置算法模式走 runParameterSearchFlow。
function runSensitivityFlow() {
  return isCustomEvalMode.value ? runAnalysisFlow() : runParameterSearchFlow()
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col items-center gap-3 py-4">
    <div class="flex justify-center">
      <button
        v-if="!isSensitivityMode"
        @click="runAnalysisFlow"
        :disabled="isLoading"
        class="min-w-[220px] cursor-pointer rounded-full border-none bg-gradient-to-r from-blue-500 to-indigo-600 px-10 py-3.5 text-base font-semibold text-white shadow-lg shadow-indigo-500/30 transition-all hover:from-blue-600 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
      >
        <span class="flex items-center justify-center gap-2">
          <span v-if="isLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          {{ isLoading ? '正在运行分析...' : '运行分析' }}
        </span>
      </button>

      <button
        v-else
        @click="runSensitivityFlow"
        :disabled="isPsLoading"
        class="min-w-[220px] cursor-pointer rounded-full border-none bg-gradient-to-r from-amber-500 to-amber-600 px-10 py-3.5 text-base font-semibold text-white shadow-lg shadow-amber-500/30 transition-all hover:from-amber-600 hover:to-amber-700 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
      >
        <span class="flex items-center justify-center gap-2">
          <span v-if="isPsLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          {{ isPsLoading ? '正在搜索...' : '运行参数敏感性分析' }}
        </span>
      </button>
    </div>

    <!-- 累积式运行日志：运行前为空（隐藏），点“运行分析”后逐行追加，已展示的行不清除 -->
    <div
      v-if="logEntries.length"
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
