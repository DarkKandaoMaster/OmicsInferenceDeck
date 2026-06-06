<script setup lang="ts">
import { useResources, BOXPLOT_VARIANTS } from '~/composables/domain/useResources'
import type { PlotFormat } from '~/utils/api'

useHead({ title: 'Resources - OmicsInferenceDeck' })

const {
  inputText, variant, svg, isLoading, isDownloading, errorMessage,
  generate, download,
} = useResources()

const formats: Array<{ label: string, value: PlotFormat }> = [
  { label: 'PNG', value: 'png' },
  { label: 'SVG', value: 'svg' },
  { label: 'PDF', value: 'pdf' },
]

const downloadOpen = ref(false)
const downloadRoot = ref<HTMLElement | null>(null)

function handleDocumentClick(event: MouseEvent) {
  if (!downloadRoot.value?.contains(event.target as Node)) downloadOpen.value = false
}
onMounted(() => document.addEventListener('click', handleDocumentClick))
onUnmounted(() => document.removeEventListener('click', handleDocumentClick))

async function handleDownload(format: PlotFormat) {
  downloadOpen.value = false
  await download(format)
}
</script>

<template>
  <div class="py-8 max-w-6xl mx-auto px-4">
    <section class="mx-auto w-full max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <!-- 卡片头部：标题 + 说明 + 图表类型选择 -->
      <div class="flex flex-col gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 class="m-0 text-base font-semibold text-slate-900">箱线图</h3>
          <p class="mt-1 text-xs text-slate-500">
            粘贴「方法名,数值,数值,...」格式的数据（每行一个方法，数值数量不限），选择图表类型后生成横向箱线图，并可下载为 PNG / SVG / PDF。
          </p>
        </div>
        <div class="flex items-center gap-3">
          <label class="whitespace-nowrap text-xs font-medium text-slate-700">图表类型：</label>
          <select
            v-model="variant"
            class="w-40 rounded-lg border border-slate-200 bg-white px-3 py-2 text-[13px] text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/10"
          >
            <option v-for="item in BOXPLOT_VARIANTS" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>
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
            class="w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-[13px] leading-relaxed text-slate-700 outline-none focus:border-primary"
            placeholder="Subtype-DCC,1.11,2.33,8.79,..."
          />
          <div class="mt-4 flex items-center gap-3">
            <button
              type="button"
              class="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="isLoading"
              @click="generate"
            >
              {{ isLoading ? '生成中...' : '生成箱线图' }}
            </button>
            <p v-if="errorMessage" class="text-[13px] text-red-600">{{ errorMessage }}</p>
          </div>
        </div>

        <div class="h-px bg-slate-200 lg:h-auto lg:w-px" />

        <!-- 预览区 -->
        <div>
          <div class="mb-3 flex items-center justify-between gap-3">
            <h4 class="m-0 text-sm font-semibold text-slate-900">箱线图预览</h4>
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
              点击「生成箱线图」后在此预览。
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
