import { renderResourceBoxplot, downloadResourceBoxplot, type PlotFormat } from '~/utils/api'

/** 变体定义：A 为 -log10 P-values，B 为显著临床参数数量 */
export const BOXPLOT_VARIANTS = [
  { value: 'pvalues', label: '-log10 P-values' },
  { value: 'clinical', label: 'The number of significant clinical parameters' },
] as const

const inputText = ref('')
const variant = ref<string>('pvalues')
const svg = ref('')
const isLoading = ref(false)
const isDownloading = ref<PlotFormat | null>(null)
const errorMessage = ref('')

export function useResources() {
  async function generate() {
    isLoading.value = true
    errorMessage.value = ''
    try {
      const res = await renderResourceBoxplot({
        data: inputText.value,
        variant: variant.value,
      })
      svg.value = res.data.svg
    } catch (error: any) {
      svg.value = ''
      errorMessage.value = '生成失败: ' + (error.response?.data?.detail || error.message)
    } finally {
      isLoading.value = false
    }
  }

  async function download(format: PlotFormat) {
    if (isDownloading.value) return
    isDownloading.value = format
    errorMessage.value = ''
    try {
      const response = await downloadResourceBoxplot({
        data: inputText.value,
        variant: variant.value,
        format,
      })
      const blob = response.data instanceof Blob
        ? response.data
        : new Blob([response.data])
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `boxplot_${variant.value}.${format}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (error: any) {
      errorMessage.value = '下载失败: ' + (error.response?.data?.detail || error.message)
    } finally {
      isDownloading.value = null
    }
  }

  return {
    inputText, variant, svg, isLoading, isDownloading, errorMessage,
    generate, download,
  }
}
