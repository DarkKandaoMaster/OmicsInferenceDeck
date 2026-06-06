<script setup lang="ts">
import {
  useResources,
  useResourceHeatmap,
  BOXPLOT_VARIANTS,
  EXAMPLE_INPUT,
  HEATMAP_EXAMPLE_INPUT,
} from '~/composables/domain/useResources'
import type { PlotFormat } from '~/utils/api'

useHead({ title: 'Resources - OmicsInferenceDeck' })

const {
  inputText, variant, svg, isLoading, isDownloading, errorMessage,
  generate, download,
} = useResources()

const {
  inputText: heatmapInput,
  svg: heatmapSvg,
  isLoading: heatmapIsLoading,
  isDownloading: heatmapIsDownloading,
  errorMessage: heatmapErrorMessage,
  generate: heatmapGenerate,
  download: heatmapDownload,
} = useResourceHeatmap()

const formats: Array<{ label: string, value: PlotFormat }> = [
  { label: 'PNG', value: 'png' },
  { label: 'SVG', value: 'svg' },
  { label: 'PDF', value: 'pdf' },
]

// 开关：关 = pvalues，开 = clinical
const isClinical = computed({
  get: () => variant.value === 'clinical',
  set: (checked: boolean) => { variant.value = checked ? 'clinical' : 'pvalues' },
})
const variantLabel = computed(
  () => BOXPLOT_VARIANTS.find(item => item.value === variant.value)?.label ?? '',
)

const downloadOpen = ref(false)
const downloadRoot = ref<HTMLElement | null>(null)

const isDragOver = ref(false)

async function handleDrop(event: DragEvent) {
  isDragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  // 读取为纯文本（CSV/TSV/txt 等文本文件）
  inputText.value = await file.text()
}

// 热力图卡片的独立下拉与拖拽状态，避免与箱线图卡片相互干扰
const heatmapDownloadOpen = ref(false)
const heatmapDownloadRoot = ref<HTMLElement | null>(null)
const heatmapIsDragOver = ref(false)

async function handleHeatmapDrop(event: DragEvent) {
  heatmapIsDragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  heatmapInput.value = await file.text()
}

function handleDocumentClick(event: MouseEvent) {
  if (!downloadRoot.value?.contains(event.target as Node)) downloadOpen.value = false
  if (!heatmapDownloadRoot.value?.contains(event.target as Node)) heatmapDownloadOpen.value = false
}
onMounted(() => document.addEventListener('click', handleDocumentClick))
onUnmounted(() => document.removeEventListener('click', handleDocumentClick))

async function handleDownload(format: PlotFormat) {
  downloadOpen.value = false
  await download(format)
}

async function handleHeatmapDownload(format: PlotFormat) {
  heatmapDownloadOpen.value = false
  await heatmapDownload(format)
}
</script>

