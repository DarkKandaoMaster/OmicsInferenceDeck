<script setup lang="ts">
import {
  useTools,
  useToolHeatmap,
  useToolStitch,
  BOXPLOT_VARIANTS,
  boxplotDefaultLabels,
  EXAMPLE_INPUT,
  HEATMAP_EXAMPLE_INPUT,
} from '~/composables/domain/useTools'
import type { PlotFormat } from '~/utils/api'

useHead({ title: 'Tools - OmicsInferenceDeck' })

const {
  inputText, variant, svg, isLoading, isDownloading, errorMessage,
  xlabel: boxXlabel, ylabel: boxYlabel,
  generate, download,
} = useTools()

const {
  inputText: heatmapInput,
  svg: heatmapSvg,
  isLoading: heatmapIsLoading,
  isDownloading: heatmapIsDownloading,
  errorMessage: heatmapErrorMessage,
  xlabel: heatmapXlabel,
  ylabel: heatmapYlabel,
  legend: heatmapLegend,
  generate: heatmapGenerate,
  download: heatmapDownload,
} = useToolHeatmap()

const {
  files: stitchFiles,
  format: stitchFormat,
  row1: stitchRow1,
  row2: stitchRow2,
  row3: stitchRow3,
  preview: stitchPreview,
  previewFormat: stitchPreviewFormat,
  isLoading: stitchIsLoading,
  isDownloading: stitchIsDownloading,
  errorMessage: stitchErrorMessage,
  total: stitchTotal,
  rowSum: stitchRowSum,
  canStitch: stitchCanStitch,
  addFiles: stitchAddFiles,
  removeFile: stitchRemoveFile,
  stitch: stitchStitch,
  download: stitchDownload,
  clear: stitchClear,
} = useToolStitch()

// 文件上传框的 accept：已选格式则锁定，否则允许三种
const stitchAccept = computed(() =>
  stitchFormat.value ? `.${stitchFormat.value}` : '.png,.svg,.pdf',
)

function handleStitchFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  stitchAddFiles(input.files)
  // 允许重复选择同一文件
  input.value = ''
}

const formats: Array<{ label: string, value: PlotFormat }> = [
  { label: 'PNG', value: 'png' },
  { label: 'SVG', value: 'svg' },
  { label: 'PDF', value: 'pdf' },
]

// 用户手动改过坐标轴标签后置位；此时显示「其他」并把开关视觉置为关闭。
// 只有点击开关（isClinical setter）才会清除，符合「只有点开关才退出」。
const isCustom = ref(false)

