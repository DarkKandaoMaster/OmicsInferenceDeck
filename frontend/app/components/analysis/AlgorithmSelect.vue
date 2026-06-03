<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useDataState } from '~/composables/domain/useDataState'

const {
  algorithms,
  selectedAlgorithm,
  isTestMode,
  testNClusters,
  testMaxIter,
  testNNeighbors,
  randomSeed,
  kValue,
  maxIter,
  nNeighbors,
} = useAlgorithmState()

const { isCustomEvalMode, customEvalFile, customEvalUploadStatus, handleCustomEvalFileChange, clearCustomEvalFile } = useDataState()

const algorithmsWithK = ['K-means', 'Spectral Clustering', 'NEMO', 'SNF', 'Hclust', 'PIntMF', 'MOSD', 'Parea']
const algorithmsWithSeed = ['K-means', 'Spectral Clustering', 'Hclust', 'PIntMF', 'MOSD', 'Parea']

const selectedAlgorithmsWithParams = computed(() => selectedAlgorithm.value.filter(algo => algorithmsWithK.includes(algo)))
const hasSelectedAlgorithm = computed(() => selectedAlgorithm.value.length > 0)
</script>

<template>
  <section v-if="isCustomEvalMode" class="mx-auto w-full max-w-5xl rounded-lg border border-slate-200 bg-white shadow-sm">
    <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
      <h3 class="m-0 text-base font-semibold text-slate-900">2. 上传自己算法生成的结果文件</h3>
    </div>
    <div class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <p class="mb-4 text-[13px] leading-relaxed text-slate-500">
          请把你上传的组学数据作为输入，用你自己的算法，生成一个CSV/Excel文件：<br>
          1.从左到右分别是<br>
          <strong>病人名称</strong>（索引列）、<br>
          <strong>聚类结果</strong>（第2列）、<br>
          <strong>融合后的特征矩阵</strong>（第3列及之后）。<br>
          2.行代表病人，列代表特征。有表头行、索引列。
        </p>
        <div class="relative rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 text-center transition-all hover:border-primary hover:bg-indigo-50">
          <input type="file" accept=".csv,.xlsx,.xls" class="absolute inset-0 h-full w-full cursor-pointer opacity-0" @change="handleCustomEvalFileChange($event)" />
          <div class="flex min-h-[116px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
            <span class="text-sm font-semibold text-slate-900">点击选择结果数据文件</span>
            <span class="mt-1 text-xs text-slate-500">CSV / XLSX / XLS</span>
          </div>
        </div>
        <div v-if="customEvalFile" class="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <span class="truncate text-[13px] text-slate-900" :title="customEvalFile.name">{{ customEvalFile.name }}</span>
          <button type="button" aria-label="移除" title="移除" class="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 hover:border-red-300 hover:text-red-600" @click="clearCustomEvalFile()">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div v-show="customEvalUploadStatus" class="mt-3 rounded-lg border border-green-200 bg-green-50 p-2 text-xs text-green-800">
          {{ customEvalUploadStatus }}
        </div>
      </div>

      <div class="rounded-lg bg-slate-900 p-4">
        <div class="mb-2 text-[11px] font-semibold uppercase text-slate-400">CSV 格式预览</div>
        <pre class="m-0 overflow-x-auto whitespace-pre text-xs leading-relaxed text-slate-100">patient,cluster,feature_1,feature_2,...
