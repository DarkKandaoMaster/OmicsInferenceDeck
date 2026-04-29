<script setup lang="ts">
import { useDataState } from '~/composables/domain/useDataState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'

const {
  omicsFileConfigs, omicsTypes, uploadStatus,
  omicsIsRowSample, omicsHasHeader, omicsHasIndex,
  exampleText,
  clinicalUploadStatus,
  clinicalIsRowSample, clinicalHasHeader, clinicalHasIndex,
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
  kValue,
} = useAlgorithmState()

function handleCancerSubtypeChange() {
  applyCancerSubtypeClusterCount(selectedCancerSubtype.value)
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
    <div class="bg-slate-50 px-5 py-4 border-b border-slate-200 flex items-center gap-2.5">
      <span>📂</span>
      <h3 class="m-0 text-base font-semibold text-slate-900">1. 数据上传</h3>
    </div>
    <div class="p-5 flex-1">
      <!-- 组学数据 -->
      <div class="mb-0">
        <div class="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <label class="block text-xs font-medium text-slate-700 mb-1.5">癌症亚型</label>
          <div class="flex items-center gap-2">
            <select v-model="selectedCancerSubtype" @change="handleCancerSubtypeChange" class="flex-1 min-w-0 px-3 py-2 border border-slate-200 rounded-lg text-[13px] bg-white text-slate-900 cursor-pointer outline-none focus:border-primary focus:ring-2 focus:ring-primary/10">
              <option v-for="option in cancerSubtypeOptions" :key="option.type" :value="option.type">
                {{ option.type }}
              </option>
            </select>
          </div>
        </div>
        <h4 class="m-0 mb-3 text-sm flex items-center gap-2">🧬 组学数据 <span class="text-[11px] px-1.5 py-0.5 rounded bg-red-100 text-red-700">必填</span></h4>

        <div class="flex flex-col gap-2 mb-4">
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': omicsIsRowSample }">
            <input type="checkbox" v-model="omicsIsRowSample" @change="handleFormatChange" class="hidden" />
            行代表特征, 列代表病人
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': omicsHasHeader }">
            <input type="checkbox" v-model="omicsHasHeader" @change="handleFormatChange" class="hidden" />
            包含表头行
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': omicsHasIndex }">
            <input type="checkbox" v-model="omicsHasIndex" @change="handleFormatChange" class="hidden" />
            包含索引列
          </label>
        </div>

        <div class="bg-slate-800 rounded-lg p-3 mb-4">
          <div class="text-[11px] text-slate-400 mb-2 uppercase tracking-wider">CSV 格式预览</div>
          <pre class="m-0 text-slate-100 font-mono text-xs leading-relaxed overflow-x-auto">{{ exampleText }}</pre>
        </div>

        <div class="relative border-2 border-dashed border-slate-200 rounded-lg bg-slate-100 hover:border-primary hover:bg-indigo-50 transition-all text-center">
          <input type="file" @change="handleFileChange" multiple class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" id="omics-file" />
          <label for="omics-file" class="flex flex-col p-5 pointer-events-none">
            <span class="text-sm font-medium text-slate-900">选择或拖入组学文件 (支持多选)</span>
            <small class="text-xs text-slate-500 mt-1">如果是多个文件，平台将自动取病人交集；如果是多个同一组学类型的文件，平台还将自动按特征列拼接</small>
          </label>
        </div>

        <!-- 已选文件列表 + 组学类型选择 -->
        <div v-if="omicsFileConfigs.length > 0" class="mt-4 flex flex-col gap-2">
          <div v-for="config in omicsFileConfigs" :key="config.id" class="flex justify-between items-center bg-slate-100 px-3 py-2 rounded-lg border border-slate-200">
            <span class="text-[13px] text-slate-900 whitespace-nowrap overflow-hidden text-ellipsis max-w-[60%]" :title="config.originalName">📄 {{ config.originalName }}</span>
            <select v-model="config.type" @change="handleFormatChange" class="w-[140px] px-2 py-1 border border-slate-200 rounded-lg text-[13px] bg-white cursor-pointer outline-none focus:border-primary">
              <option v-for="type in omicsTypes" :key="type" :value="type">{{ type }}</option>
            </select>
          </div>
        </div>

        <div v-show="uploadStatus" class="mt-2 text-xs p-2 rounded-lg whitespace-pre-wrap break-words" :class="uploadStatus.startsWith('❌') ? 'bg-red-50 text-red-700 border border-red-200' : uploadStatus.startsWith('✅') ? 'bg-green-50 text-green-800 border border-green-200' : ''">
          {{ uploadStatus }}
        </div>
      </div>

      <hr class="border-none border-t border-dashed border-slate-200 my-6" />

      <!-- mRNA 表达矩阵 -->
      <div>
        <h4 class="m-0 mb-3 text-sm flex items-center gap-2">mRNA 表达矩阵 <span class="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">选填</span></h4>

        <div class="flex flex-col gap-2 mb-4">
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': expressionMatrixIsRowSample }">
            <input type="checkbox" v-model="expressionMatrixIsRowSample" @change="handleExpressionMatrixFormatChange" class="hidden" />
            行代表基因，列代表样本
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': expressionMatrixHasHeader }">
            <input type="checkbox" v-model="expressionMatrixHasHeader" @change="handleExpressionMatrixFormatChange" class="hidden" />
            包含表头行
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': expressionMatrixHasIndex }">
            <input type="checkbox" v-model="expressionMatrixHasIndex" @change="handleExpressionMatrixFormatChange" class="hidden" />
            包含索引列
          </label>
        </div>

        <div class="bg-slate-800 rounded-lg p-3 mb-4">
          <div class="text-[11px] text-slate-400 mb-2 uppercase tracking-wider">TXT / CSV 格式预览</div>
          <pre class="m-0 text-slate-100 font-mono text-xs leading-relaxed overflow-x-auto">{{ expressionMatrixExampleText }}</pre>
        </div>

        <div class="relative border-2 border-dashed border-slate-200 rounded-lg bg-slate-100 hover:border-primary hover:bg-indigo-50 transition-all text-center">
          <input type="file" @change="handleExpressionMatrixFileChange" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" id="expression-matrix-file" />
          <label for="expression-matrix-file" class="flex flex-col p-5 pointer-events-none">
            <span class="text-sm font-medium text-slate-900">点击选择 mRNA 表达矩阵</span>
            <small class="text-xs text-slate-500 mt-1">用于肿瘤与正常样本差异表达分析及 GO/KEGG 富集分析；不参与聚类。</small>
          </label>
        </div>

        <div v-if="expressionMatrixFile" class="mt-4 flex justify-between items-center bg-slate-100 px-3 py-2 rounded-lg border border-slate-200">
          <span class="text-[13px] text-slate-900 whitespace-nowrap overflow-hidden text-ellipsis max-w-[80%]" :title="expressionMatrixFile.name">{{ expressionMatrixFile.name }}</span>
          <span class="text-[12px] text-slate-500">mRNA</span>
        </div>

        <div v-show="expressionMatrixUploadStatus" class="mt-2 text-xs p-2 rounded-lg whitespace-pre-wrap break-words bg-slate-50 text-slate-700 border border-slate-200">
          {{ expressionMatrixUploadStatus }}
        </div>
      </div>

      <hr class="border-none border-t border-dashed border-slate-200 my-6" />

      <!-- 临床数据 -->
      <div>
        <h4 class="m-0 mb-3 text-sm flex items-center gap-2">🏥 临床数据 <span class="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">选填</span></h4>

        <div class="flex flex-col gap-2 mb-4">
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': clinicalIsRowSample }">
            <input type="checkbox" v-model="clinicalIsRowSample" @change="handleClinicalFormatChange" class="hidden" />
            行代表特征, 列代表病人
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': clinicalHasHeader }">
            <input type="checkbox" v-model="clinicalHasHeader" @change="handleClinicalFormatChange" class="hidden" />
            包含表头行
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer px-3 py-2 rounded-lg border border-slate-200 transition-all hover:border-primary" :class="{ 'bg-indigo-50 !border-primary !text-primary font-medium': clinicalHasIndex }">
            <input type="checkbox" v-model="clinicalHasIndex" @change="handleClinicalFormatChange" class="hidden" />
            包含索引列
          </label>
        </div>

        <div class="bg-slate-800 rounded-lg p-3 mb-4">
          <div class="text-[11px] text-slate-400 mb-2 uppercase tracking-wider">CSV 格式预览</div>
          <pre class="m-0 text-slate-100 font-mono text-xs leading-relaxed overflow-x-auto">{{ clinicalExampleText }}</pre>
        </div>

        <div class="relative border-2 border-dashed border-slate-200 rounded-lg bg-slate-100 hover:border-primary hover:bg-indigo-50 transition-all text-center">
          <input type="file" @change="handleClinicalFileChange" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" id="clinical-file" />
          <label for="clinical-file" class="flex flex-col p-5 pointer-events-none">
            <span class="text-sm font-medium text-slate-900">点击选择临床文件</span>
            <small class="text-xs text-slate-500 mt-1">需包含 OS 和 OS.time</small>
          </label>
        </div>

        <div v-show="clinicalUploadStatus" class="mt-2 text-xs p-2 rounded-lg whitespace-pre-wrap break-words" :class="clinicalUploadStatus.startsWith('❌') ? 'bg-red-50 text-red-700 border border-red-200' : clinicalUploadStatus.startsWith('✅') ? 'bg-green-50 text-green-800 border border-green-200' : ''">
          {{ clinicalUploadStatus }}
        </div>
      </div>
    </div>
  </div>
</template>
