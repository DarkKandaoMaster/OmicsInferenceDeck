import { renderResourceBoxplot, downloadResourceBoxplot, type PlotFormat } from '~/utils/api'

/** 变体定义：A 为 -log10 P-values，B 为显著临床参数数量 */
export const BOXPLOT_VARIANTS = [
  { value: 'pvalues', label: 'A · -log10 P-values' },
  { value: 'clinical', label: 'B · The number of significant clinical parameters' },
] as const

/** 默认示例数据，方便用户上手（对应 -log10 P-values 变体） */
const SAMPLE_TEXT = `Subtype-DCC,1.11,2.33,8.79,1.69,3.75,5.94,1.48,5.46,2.77
Subtype-GAN,1.28,1.45,7.77,2.83,1.65,0.1,0.39,7.4,2.62
NEMO,1.21,2.8,5.72,2.63,3.04,5.01,1.8,5.96,2.38
SNF,0.93,1.31,8.19,2.23,3.24,5.27,0.72,5,2.77
PINS,1.42,1.61,4.44,2.46,3.41,2.32,1.26,5.04,3.63
NMF,0.4,0.24,5.63,0.42,1.49,3.54,0.1,5.1,1.39
MCCA,1.73,1.03,7.91,0.49,2.15,0.89,0.18,3.75,1.1
iCluster,0.53,0.21,2.95,0.23,0.54,0.98,0.06,2.13,1.36
Spectral,0.08,1.67,5.46,0.6,2.39,1.77,0.19,0.81,1.82
K-Means,0.12,0.66,4.77,1.01,2.38,1.56,0.01,7.03,1.67
LRAcluster,0.27,0.63,6.83,0.19,2.03,2.05,0.14,4.58,2.52`

const inputText = ref(SAMPLE_TEXT)
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
