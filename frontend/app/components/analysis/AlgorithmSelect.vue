<script setup lang="ts">
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
const { algorithms, selectedAlgorithm, isTestMode, testNClusters, testMaxIter, testNNeighbors, randomSeed, kValue, maxIter, nNeighbors } = useAlgorithmState()
</script>

<template>
  <div class="col-span-2 grid grid-cols-2 gap-6 items-start">
    <!-- 左半：算法选择 -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
      <div class="bg-slate-50 px-5 py-4 border-b border-slate-200 flex items-center gap-2.5">
        <span>⚙️</span>
        <h3 class="m-0 text-base font-semibold text-slate-900">2. 算法选择</h3>
      </div>
      <div class="p-5">
        <!-- 测试模式开关 -->
        <div class="flex items-center gap-3 p-4 rounded-lg border mb-6 transition-all" :class="isTestMode ? 'bg-red-50 border-red-200' : 'border-slate-200'">
          <label class="relative inline-block w-11 h-6 cursor-pointer">
            <input v-model="isTestMode" type="checkbox" class="sr-only peer" />
            <span class="absolute inset-0 bg-gray-300 rounded-full transition-colors peer-checked:bg-red-500" />
            <span class="absolute left-[3px] bottom-[3px] w-[18px] h-[18px] bg-white rounded-full transition-transform peer-checked:translate-x-5" />
          </label>
          <div>
            <strong class="block text-sm" :class="isTestMode ? 'text-red-600' : 'text-slate-900'">开启测试模式</strong>
            <span class="text-xs text-slate-500">执行参数敏感性分析</span>
          </div>
        </div>

        <!-- 算法列表 -->
        <h4 class="text-[13px] text-slate-500 uppercase mb-3">可用聚类算法</h4>
        <div class="flex flex-col gap-2">
          <label
            v-for="algo in algorithms"
            :key="algo"
            class="flex items-center justify-between px-4 py-3 rounded-lg border cursor-pointer transition-all"
            :class="selectedAlgorithm.includes(algo) ? 'border-primary bg-indigo-50' : 'border-slate-200 hover:border-blue-400 hover:bg-slate-100'"
          >
            <span class="flex items-center gap-2">
              <input type="checkbox" v-model="selectedAlgorithm" :value="algo" class="hidden" />
              <span class="text-sm font-medium">{{ algo }}</span>
            </span>
            <span v-if="selectedAlgorithm.includes(algo)" class="text-primary font-bold">✓</span>
          </label>
        </div>
      </div>
    </div>

    <!-- 右半：参数配置 -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
      <div class="bg-slate-50 px-5 py-4 border-b border-slate-200 flex items-center gap-2.5">
        <span>🎛️</span>
        <h3 class="m-0 text-base font-semibold text-slate-900">3. 参数配置</h3>
      </div>
      <div class="p-5 flex-1">
        <!-- 未选算法时的空状态 -->
        <div v-if="selectedAlgorithm.length === 0" class="flex flex-col items-center justify-center min-h-[200px] text-slate-500">
          <span class="text-3xl mb-2 opacity-50">👈</span>
          <p>请先在左侧选择一种算法</p>
        </div>

        <div v-else class="flex flex-col gap-5">
          <!-- 常规参数模式 -->
          <template v-if="!isTestMode">
            <div v-if="selectedAlgorithm.includes('K-means')" class="bg-slate-100 p-4 rounded-lg border border-slate-200">
              <h4 class="m-0 mb-4 text-sm text-primary font-semibold border-b border-black/5 pb-2">K-means 参数</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数 (K值)</label>
                <input type="number" v-model="kValue" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">随机种子 (-1表示None)</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">最大迭代</label>
                <input type="number" v-model="maxIter" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('Spectral Clustering')" class="bg-slate-100 p-4 rounded-lg border border-slate-200">
              <h4 class="m-0 mb-4 text-sm text-primary font-semibold border-b border-black/5 pb-2">Spectral Clustering 参数</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数 (K值)</label>
                <input type="number" v-model="kValue" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">邻居数 (n_neighbors)</label>
                <input type="number" v-model="nNeighbors" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子 (-1表示None)</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('NEMO')" class="bg-slate-100 p-4 rounded-lg border border-slate-200">
              <h4 class="m-0 mb-4 text-sm text-primary font-semibold border-b border-black/5 pb-2">NEMO 参数</h4>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数 (K值)</label>
                <input type="number" v-model="kValue" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('SNF')" class="bg-slate-100 p-4 rounded-lg border border-slate-200">
              <h4 class="m-0 mb-4 text-sm text-primary font-semibold border-b border-black/5 pb-2">SNF 参数</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数 (K值)</label>
                <input type="number" v-model="kValue" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">构建KNN网络邻居数 (K)</label>
                <input type="number" v-model="nNeighbors" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('MOSD')" class="bg-slate-100 p-4 rounded-lg border border-slate-200">
              <h4 class="m-0 mb-4 text-sm text-primary font-semibold border-b border-black/5 pb-2">MOSD 参数</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数 (K值)</label>
                <input type="number" v-model="kValue" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子 (-1表示None)</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>
          </template>

          <!-- 测试模式参数 -->
          <template v-else>
            <div class="bg-amber-50 border border-orange-200 p-3 rounded-lg text-[13px] text-amber-700 mb-4">
              ⚠️ 测试模式需利用临床文件计算P-value，请确保已上传。
            </div>

            <div v-if="selectedAlgorithm.includes('K-means')" class="bg-amber-50 p-4 rounded-lg border border-orange-200">
              <h4 class="m-0 mb-4 text-sm text-amber-600 font-semibold border-b border-black/5 pb-2">K-means 测试范围</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数范围 (逗号分隔)</label>
                <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">最大迭代范围 (逗号分隔)</label>
                <input type="text" v-model="testMaxIter" placeholder="如: 100,200,300" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('Spectral Clustering')" class="bg-amber-50 p-4 rounded-lg border border-orange-200">
              <h4 class="m-0 mb-4 text-sm text-amber-600 font-semibold border-b border-black/5 pb-2">Spectral Clustering 测试范围</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数范围 (逗号分隔)</label>
                <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">邻居数范围 (逗号分隔)</label>
                <input type="text" v-model="testNNeighbors" placeholder="如: 5,10,15" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('NEMO')" class="bg-amber-50 p-4 rounded-lg border border-orange-200">
              <h4 class="m-0 mb-4 text-sm text-amber-600 font-semibold border-b border-black/5 pb-2">NEMO 测试范围</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数范围 (逗号分隔)</label>
                <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('SNF')" class="bg-amber-50 p-4 rounded-lg border border-orange-200">
              <h4 class="m-0 mb-4 text-sm text-amber-600 font-semibold border-b border-black/5 pb-2">SNF 测试范围</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数范围 (逗号分隔)</label>
                <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">邻居数范围 (逗号分隔)</label>
                <input type="text" v-model="testNNeighbors" placeholder="如: 10,20,30" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>

            <div v-if="selectedAlgorithm.includes('MOSD')" class="bg-amber-50 p-4 rounded-lg border border-orange-200">
              <h4 class="m-0 mb-4 text-sm text-amber-600 font-semibold border-b border-black/5 pb-2">MOSD 测试范围</h4>
              <div class="mb-3">
                <label class="block text-xs text-slate-700 mb-1.5">聚类簇数范围 (逗号分隔)</label>
                <input type="text" v-model="testNClusters" placeholder="如: 2,3,4,5" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
              <div>
                <label class="block text-xs text-slate-700 mb-1.5">随机种子</label>
                <input type="number" v-model="randomSeed" class="w-full px-3 py-2 border border-slate-200 rounded-lg text-[13px] text-slate-900 transition-all focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
