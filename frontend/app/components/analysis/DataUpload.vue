<script setup lang="ts">
import { useDataState } from '~/composables/domain/useDataState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'

const {
  omicsFileConfigs, omicsTypes, uploadStatus,
  omicsIsRowSample, omicsHasHeader, omicsHasIndex,
  exampleText,
  clinicalUploadStatus, clinicalIsRowSample, clinicalHasHeader, clinicalHasIndex,
  clinicalExampleText,
  expressionMatrixFile, expressionMatrixUploadStatus,
  expressionMatrixIsRowSample, expressionMatrixHasHeader, expressionMatrixHasIndex,
  expressionMatrixExampleText,
  handleFileChange, handleFormatChange,
  handleExpressionMatrixFileChange, handleExpressionMatrixFormatChange,
  handleClinicalFileChange, handleClinicalFormatChange,
} = useDataState()

const {
  cancerSubtypeOptions,
  selectedCancerSubtype,
  applyCancerSubtypeClusterCount,
} = useAlgorithmState()

function handleCancerSubtypeChange() {
  applyCancerSubtypeClusterCount(selectedCancerSubtype.value)
}
</script>

<template>
  <section class="mx-auto w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
    <div class="relative flex flex-col gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4 md:flex-row md:items-center md:justify-center">
      <div class="md:absolute md:left-5 md:top-1/2 md:-translate-y-1/2">
        <h3 class="m-0 text-base font-semibold text-slate-900">1. 数据上传</h3>
      </div>
      <div class="flex w-full max-w-sm items-center gap-3">
        <label class="whitespace-nowrap text-xs font-medium text-slate-700"><h4 class="m-0 text-sm font-semibold text-slate-900">对应癌症亚型：</h4></label>
        <select
          v-model="selectedCancerSubtype"
          class="w-40 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10"
          @change="handleCancerSubtypeChange"
        >
          <option v-for="option in cancerSubtypeOptions" :key="option.type" :value="option.type">
            {{ option.type }}
          </option>
        </select>
      </div>
    </div>

    <div class="grid gap-5 p-5 xl:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)_1px_minmax(0,1fr)]">
      <div>
        <div class="mb-3 flex items-center justify-between gap-3">
          <h4 class="m-0 text-sm font-semibold text-slate-900">组学数据</h4>
        </div>

        <div class="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3 xl:grid-cols-1">
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="omicsIsRowSample ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="omicsIsRowSample" type="checkbox" class="hidden" @change="handleFormatChange" />
            <span>行代表特征，列代表病人</span>
            <span v-if="omicsIsRowSample" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="omicsHasHeader ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="omicsHasHeader" type="checkbox" class="hidden" @change="handleFormatChange" />
            <span>包含表头行</span>
            <span v-if="omicsHasHeader" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="omicsHasIndex ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="omicsHasIndex" type="checkbox" class="hidden" @change="handleFormatChange" />
            <span>包含索引列</span>
            <span v-if="omicsHasIndex" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
        </div>

        <div class="mb-3 rounded-lg bg-slate-900 p-3">
          <div class="mb-2 text-[11px] font-semibold uppercase text-slate-400">CSV 格式预览</div>
          <pre class="m-0 min-h-[112px] overflow-x-auto whitespace-pre text-xs leading-relaxed text-slate-100">{{ exampleText }}</pre>
        </div>

        <div class="relative rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 text-center transition-all hover:border-primary hover:bg-indigo-50">
          <input id="omics-file" type="file" multiple class="absolute inset-0 h-full w-full cursor-pointer opacity-0" @change="handleFileChange" />
          <label for="omics-file" class="flex min-h-[104px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
            <span class="text-sm font-semibold text-slate-900">选择或拖入组学文件</span>
            <small class="mt-1 text-xs leading-relaxed text-slate-500">必填。支持多选，运行时自动对齐病人交集。</small>
          </label>
        </div>

        <div v-if="omicsFileConfigs.length > 0" class="mt-3 flex flex-col gap-2">
          <div v-for="config in omicsFileConfigs" :key="config.id" class="grid grid-cols-[minmax(0,1fr)_128px] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <span class="truncate text-[13px] text-slate-900" :title="config.originalName">{{ config.originalName }}</span>
            <select v-model="config.type" class="rounded-lg border border-slate-200 bg-white px-2 py-1 text-[13px] outline-none focus:border-primary" @change="handleFormatChange">
              <option v-for="type in omicsTypes" :key="type" :value="type">{{ type }}</option>
            </select>
          </div>
        </div>

        <div v-show="uploadStatus" class="mt-3 whitespace-pre-wrap break-words rounded-lg p-2 text-xs" :class="uploadStatus.startsWith('❌') ? 'border border-red-200 bg-red-50 text-red-700' : uploadStatus.startsWith('✅') ? 'border border-green-200 bg-green-50 text-green-800' : 'border border-slate-200 bg-slate-50 text-slate-700'">
          {{ uploadStatus }}
        </div>
      </div>

      <div class="h-px bg-slate-200 xl:h-auto xl:w-px" />

      <div>
        <div class="mb-3 flex items-center justify-between gap-3">
          <h4 class="m-0 text-sm font-semibold text-slate-900">mRNA表达矩阵</h4>
        </div>

        <div class="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3 xl:grid-cols-1">
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="expressionMatrixIsRowSample ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="expressionMatrixIsRowSample" type="checkbox" class="hidden" @change="handleExpressionMatrixFormatChange" />
            <span>行代表基因，列代表病人</span>
            <span v-if="expressionMatrixIsRowSample" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="expressionMatrixHasHeader ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="expressionMatrixHasHeader" type="checkbox" class="hidden" @change="handleExpressionMatrixFormatChange" />
            <span>包含表头行</span>
            <span v-if="expressionMatrixHasHeader" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="expressionMatrixHasIndex ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="expressionMatrixHasIndex" type="checkbox" class="hidden" @change="handleExpressionMatrixFormatChange" />
            <span>包含索引列</span>
            <span v-if="expressionMatrixHasIndex" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
        </div>

        <div class="mb-3 rounded-lg bg-slate-900 p-3">
          <div class="mb-2 text-[11px] font-semibold uppercase text-slate-400">CSV 格式预览</div>
          <pre class="m-0 min-h-[112px] overflow-x-auto whitespace-pre text-xs leading-relaxed text-slate-100">{{ expressionMatrixExampleText }}</pre>
        </div>

        <div class="relative rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 text-center transition-all hover:border-primary hover:bg-indigo-50">
          <input id="expression-matrix-file" type="file" class="absolute inset-0 h-full w-full cursor-pointer opacity-0" @change="handleExpressionMatrixFileChange" />
          <label for="expression-matrix-file" class="flex min-h-[104px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
            <span class="text-sm font-semibold text-slate-900">选择mRNA表达矩阵</span>
            <small class="mt-1 text-xs leading-relaxed text-slate-500">可选。用于差异表达和 GO/KEGG 富集分析。</small>
          </label>
        </div>

        <div v-if="expressionMatrixFile" class="mt-3 flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <span class="truncate text-[13px] text-slate-900" :title="expressionMatrixFile.name">{{ expressionMatrixFile.name }}</span>
          <span class="text-xs text-slate-500">mRNA</span>
        </div>

        <div v-show="expressionMatrixUploadStatus" class="mt-3 whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
          {{ expressionMatrixUploadStatus }}
        </div>
      </div>

      <div class="h-px bg-slate-200 xl:h-auto xl:w-px" />

      <div>
        <div class="mb-3 flex items-center justify-between gap-3">
          <h4 class="m-0 text-sm font-semibold text-slate-900">临床数据</h4>
        </div>

        <div class="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3 xl:grid-cols-1">
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="clinicalIsRowSample ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="clinicalIsRowSample" type="checkbox" class="hidden" @change="handleClinicalFormatChange" />
            <span>行代表特征，列代表病人</span>
            <span v-if="clinicalIsRowSample" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="clinicalHasHeader ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="clinicalHasHeader" type="checkbox" class="hidden" @change="handleClinicalFormatChange" />
            <span>包含表头行</span>
            <span v-if="clinicalHasHeader" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-all hover:border-primary" :class="clinicalHasIndex ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-700'">
            <input v-model="clinicalHasIndex" type="checkbox" class="hidden" @change="handleClinicalFormatChange" />
            <span>包含索引列</span>
            <span v-if="clinicalHasIndex" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
        </div>

        <div class="mb-3 rounded-lg bg-slate-900 p-3">
          <div class="mb-2 text-[11px] font-semibold uppercase text-slate-400">CSV 格式预览</div>
          <pre class="m-0 min-h-[112px] overflow-x-auto whitespace-pre text-xs leading-relaxed text-slate-100">{{ clinicalExampleText }}</pre>
        </div>

        <div class="relative rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 text-center transition-all hover:border-primary hover:bg-indigo-50">
          <input id="clinical-file" type="file" class="absolute inset-0 h-full w-full cursor-pointer opacity-0" @change="handleClinicalFileChange" />
          <label for="clinical-file" class="flex min-h-[104px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
            <span class="text-sm font-semibold text-slate-900">选择临床文件</span>
            <small class="mt-1 text-xs leading-relaxed text-slate-500">可选。建议包含 OS 和 OS.time 字段。</small>
          </label>
        </div>

        <div v-show="clinicalUploadStatus" class="mt-3 whitespace-pre-wrap break-words rounded-lg p-2 text-xs" :class="clinicalUploadStatus.startsWith('❌') ? 'border border-red-200 bg-red-50 text-red-700' : clinicalUploadStatus.startsWith('✅') ? 'border border-green-200 bg-green-50 text-green-800' : 'border border-slate-200 bg-slate-50 text-slate-700'">
          {{ clinicalUploadStatus }}
        </div>
      </div>
    </div>
  </section>
</template>
