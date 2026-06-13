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
  testLatentDim,
  randomSeed,
  kValue,
  maxIter,
  nNeighbors,
  kmeansNInit,
  kmeansTol,
  kmeansInit,
  spectralAssignLabels,
  spectralNInit,
  hclustMethod,
  hclustDistance,
  snfAlpha,
  snfIterations,
  pintmfLatentDim,
  pintmfMaxIter,
  pintmfMaxFeatures,
  nemoNNeighbors,
  pareaStructure,
} = useAlgorithmState()

// 下拉选项（合法取值由 sklearn / R 脚本校验）
const kmeansInitOptions = ['k-means++', 'random']
const spectralAssignOptions = ['kmeans', 'discretize', 'cluster_qr']
const hclustMethodOptions = ['ward.D', 'ward.D2', 'single', 'complete', 'average', 'mcquitty', 'median', 'centroid']
const hclustDistanceOptions = ['euclidean', 'maximum', 'manhattan', 'canberra', 'binary', 'minkowski']
const pareaStructureOptions = [
  { value: '2', label: '2 - 双层集成 (默认)' },
  { value: '1', label: '1 - 单层集成' },
]

const {
  isCustomEvalMode, customEvalFile, isCustomEvalTestMode, handleCustomEvalFileChange, clearCustomEvalFile,
  customEvalMatFile, matXCol, matYCol, matScoreCol, matXLabel, matYLabel,
  handleCustomEvalMatFileChange, clearCustomEvalMatFile,
} = useDataState()

const algorithmsWithK = ['K-means', 'Spectral Clustering', 'NEMO', 'SNF', 'Hclust', 'PIntMF', 'MOSD', 'Parea']
const algorithmsWithSeed = ['K-means', 'Spectral Clustering', 'Hclust', 'PIntMF', 'MOSD', 'Parea']

const selectedAlgorithmsWithParams = computed(() => selectedAlgorithm.value.filter(algo => algorithmsWithK.includes(algo)))
const hasSelectedAlgorithm = computed(() => selectedAlgorithm.value.length > 0)
</script>

<template>
  <section v-if="isCustomEvalMode" class="mx-auto w-full max-w-5xl rounded-lg border border-slate-200 bg-white shadow-sm">
    <div class="flex flex-col gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4 md:flex-row md:items-center md:justify-between">
      <h3 class="m-0 text-base font-semibold text-slate-900">2. 上传自己算法生成的结果文件</h3>
      <label class="flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg border px-4 py-3 md:w-[280px]" :class="isCustomEvalTestMode ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-white'">
        <span>
          <span class="block text-sm font-semibold" :class="isCustomEvalTestMode ? 'text-amber-700' : 'text-slate-900'">参数敏感性分析</span>
          <span class="block text-xs text-slate-500">按参数范围运行搜索</span>
        </span>
        <span class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors" :class="isCustomEvalTestMode ? 'bg-amber-500' : 'bg-slate-300'">
          <input v-model="isCustomEvalTestMode" type="checkbox" class="sr-only" />
          <span class="h-[18px] w-[18px] rounded-full bg-white transition-transform" :class="isCustomEvalTestMode ? 'translate-x-5' : 'translate-x-[3px]'" />
        </span>
      </label>
    </div>
    <!-- 默认：上传自定义聚类结果（CSV/XLSX） -->
    <div v-if="!isCustomEvalTestMode" class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <p class="mb-4 text-[13px] leading-relaxed text-slate-500">
          请把您上传的组学数据作为输入，用您自己的算法，生成一个CSV/TSV/XLSX文件：<br>
          1. 从左到右分别是<br>
          <strong>病人名称</strong>（索引列）、<br>
          <strong>聚类结果</strong>（第2列）、<br>
          <strong>融合后的特征矩阵</strong>（第3列及之后）（可选）。<br>
          2. 有表头行。
        </p>
        <div class="relative rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 text-center transition-all hover:border-primary hover:bg-indigo-50">
          <input type="file" accept=".csv,.xlsx,.xls" class="absolute inset-0 h-full w-full cursor-pointer opacity-0" @change="handleCustomEvalFileChange($event)" />
          <div class="flex min-h-[116px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
            <span class="text-sm font-semibold text-slate-900">点击选择结果数据文件</span>
            <span class="mt-1 text-xs text-slate-500">CSV / TSV / XLSX</span>
          </div>
        </div>
        <div v-if="customEvalFile" class="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <span class="truncate text-[13px] text-slate-900" :title="customEvalFile.name">{{ customEvalFile.name }}</span>
          <button type="button" aria-label="移除" title="移除" class="flex h-7 w-7 items-center justify-center text-slate-500 hover:text-red-600" @click="clearCustomEvalFile()">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
      </div>

      <div class="rounded-lg bg-slate-900 p-4">
        <div class="mb-2 text-[11px] font-semibold uppercase text-slate-400">CSV 格式预览</div>
        <pre class="m-0 overflow-x-auto whitespace-pre text-xs leading-relaxed text-slate-100">patient,cluster,feature_1,feature_2,...
