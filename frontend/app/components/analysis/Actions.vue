<script setup lang="ts">
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { isLoading } = useUIState()
const { isTestMode, isPsLoading } = useAlgorithmState()
const { analysisStatus, runAnalysisFlow, runParameterSearchFlow } = useAnalysisActions()
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl justify-center py-4">
    <button
      v-if="!isTestMode"
      @click="runAnalysisFlow"
      :disabled="isLoading"
      class="min-w-[220px] cursor-pointer rounded-lg border-none bg-primary px-10 py-3.5 text-base font-semibold text-white shadow-sm transition-all hover:bg-primary-hover hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
    >
      <span class="flex items-center gap-2">
        <span v-if="isLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        {{ isLoading ? (analysisStatus || '正在运行分析...') : '运行分析' }}
      </span>
    </button>

    <button
      v-else
      @click="runParameterSearchFlow"
      :disabled="isPsLoading"
      class="min-w-[220px] cursor-pointer rounded-lg border-none bg-amber-600 px-10 py-3.5 text-base font-semibold text-white shadow-sm transition-all hover:bg-amber-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
    >
      <span class="flex items-center gap-2">
        <span v-if="isPsLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        {{ isPsLoading ? '正在搜索...' : '运行参数敏感性分析' }}
      </span>
    </button>
  </div>
</template>