// 开关：关 = pvalues，开 = clinical
const isClinical = computed({
  // isCustom 为真时返回 false，使滑块停在灰色关闭位
  get: () => !isCustom.value && variant.value === 'clinical',
  set: (checked: boolean) => {
    variant.value = checked ? 'clinical' : 'pvalues'
    // 切换变体时把两个输入框重置为该变体的默认值
    const d = boxplotDefaultLabels(variant.value)
    boxXlabel.value = d.xlabel
    boxYlabel.value = d.ylabel
    isCustom.value = false // 点击开关即退出「其他」
  },
})
const variantLabel = computed(() =>
  isCustom.value
    ? '其他'
    : BOXPLOT_VARIANTS.find(item => item.value === variant.value)?.label ?? '',
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
    <!-- 第一张卡片 -->
    <section class="mx-auto w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <!-- 卡片头部：标题 + 说明 -->
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-3xl font-bold text-slate-900">图表拼接</h3>
        <p class="mt-1 text-xs text-slate-500">
          您可以在这里上传多个<strong>同一格式</strong>（PNG/SVG/PDF）的图表，我们会把它按照上传顺序从左到右、从上到下拼接成最多3行的网格图表。输出格式将会与上传格式一致。<br>
          如果是尺寸相同的图片，拼接出来保证一像素都不损失；如果尺寸不同，那么部分图片可能会因放大或缩小稍微损失点像素
        </p>
      </div>

      <!-- 卡片主体：控制区 + 预览 -->
      <div class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_1px_minmax(0,1fr)]">
        <!-- 控制区 -->
        <div>
          <h4 class="m-0 mb-3 text-sm font-semibold text-slate-900">总图表 {{ stitchTotal }} 个</h4>

          <div class="flex flex-col gap-2">
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="w-10 shrink-0">第一行</span>
              <input v-model.number="stitchRow1" type="number" min="0" class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none w-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              <span>个</span>
            </label>
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="w-10 shrink-0">第二行</span>
              <input v-model.number="stitchRow2" type="number" min="0" class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none w-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              <span>个</span>
            </label>
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="w-10 shrink-0">第三行</span>
              <input v-model.number="stitchRow3" type="number" min="0" class="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none w-20 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
              <span>个</span>
            </label>
          </div>

          <p v-if="stitchTotal > 0 && stitchRowSum !== stitchTotal" class="mt-2 text-[13px] text-red-600">
            三行之和需等于总数（当前 {{ stitchRowSum }} / {{ stitchTotal }}）
          </p>

          <div class="mt-4 flex items-center gap-3">
            <button
              type="button"
              class="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="!stitchCanStitch || stitchIsLoading"
              @click="stitchStitch"
            >
              {{ stitchIsLoading ? '拼接中...' : '拼接图表' }}
            </button>
            <button
              type="button"
              class="rounded-lg border border-slate-200 bg-white px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="stitchTotal === 0 || stitchIsLoading"
              @click="stitchClear"
            >
              清空
            </button>
            <p v-if="stitchErrorMessage" class="text-[13px] text-red-600">{{ stitchErrorMessage }}</p>
          </div>

          <!-- 文件上传框 -->
          <div class="relative mt-4 rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 text-center transition-all hover:border-primary hover:bg-indigo-50">
            <input
              id="stitch-file"
              type="file"
              multiple
              :accept="stitchAccept"
              class="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              @change="handleStitchFileChange"
            />
            <label for="stitch-file" class="flex min-h-[104px] flex-col items-center justify-center px-4 py-5 pointer-events-none">
              <span class="text-sm font-semibold text-slate-900">选择或拖入图表文件</span>
              <small class="mt-1 text-xs leading-relaxed text-slate-500">
                {{ stitchFormat ? `已锁定 ${stitchFormat.toUpperCase()} 格式` : '支持 PNG / PDF / SVG，多选；首个文件确定格式。' }}
              </small>
            </label>
          </div>

          <!-- 已上传文件列表 -->
          <div v-if="stitchFiles.length > 0" class="mt-3 flex flex-col gap-2">
            <div v-for="(file, index) in stitchFiles" :key="index" class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <span class="truncate text-[13px] text-slate-900" :title="file.name">{{ file.name }}</span>
              <button type="button" aria-label="移除" title="移除" class="flex h-7 w-7 items-center justify-center text-slate-500 hover:text-red-600" @click="stitchRemoveFile(index)">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
          </div>
        </div>

        <div class="h-px bg-slate-200 lg:h-auto lg:w-px" />

        <!-- 预览区 -->
        <div>
          <div class="mb-3 flex items-center justify-between gap-3">
            <h4 class="m-0 text-sm font-semibold text-slate-900">拼接预览</h4>
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-[13px] text-slate-700 hover:bg-slate-100 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="!stitchPreview || stitchIsDownloading"
              @click="stitchDownload"
            >
              {{ stitchIsDownloading ? 'Preparing...' : 'Download' }}
            </button>
          </div>
          <div class="overflow-hidden rounded-lg border border-slate-200 bg-slate-50/50">
            <div v-if="stitchPreview && stitchPreviewFormat === 'svg'" class="svg-chart" v-html="stitchPreview" />
            <div v-else-if="stitchPreview" class="svg-chart">
              <img :src="stitchPreview" alt="拼接预览" class="max-w-full" />
            </div>
            <div v-else class="svg-chart text-slate-400 text-sm">
              拼接后在此预览。
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 第二张卡片 -->
    <section class="mx-auto mt-8 w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <!-- 卡片头部：标题 + 说明 -->
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-3xl font-bold text-slate-900">箱线图</h3>
        <p class="mt-1 text-xs text-slate-500">
          您可以在这里绘制箱线图，例如“各方法在x个癌症数据集上的-log10 P-values分布”或者“各方法在x个癌症数据集上的显著临床参数数量分布”。<br>
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
          <div class="mt-4 flex flex-col gap-2">
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="shrink-0">X轴标签:</span>
              <input v-model="boxXlabel" type="text" placeholder="允许留空" @input="isCustom = true"
                class="w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            </label>
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="shrink-0">Y轴标签:</span>
              <input v-model="boxYlabel" type="text" placeholder="允许留空" @input="isCustom = true"
                class="w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            </label>
          </div>
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

    <!-- 第三张卡片 -->
    <section class="mx-auto mt-8 w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <!-- 卡片头部：标题 + 说明 -->
      <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <h3 class="m-0 text-3xl font-bold text-slate-900">热图</h3>
        <p class="mt-1 text-xs text-slate-500">
          您可以在这里绘制热图。参考输入示例输入个二维矩阵就可以了。绘制出来的热图会用红框圈出每列最大值。<br>
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
          <div class="mt-4 flex flex-col gap-2">
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="shrink-0">X轴标签:</span>
              <input v-model="heatmapXlabel" type="text" placeholder="允许留空"
                class="w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            </label>
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="shrink-0">Y轴标签:</span>
              <input v-model="heatmapYlabel" type="text" placeholder="允许留空"
                class="w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            </label>
            <label class="flex items-center gap-2 text-[13px] text-slate-700">
              <span class="shrink-0">颜色条标签:</span>
              <input v-model="heatmapLegend" type="text" placeholder="允许留空"
                class="w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10" />
            </label>
          </div>
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
