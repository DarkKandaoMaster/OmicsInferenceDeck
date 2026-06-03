<script setup lang="ts">
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useDataState } from '~/composables/domain/useDataState'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useSurvival } from '~/composables/domain/useSurvival'

const { isLoading } = useUIState()
const { isTestMode, isPsLoading } = useAlgorithmState()
const { analysisStatus, runAnalysisFlow, runParameterSearchFlow } = useAnalysisActions()
const {
  uploadStatus,
  expressionMatrixUploadStatus,
  clinicalUploadStatus,
  customEvalUploadStatus,
} = useDataState()
const { isDiffLoading, diffErrorMessage } = useDifferential()
const { isEnrichmentLoading, enrichmentErrorMessage } = useEnrichment()
const { isSurvivalLoading, survivalErrorMessage, survivalResult } = useSurvival()
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col items-center gap-3 py-4">
    <div class="flex justify-center">
      <button
        v-if="!isTestMode"
        @click="runAnalysisFlow"
        :disabled="isLoading"
        class="min-w-[220px] cursor-pointer rounded-lg border-none bg-primary px-10 py-3.5 text-base font-semibold text-white shadow-sm transition-all hover:bg-primary-hover hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
      >
        <span class="flex items-center justify-center gap-2">
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

    <div class="mx-auto flex w-full max-w-3xl flex-col gap-2">
      <div v-show="uploadStatus" class="whitespace-pre-wrap break-words rounded-lg p-2 text-xs" :class="uploadStatus.startsWith('❌') ? 'border border-red-200 bg-red-50 text-red-700' : uploadStatus.startsWith('✅') ? 'border border-green-200 bg-green-50 text-green-800' : 'border border-slate-200 bg-slate-50 text-slate-700'">
        {{ uploadStatus }}
      </div>

      <div v-show="expressionMatrixUploadStatus" class="whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
        {{ expressionMatrixUploadStatus }}
      </div>

      <div v-show="clinicalUploadStatus" class="whitespace-pre-wrap break-words rounded-lg p-2 text-xs" :class="clinicalUploadStatus.startsWith('❌') ? 'border border-red-200 bg-red-50 text-red-700' : clinicalUploadStatus.startsWith('✅') ? 'border border-green-200 bg-green-50 text-green-800' : 'border border-slate-200 bg-slate-50 text-slate-700'">
        {{ clinicalUploadStatus }}
      </div>

      <div v-show="customEvalUploadStatus" class="rounded-lg border border-green-200 bg-green-50 p-2 text-xs text-green-800">
        {{ customEvalUploadStatus }}
      </div>

      <!-- 分析运行状态：差异表达 / 富集 / 生存 -->
      <div v-if="isDiffLoading" class="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
        <span class="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
        正在计算差异表达结果...
      </div>
      <div v-if="diffErrorMessage" class="whitespace-pre-wrap break-words rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700">
        {{ diffErrorMessage }}
      </div>

      <div v-if="isEnrichmentLoading" class="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
        <span class="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
        正在查询 GO + KEGG 富集结果...
      </div>
      <div v-if="enrichmentErrorMessage" class="whitespace-pre-wrap break-words rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700">
        {{ enrichmentErrorMessage }}
      </div>

      <div v-if="isSurvivalLoading" class="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
        <span class="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
        正在计算 Log-Rank P 值与 KM 生存曲线...
      </div>
      <div v-if="survivalErrorMessage" class="whitespace-pre-wrap break-words rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700">
        {{ survivalErrorMessage }}
      </div>

      <!-- 生存分析：被排除样本提示（始终显示） -->
      <div class="whitespace-pre-wrap break-words rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700">
        {{ survivalResult?.lost_samples
          ? `${survivalResult.lost_samples} clustered samples were excluded because clinical data was missing.`
          : 'No clustered samples were excluded.' }}
      </div>
    </div>
  </div>
</template>