TCGA-01,1,0.42,0.18,...
TCGA-02,2,0.31,0.66,...
TCGA-03,1,0.58,0.21,...</pre>
      </div>
    </div>
  </section>

  <section v-else class="mx-auto w-full max-w-5xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
    <div class="flex flex-col gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h3 class="m-0 text-base font-semibold text-slate-900">2. 选择平台内置算法和参数</h3>
        <p class="mt-1 text-xs text-slate-500">可选择一个或多个无监督聚类算法；参数敏感性分析会切换为范围输入。</p>
      </div>
      <label class="flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg border px-4 py-3 md:w-[280px]" :class="isTestMode ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-white'">
        <span>
          <span class="block text-sm font-semibold" :class="isTestMode ? 'text-amber-700' : 'text-slate-900'">参数敏感性分析</span>
          <span class="block text-xs text-slate-500">按参数范围运行搜索</span>
        </span>
        <span class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors" :class="isTestMode ? 'bg-amber-500' : 'bg-slate-300'">
          <input v-model="isTestMode" type="checkbox" class="sr-only" />
          <span class="h-[18px] w-[18px] rounded-full bg-white transition-transform" :class="isTestMode ? 'translate-x-5' : 'translate-x-[3px]'" />
        </span>
      </label>
    </div>

    <div class="grid gap-5 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
      <div>
        <h4 class="mb-3 mt-0 text-sm font-semibold text-slate-900">可用算法</h4>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-1">
          <label
            v-for="algo in algorithms"
            :key="algo"
            class="flex min-h-[48px] cursor-pointer items-center justify-between rounded-lg border px-4 py-3 transition-all"
            :class="selectedAlgorithm.includes(algo) ? 'border-primary bg-indigo-50 text-primary' : 'border-slate-200 text-slate-800 hover:border-primary hover:bg-slate-50'"
          >
            <span class="text-sm font-medium">{{ algo }}</span>
            <input v-model="selectedAlgorithm" type="checkbox" :value="algo" class="sr-only" />
            <span v-if="selectedAlgorithm.includes(algo)" class="ml-auto inline-block h-2 w-2 shrink-0 rounded-full bg-primary" />
          </label>
        </div>
      </div>

      <div class="min-h-[260px] rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div v-if="!hasSelectedAlgorithm" class="flex h-full min-h-[220px] items-center justify-center text-sm text-slate-500">
          请先选择至少一种算法。
        </div>

        <div v-else-if="!isTestMode" class="grid gap-4 md:grid-cols-2">
          <div v-for="algo in selectedAlgorithmsWithParams" :key="algo" class="rounded-lg border border-slate-200 bg-white p-4">
            <h4 class="m-0 mb-4 border-b border-slate-100 pb-2 text-sm font-semibold text-primary">{{ algo }} 参数</h4>
            <div class="grid gap-3">
              <label class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">聚类簇数 (K值)</span>
                <input v-model="kValue" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algo === 'K-means'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">最大迭代</span>
                <input v-model="maxIter" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algo === 'Spectral Clustering' || algo === 'SNF'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">{{ algo === 'SNF' ? '构建 KNN 网络邻居数 (K)' : '邻居数 (n_neighbors)' }}</span>
                <input v-model="nNeighbors" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algorithmsWithSeed.includes(algo)" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">随机种子 (-1 表示 None)</span>
                <input v-model="randomSeed" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
            </div>
          </div>

          <div v-if="selectedAlgorithm.includes('Subtype-GAN')" class="rounded-lg border border-slate-200 bg-white p-4">
            <h4 class="m-0 mb-2 text-sm font-semibold text-slate-900">Subtype-GAN</h4>
            <p class="m-0 text-[13px] leading-relaxed text-slate-500">该算法当前使用平台默认参数。</p>
          </div>
        </div>

        <div v-else class="grid gap-4 md:grid-cols-2">
          <div class="rounded-lg border border-amber-200 bg-amber-50 p-4 md:col-span-2">
            <p class="m-0 text-[13px] leading-relaxed text-amber-700">参数敏感性分析需利用临床文件计算 P-value，请确保已上传临床数据。</p>
          </div>

          <div v-for="algo in selectedAlgorithmsWithParams" :key="algo" class="rounded-lg border border-amber-200 bg-white p-4">
            <h4 class="m-0 mb-4 border-b border-slate-100 pb-2 text-sm font-semibold text-amber-700">{{ algo }} 测试范围</h4>
            <div class="grid gap-3">
              <label class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">聚类簇数范围 (逗号分隔)</span>
                <input v-model="testNClusters" type="text" placeholder="如: 2,3,4,5" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algo === 'K-means'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">最大迭代范围 (逗号分隔)</span>
                <input v-model="testMaxIter" type="text" placeholder="如: 100,200,300" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algo === 'Spectral Clustering' || algo === 'SNF'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">邻居数范围 (逗号分隔)</span>
                <input v-model="testNNeighbors" type="text" placeholder="如: 5,10,15" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algorithmsWithSeed.includes(algo)" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">随机种子</span>
                <input v-model="randomSeed" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
            </div>
          </div>

          <div v-if="selectedAlgorithm.includes('Subtype-GAN')" class="rounded-lg border border-slate-200 bg-white p-4">
            <h4 class="m-0 mb-2 text-sm font-semibold text-slate-900">Subtype-GAN</h4>
            <p class="m-0 text-[13px] leading-relaxed text-slate-500">该算法当前没有可配置的敏感性分析参数。</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
