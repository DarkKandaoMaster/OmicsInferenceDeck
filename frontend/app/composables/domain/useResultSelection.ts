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
  { key: 'inputClusterScatter', label: 'Input Cluster Scatter' },
  { key: 'clusterScatter', label: 'Cluster Scatter' },
  { key: 'diffVolcano', label: 'Differential Volcano' },
  { key: 'diffHeatmap', label: 'Differential Heatmap' },
  { key: 'enrichBarGO', label: 'Enrichment Bar Plot (GO)' },
  { key: 'enrichBarKEGG', label: 'Enrichment Bar Plot (KEGG)' },
  { key: 'enrichBubbleGO', label: 'Enrichment Bubble Plot (GO)' },
  { key: 'enrichBubbleKEGG', label: 'Enrichment Bubble Plot (KEGG)' },
  { key: 'survival', label: 'Survival Curve' },
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
    runDifferential,
    runEnrichment,
    metricOptions,
    chartOptions,
  }
}
