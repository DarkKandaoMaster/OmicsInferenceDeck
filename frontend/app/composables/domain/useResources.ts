import {
  renderResourceBoxplot,
  downloadResourceBoxplot,
  renderResourceHeatmap,
  downloadResourceHeatmap,
  type PlotFormat,
} from '~/utils/api'

/** 变体定义：A 为 -log10 P-values，B 为显著临床参数数量 */
export const BOXPLOT_VARIANTS = [
  { value: 'pvalues', label: '-log10 P-values' },
  { value: 'clinical', label: 'The number of significant clinical parameters' },
] as const

/** 示例输入：当用户未填写任何数据时作为兜底输入 */
export const EXAMPLE_INPUT = `Subtype-DCC,1.11,2.33,8.79,1.69,3.75,5.94,1.48,5.46,2.77
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
    // 未填写任何数据时，使用示例输入作为兜底
    if (!inputText.value.trim()) inputText.value = EXAMPLE_INPUT
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

/**热力图示例输入：带「表头行 + 索引列」的评分矩阵，取自 senior_algorithms/1.py。
这里不能直接写成：
export const HEATMAP_EXAMPLE_INPUT = `,Average,BLCA,BRCA,KIRC
Hclust,6.36,5.79,6.69,6.60
K-means,6.68,6.09,6.37,7.59
MOSD,6.62,6.60,6.34,6.93
NEMO,6.74,6.45,6.64,7.12
PIntMF,6.67,6.69,6.07,7.26
SNF,6.75,6.28,6.87,7.10
Spectral,7.05,6.94,6.58,7.64`
不然会网站显示一片空白，什么都显示不了。原因不知道...精确触发条件尚未坐实。*/
export const HEATMAP_EXAMPLE_INPUT = [
  ',Average,BLCA,BRCA,KIRC',
  'Hclust,6.36,5.79,6.69,6.60',
  'K-means,6.68,6.09,6.37,7.59',
  'MOSD,6.62,6.60,6.34,6.93',
  'NEMO,6.74,6.45,6.64,7.12',
  'PIntMF,6.67,6.69,6.07,7.26',
  'SNF,6.75,6.28,6.87,7.10',
  'Spectral,7.05,6.94,6.58,7.64',
].join('\n')


// 与箱线图状态隔离，避免两张卡片互相串数据
const heatmapInputText = ref('')
const heatmapSvg = ref('')
const heatmapIsLoading = ref(false)
const heatmapIsDownloading = ref<PlotFormat | null>(null)
const heatmapErrorMessage = ref('')

export function useResourceHeatmap() {
  async function generate() {
    heatmapIsLoading.value = true
    heatmapErrorMessage.value = ''
    // 未填写任何数据时，使用示例输入作为兜底
    if (!heatmapInputText.value.trim()) heatmapInputText.value = HEATMAP_EXAMPLE_INPUT
    try {
      const res = await renderResourceHeatmap({ data: heatmapInputText.value })
      heatmapSvg.value = res.data.svg
    } catch (error: any) {
      heatmapSvg.value = ''
      heatmapErrorMessage.value = '生成失败: ' + (error.response?.data?.detail || error.message)
    } finally {
      heatmapIsLoading.value = false
    }
  }

  async function download(format: PlotFormat) {
    if (heatmapIsDownloading.value) return
    heatmapIsDownloading.value = format
    heatmapErrorMessage.value = ''
    try {
      const response = await downloadResourceHeatmap({
        data: heatmapInputText.value,
        format,
      })
      const blob = response.data instanceof Blob
        ? response.data
        : new Blob([response.data])
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `heatmap.${format}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (error: any) {
      heatmapErrorMessage.value = '下载失败: ' + (error.response?.data?.detail || error.message)
    } finally {
      heatmapIsDownloading.value = null
    }
  }

  return {
    inputText: heatmapInputText,
    svg: heatmapSvg,
    isLoading: heatmapIsLoading,
    isDownloading: heatmapIsDownloading,
    errorMessage: heatmapErrorMessage,
    generate, download,
  }
}
