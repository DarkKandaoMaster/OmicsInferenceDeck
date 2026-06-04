export type MetricKey = 'cluster' | 'clinical' | 'biology' | 'awa'
export type ChartKey =
  | 'inputClusterScatter'
  | 'clusterScatter'
  | 'diffVolcano'
  | 'diffHeatmap'
  | 'enrichBarGO'
  | 'enrichBarKEGG'
  | 'enrichBubbleGO'
  | 'enrichBubbleKEGG'
  | 'survival'

export const metricOptions: { key: MetricKey; label: string }[] = [
  { key: 'cluster', label: '聚类内部质量指标' },
  { key: 'clinical', label: '临床关联指标' },
  { key: 'biology', label: '生物学相关性指标' },
  { key: 'awa', label: '综合得分' },
]

export const chartOptions: { key: ChartKey; label: string }[] = [
  { key: 'inputClusterScatter', label: '聚类前散点图' },
  { key: 'clusterScatter', label: '聚类后散点图' },
  { key: 'diffVolcano', label: '差异火山图' },
  { key: 'diffHeatmap', label: '差异热图' },
  { key: 'enrichBarGO', label: 'GO富集分析条形图' },
  { key: 'enrichBarKEGG', label: 'KEGG富集分析条形图' },
  { key: 'enrichBubbleGO', label: 'GO富集分析气泡图' },
  { key: 'enrichBubbleKEGG', label: 'KEGG富集分析气泡图' },
  { key: 'survival', label: '生存曲线' },
]

const enabledMetrics = reactive<Record<MetricKey, boolean>>({
  cluster: true,
  clinical: true,
  biology: true,
  awa: true,
})

const enabledCharts = reactive<Record<ChartKey, boolean>>({
  inputClusterScatter: true,
  clusterScatter: true,
  diffVolcano: true,
  diffHeatmap: true,
  enrichBarGO: true,
  enrichBarKEGG: true,
  enrichBubbleGO: true,
  enrichBubbleKEGG: true,
  survival: true,
})

const selectedBiologyDb = ref<'GO' | 'KEGG'>('GO')

const runDifferential = computed(
  () => enabledCharts.diffVolcano || enabledCharts.diffHeatmap,
)
const runEnrichment = computed(
  () =>
    enabledCharts.enrichBarGO ||
    enabledCharts.enrichBarKEGG ||
    enabledCharts.enrichBubbleGO ||
    enabledCharts.enrichBubbleKEGG,
)

export function useResultSelection() {
  return {
    enabledMetrics,
    enabledCharts,
    selectedBiologyDb,
    runDifferential,
    runEnrichment,
    metricOptions,
    chartOptions,
  }
}