<template>
  <div class="py-8 max-w-6xl mx-auto px-4">
    <section class="mx-auto w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <!-- 卡片头部：标题 + 说明 -->
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-3xl font-bold text-slate-900">箱线图</h3>
        <p class="mt-1 text-xs text-slate-500">
          你可以在这里绘制“各方法在x个癌症数据集上的-log10 P-values分布”或者“各方法在x个癌症数据集上的显著临床参数数量分布”。<br>
          注意输入数据需要索引列，不需要表头行。
        </p>
      </div>

      <!-- 卡片主体：输入数据 + 预览 -->
      <div class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)]">
        <!-- 输入区 -->
        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">输入数据</h4>
          <textarea
            v-model="inputText"
            rows="14"
            spellcheck="false"
            class="w-full resize-y rounded-lg border bg-slate-50 p-3 font-mono text-[13px] leading-relaxed text-slate-700 outline-none focus:border-primary"
            :class="isDragOver ? 'border-primary border-dashed bg-primary/5' : 'border-slate-200'"
            :placeholder="`示例输入：（支持直接拖入CSV/TSV格式的纯文本文件）\n${EXAMPLE_INPUT}`"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleDrop"
          />
          <label class="mt-4 flex w-full max-w-[280px] cursor-pointer items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
            <span>
              <span class="block text-sm font-semibold text-slate-900">我想绘制：</span>
              <span class="block text-xs text-slate-500">{{ variantLabel }}</span>
            </span>
            <span class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors" :class="isClinical ? 'bg-primary' : 'bg-slate-300'">
              <input v-model="isClinical" type="checkbox" class="sr-only" />
              <span class="h-[18px] w-[18px] rounded-full bg-white transition-transform" :class="isClinical ? 'translate-x-5' : 'translate-x-[3px]'" />
            </span>
          </label>
          <div class="mt-4 flex items-center gap-3">
            <button
              type="button"
              class="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="isLoading"
              @click="generate"
            >
              {{ isLoading ? '生成中...' : '生成图表' }}
            </button>
            <p v-if="errorMessage" class="text-[13px] text-red-600">{{ errorMessage }}</p>
          </div>
        </div>

        <div class="h-px bg-slate-200 lg:h-auto lg:w-px" />

        <!-- 预览区 -->
        <div>
          <div class="mb-3 flex items-center justify-between gap-3">
            <h4 class="m-0 text-sm font-semibold text-slate-900">图表预览</h4>
            <div ref="downloadRoot" class="relative inline-flex">
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-[13px] text-slate-700 hover:bg-slate-100 disabled:opacity-60 disabled:cursor-not-allowed"
                :disabled="!svg || !!isDownloading"
                @click.stop="downloadOpen = !downloadOpen"
              >
                {{ isDownloading ? 'Preparing...' : 'Download' }}
              </button>
              <div
                v-if="downloadOpen"
                class="absolute right-0 top-full z-20 mt-2 min-w-[96px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
              >
                <button
                  v-for="item in formats"
                  :key="item.value"
                  type="button"
                  class="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                  :disabled="!!isDownloading"
                  @click.stop="handleDownload(item.value)"
                >
                  {{ item.label }}
                </button>
              </div>
            </div>
          </div>
          <div class="overflow-hidden rounded-lg border border-slate-200 bg-slate-50/50">
            <div v-if="svg" class="svg-chart" v-html="svg" />
            <div v-else class="svg-chart text-slate-400 text-sm">
              生成图表后在此预览。
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 第二张卡片：综合评分热力图 -->
    <section class="mx-auto mt-8 w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <!-- 卡片头部：标题 + 说明 -->
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-3xl font-bold text-slate-900">综合评分热力图</h3>
        <p class="mt-1 text-xs text-slate-500">
          把「算法 × 癌症类型」的二维评分矩阵渲染成热力图：单元格两位小数标注、3D-AWA score 颜色条、红框圈出每列最大值。<br>
          注意输入数据需要表头行和索引列。
        </p>
      </div>

      <!-- 卡片主体：输入数据 + 预览 -->
      <div class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)]">
        <!-- 输入区 -->
        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">输入数据</h4>
          <textarea
            v-model="heatmapInput"
            rows="14"
            spellcheck="false"
            class="w-full resize-y rounded-lg border bg-slate-50 p-3 font-mono text-[13px] leading-relaxed text-slate-700 outline-none focus:border-primary"
            :class="heatmapIsDragOver ? 'border-primary border-dashed bg-primary/5' : 'border-slate-200'"
            :placeholder="`示例输入：（支持直接拖入CSV/TSV格式的纯文本文件）\n${HEATMAP_EXAMPLE_INPUT}`"
            @dragover.prevent="heatmapIsDragOver = true"
            @dragleave.prevent="heatmapIsDragOver = false"
            @drop.prevent="handleHeatmapDrop"
          />
          <div class="mt-4 flex items-center gap-3">
            <button
              type="button"
              class="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="heatmapIsLoading"
              @click="heatmapGenerate"
            >
              {{ heatmapIsLoading ? '生成中...' : '生成图表' }}
            </button>
            <p v-if="heatmapErrorMessage" class="text-[13px] text-red-600">{{ heatmapErrorMessage }}</p>
          </div>
        </div>

        <div class="h-px bg-slate-200 lg:h-auto lg:w-px" />

        <!-- 预览区 -->
        <div>
          <div class="mb-3 flex items-center justify-between gap-3">
            <h4 class="m-0 text-sm font-semibold text-slate-900">图表预览</h4>
            <div ref="heatmapDownloadRoot" class="relative inline-flex">
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-[13px] text-slate-700 hover:bg-slate-100 disabled:opacity-60 disabled:cursor-not-allowed"
                :disabled="!heatmapSvg || !!heatmapIsDownloading"
                @click.stop="heatmapDownloadOpen = !heatmapDownloadOpen"
              >
                {{ heatmapIsDownloading ? 'Preparing...' : 'Download' }}
              </button>
              <div
                v-if="heatmapDownloadOpen"
                class="absolute right-0 top-full z-20 mt-2 min-w-[96px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
              >
                <button
                  v-for="item in formats"
                  :key="item.value"
                  type="button"
                  class="block w-full px-3 py-2 text-left text-[13px] text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                  :disabled="!!heatmapIsDownloading"
                  @click.stop="handleHeatmapDownload(item.value)"
                >
                  {{ item.label }}
                </button>
              </div>
            </div>
          </div>
          <div class="overflow-hidden rounded-lg border border-slate-200 bg-slate-50/50">
            <div v-if="heatmapSvg" class="svg-chart" v-html="heatmapSvg" />
            <div v-else class="svg-chart text-slate-400 text-sm">
              生成图表后在此预览。
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
