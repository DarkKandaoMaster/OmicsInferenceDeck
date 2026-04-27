<script setup lang="ts">
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const { isLoading } = useUIState()
const { isTestMode, isPsLoading } = useAlgorithmState()
const { analysisStatus, runAnalysisFlow, runParameterSearchFlow } = useAnalysisActions()
</script>

<template>
  <div class="flex justify-center my-10">
    <button
      v-if="!isTestMode"
      @click="runAnalysisFlow"
      :disabled="isLoading"
      class="border-none rounded-[30px] text-base font-semibold px-10 py-4 cursor-pointer transition-all shadow-md text-white bg-gradient-to-r from-primary to-secondary hover:-translate-y-0.5 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0"
    >
      <span class="flex items-center gap-2">
        <span v-if="isLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        {{ isLoading ? (analysisStatus || 'Running analysis...') : 'Run Analysis' }}
      </span>
    </button>

    <button
      v-else
      @click="runParameterSearchFlow"
      :disabled="isPsLoading"
      class="border-none rounded-[30px] text-base font-semibold px-10 py-4 cursor-pointer transition-all shadow-md text-white bg-gradient-to-r from-red-500 to-amber-500 hover:-translate-y-0.5 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0"
    >
      <span class="flex items-center gap-2">
        <span v-if="isPsLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        {{ isPsLoading ? 'Searching...' : 'Run Parameter Search' }}
      </span>
    </button>
  </div>
</template>
