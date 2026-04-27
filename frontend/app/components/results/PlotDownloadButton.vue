<script setup lang="ts">
import { downloadPlot } from '~/utils/api'

type PlotFormat = 'png' | 'svg' | 'pdf'

const props = withDefaults(defineProps<{
  plotType: string
  params: Record<string, any>
  filenamePrefix?: string
  disabled?: boolean
}>(), {
  filenamePrefix: 'plot',
  disabled: false,
})

const rootRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)
const isDownloading = ref<PlotFormat | null>(null)

const formats: Array<{ label: string, value: PlotFormat }> = [
  { label: 'PNG', value: 'png' },
  { label: 'SVG', value: 'svg' },
  { label: 'PDF', value: 'pdf' },
]

function extensionContentType(format: PlotFormat) {
  if (format === 'png') return 'image/png'
  if (format === 'svg') return 'image/svg+xml'
  return 'application/pdf'
}

function filenameFromDisposition(disposition: string | undefined, fallback: string) {
  if (!disposition) return fallback
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  if (encoded) return decodeURIComponent(encoded)
  const quoted = disposition.match(/filename="?([^";]+)"?/i)?.[1]
  return quoted || fallback
}

async function handleDownload(format: PlotFormat) {
  if (props.disabled || isDownloading.value) return
  isOpen.value = false
  isDownloading.value = format

  try {
    const response = await downloadPlot({
      ...props.params,
      plot_type: props.plotType,
      format,
    })
    const contentType = response.headers['content-type'] || extensionContentType(format)
    const blob = response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: contentType })
    const filename = filenameFromDisposition(
      response.headers['content-disposition'],
      `${props.filenamePrefix}.${format}`,
    )
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    alert('图表下载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isDownloading.value = null
  }
}

function handleDocumentClick(event: MouseEvent) {
  if (!rootRef.value?.contains(event.target as Node)) isOpen.value = false
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onUnmounted(() => document.removeEventListener('click', handleDocumentClick))
</script>

<template>
  <div ref="rootRef" class="relative inline-flex">
    <button
      type="button"
      class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-[13px] text-slate-700 hover:bg-slate-100 disabled:opacity-60 disabled:cursor-not-allowed"
      :disabled="disabled || !!isDownloading"
      @click.stop="isOpen = !isOpen"
    >
      {{ isDownloading ? 'Preparing...' : 'Download' }}
    </button>
    <div
      v-if="isOpen"
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
</template>
