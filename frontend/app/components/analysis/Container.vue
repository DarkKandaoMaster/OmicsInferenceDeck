<script setup lang="ts">
import { useDataState } from '~/composables/domain/useDataState'
import { useUIState } from '~/composables/core/useUIState'

const { isCustomEvalMode, customEvalUploadStatus, handleCustomEvalFileChange } = useDataState()
const { errorMessage } = useUIState()
</script>

<template>
  <div>
    <!-- 配置区 -->
    <div class="grid grid-cols-3 gap-6 mb-8 items-start">
      <!-- 第1栏：数据上传 -->
      <AnalysisDataUpload />

      <!-- 第2+3栏：算法选择 + 参数配置（非自定义模式） -->
      <AnalysisAlgorithmSelect v-if="!isCustomEvalMode" class="col-span-2" />

      <!-- 自定义模式：结果数据上传卡 -->
      <div v-else class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
        <div class="bg-slate-50 px-5 py-4 border-b border-slate-200 flex items-center gap-2.5">
          <span>📥</span>
          <h3 class="m-0 text-base font-semibold text-slate-900">2. 结果数据上传</h3>
        </div>
        <div class="p-5">
          <h4 class="m-0 mb-3 text-sm flex items-center gap-2">📊 聚类结果与特征矩阵 <span class="text-[11px] px-1.5 py-0.5 rounded bg-red-100 text-red-700">必填</span></h4>
          <p class="text-[13px] text-slate-500 mb-3 leading-relaxed">
            请把你上传的组学数据作为输入，用你自己的算法，生成一个CSV/Excel文件：<br>
            1.从左到右分别是<br>
            <strong>病人名称</strong>（索引列）、<br>
            <strong>聚类结果</strong>（第2列）、<br>
            <strong>融合后的特征矩阵</strong>（第3列及之后）。<br>
            2.行代表病人，列代表特征。有表头行、索引列。
          </p>
          <div class="relative border-2 border-dashed border-slate-200 rounded-lg bg-slate-100 hover:border-primary hover:bg-indigo-50 transition-all text-center">
            <input type="file" @change="handleCustomEvalFileChange($event)" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" accept=".csv, .xlsx, .xls" />
            <div class="flex flex-col p-5 pointer-events-none">
              <span class="text-sm font-medium text-slate-900">点击选择结果数据文件</span>
            </div>
          </div>
          <div v-show="customEvalUploadStatus" class="mt-2 text-xs p-2 rounded-lg bg-green-50 text-green-800 border border-green-200">
            {{ customEvalUploadStatus }}
          </div>
        </div>
      </div>
    </div>

    <!-- 运行按钮 -->
    <AnalysisActions />

    <!-- 全局错误 -->
    <div v-if="errorMessage" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl mb-8 flex items-center gap-3 font-medium">
      <span>❌</span> {{ errorMessage }}
    </div>

    <!-- 结果区域 -->
    <ResultsContainer />
  </div>
</template>