TCGA-01,1,0.42,0.18,...
TCGA-02,2,0.31,0.66,...
TCGA-03,1,0.58,0.21,...
...</pre>
      </div>
    </div>

    <!-- 参数敏感性分析：上传结果 .mat，直接读取指定列绘制敏感性曲面图 -->
    <div v-else class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <p class="mb-4 text-[13px] leading-relaxed text-slate-500">
          请把您参数扫描产生的.mat结果文件作为输入，平台会直接读取其中<strong>首个数据变量</strong>里的列绘制参数敏感性图，而无需上传组学/临床等数据。<br>
          输入X列号、Y列号时需注意，列号应从1起始。允许Y列号留空，平台将仅按X列号绘制2D敏感性曲线。
        </p>

        <div class="mt-4 flex flex-col gap-2">
          <label class="flex items-center gap-2 text-[13px] text-slate-700">
            <span class="shrink-0">X轴名称:</span>
            <input v-model="matXLabel" type="text" placeholder="gamma"
              class="w-48 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            <span class="shrink-0">X列号:</span>
            <input v-model.number="matXCol" type="number" min="1"
              class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none w-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700">
            <span class="shrink-0">Y轴名称:</span>
            <input v-model="matYLabel" type="text" placeholder="delta"
              class="w-48 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            <span class="shrink-0">Y列号:</span>
            <input v-model.number="matYCol" type="number" min="1" placeholder="留空画 2D"
              class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none w-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
          </label>
          <label class="flex items-center gap-2 text-[13px] text-slate-700">
            <span class="shrink-0">−log10(p)列号:</span>
            <input v-model.number="matScoreCol" type="number" min="1"
              class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none w-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
          </label>
        </div>

        <div class="relative mt-4 rounded-lg border-2 border-dashed border-amber-200 bg-amber-50/60 text-center transition-all hover:border-amber-400 hover:bg-amber-50">
          <input type="file" accept=".mat" class="absolute inset-0 h-full w-full cursor-pointer opacity-0" @change="handleCustomEvalMatFileChange($event)" />
          <div class="flex min-h-[116px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
            <span class="text-sm font-semibold text-slate-900">点击选择 .mat 结果文件</span>
            <span class="mt-1 text-xs text-slate-500">MATLAB .mat</span>
          </div>
        </div>
        <div v-if="customEvalMatFile" class="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <span class="truncate text-[13px] text-slate-900" :title="customEvalMatFile.name">{{ customEvalMatFile.name }}</span>
          <button type="button" aria-label="移除" title="移除" class="flex h-7 w-7 items-center justify-center text-slate-500 hover:text-red-600" @click="clearCustomEvalMatFile()">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
      </div>

      <div class="rounded-lg bg-slate-900 p-4">
        <div class="mb-2 text-[11px] font-semibold uppercase text-slate-400">.mat 列语义</div>
        <pre class="m-0 overflow-x-auto whitespace-pre text-xs leading-relaxed text-slate-100">results = N×18 矩阵
 第15列  gamma        → X 轴
 第16列  delta        → Y 轴
 第17列  -log10(p)    → 高度(Z)</pre>
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

              <!-- K-means 额外参数 -->
              <template v-if="algo === 'K-means'">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">初始化次数 (n_init)</span>
                  <input v-model.number="kmeansNInit" type="number" min="1" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">收敛阈值 (tol)</span>
                  <input v-model.number="kmeansTol" type="number" step="0.0001" min="0" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">初始化方式 (init)</span>
                  <select v-model="kmeansInit" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10">
                    <option v-for="opt in kmeansInitOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </label>
              </template>

              <!-- Spectral 额外参数 -->
              <template v-if="algo === 'Spectral Clustering'">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">标签分配方式 (assign_labels)</span>
                  <select v-model="spectralAssignLabels" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10">
                    <option v-for="opt in spectralAssignOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">初始化次数 (n_init)</span>
                  <input v-model.number="spectralNInit" type="number" min="1" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
              </template>

              <!-- Hclust 额外参数 -->
              <template v-if="algo === 'Hclust'">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">连接方式 (method)</span>
                  <select v-model="hclustMethod" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10">
                    <option v-for="opt in hclustMethodOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">距离度量 (distance)</span>
                  <select v-model="hclustDistance" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10">
                    <option v-for="opt in hclustDistanceOptions" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </label>
              </template>

              <!-- SNF 额外参数 -->
              <template v-if="algo === 'SNF'">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">高斯核参数 σ (alpha)</span>
                  <input v-model.number="snfAlpha" type="number" step="0.1" min="0" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">扩散迭代次数 (T)</span>
                  <input v-model.number="snfIterations" type="number" min="1" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
              </template>

              <!-- PIntMF 额外参数 -->
              <template v-if="algo === 'PIntMF'">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">隐变量维度 (latent_dim，≥2，默认随 K)</span>
                  <input v-model.number="pintmfLatentDim" type="number" min="2" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">最大迭代 (max_iter)</span>
                  <input v-model.number="pintmfMaxIter" type="number" min="1" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-medium text-slate-700">每组学最大特征数 (max_features)</span>
                  <input v-model.number="pintmfMaxFeatures" type="number" min="1" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
              </template>

              <!-- NEMO 额外参数 -->
              <label v-if="algo === 'NEMO'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">邻居数 (n_neighbors，0=自动)</span>
                <input v-model.number="nemoNNeighbors" type="number" min="0" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>

              <!-- Parea 额外参数 -->
              <label v-if="algo === 'Parea'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">集成结构 (structure)</span>
                <select v-model="pareaStructure" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10">
                  <option v-for="opt in pareaStructureOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </label>

              <label v-if="algorithmsWithSeed.includes(algo)" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">随机种子 (-1 表示 None)</span>
                <input v-model="randomSeed" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
            </div>
          </div>

          <!-- Subtype-GAN 后端未实现，暂时注释掉
          <div v-if="selectedAlgorithm.includes('Subtype-GAN')" class="rounded-lg border border-slate-200 bg-white p-4">
            <h4 class="m-0 mb-2 text-sm font-semibold text-slate-900">Subtype-GAN</h4>
            <p class="m-0 text-[13px] leading-relaxed text-slate-500">该算法当前使用平台默认参数。</p>
          </div>
          -->
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
              <label v-if="algo === 'Spectral Clustering' || algo === 'SNF' || algo === 'NEMO'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">邻居数范围 (逗号分隔){{ algo === 'NEMO' ? '（0=自动）' : '' }}</span>
                <input v-model="testNNeighbors" type="text" placeholder="如: 5,10,15" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algo === 'PIntMF'" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">latent_dim 范围 (逗号分隔，≥2)</span>
                <input v-model="testLatentDim" type="text" placeholder="如: 2,3,4,5" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>
              <label v-if="algorithmsWithSeed.includes(algo)" class="block">
                <span class="mb-1.5 block text-xs font-medium text-slate-700">随机种子</span>
                <input v-model="randomSeed" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </label>

              <!-- 固定参数说明：以下枚举/标量参数取自“普通模式”设置，在本次扫描中作为固定值参与。这些固定值直接取自你在「普通模式」里给该算法设置的参数。所以那行说明的作用就是告诉你：“这次扫描中，这些参数会被锁定成普通模式里的当前取值”。如果你想换，就回普通模式改，再回来跑扫描。 -->
              <p v-if="algo === 'K-means'" class="m-0 text-xs leading-relaxed text-slate-500">
                固定参数（已锁定为当前普通模式里的值）：n_init={{ kmeansNInit }}、tol={{ kmeansTol }}、init={{ kmeansInit }}
              </p>
              <p v-else-if="algo === 'Spectral Clustering'" class="m-0 text-xs leading-relaxed text-slate-500">
                固定参数（已锁定为当前普通模式里的值）：assign_labels={{ spectralAssignLabels }}、n_init={{ spectralNInit }}
              </p>
              <p v-else-if="algo === 'Hclust'" class="m-0 text-xs leading-relaxed text-slate-500">
                固定参数（已锁定为当前普通模式里的值）：method={{ hclustMethod }}、distance={{ hclustDistance }}
              </p>
              <p v-else-if="algo === 'SNF'" class="m-0 text-xs leading-relaxed text-slate-500">
                固定参数（已锁定为当前普通模式里的值）：alpha={{ snfAlpha }}、T={{ snfIterations }}
              </p>
              <p v-else-if="algo === 'PIntMF'" class="m-0 text-xs leading-relaxed text-slate-500">
                固定参数（已锁定为当前普通模式里的值）：max_iter={{ pintmfMaxIter }}、max_features={{ pintmfMaxFeatures }}
              </p>
              <p v-else-if="algo === 'Parea'" class="m-0 text-xs leading-relaxed text-slate-500">
                固定参数（已锁定为当前普通模式里的值）：structure={{ pareaStructure }}
              </p>
            </div>
          </div>

          <!-- Subtype-GAN 后端未实现，暂时注释掉
          <div v-if="selectedAlgorithm.includes('Subtype-GAN')" class="rounded-lg border border-slate-200 bg-white p-4">
            <h4 class="m-0 mb-2 text-sm font-semibold text-slate-900">Subtype-GAN</h4>
            <p class="m-0 text-[13px] leading-relaxed text-slate-500">该算法当前没有可配置的敏感性分析参数。</p>
          </div>
          -->
        </div>
      </div>
    </div>
  </section>
</template>
