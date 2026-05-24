export type MetricKey = 'cluster' | 'clinical' | 'biology' | 'awa'
export type ChartKey =
  | 'clusterScatter'
  | 'diffVolcano'
  | 'diffHeatmap'
  | 'enrichBar'
  | 'enrichBubble'
  | 'survival'

export const metricOptions: { key: MetricKey; label: string }[] = [
  { key: 'cluster', label: '聚类内部质量指标' },
  { key: 'clinical', label: '临床关联指标' },
  { key: 'biology', label: '生物学相关性指标' },
  { key: 'awa', label: '综合得分' },
]

export const chartOptions: { key: ChartKey; label: string }[] = [
  { key: 'clusterScatter', label: 'Cluster Scatter' },
  { key: 'diffVolcano', label: 'Differential Volcano' },
  { key: 'diffHeatmap', label: 'Differential Heatmap' },
  { key: 'enrichBar', label: 'Enrichment Bar Plot' },
  { key: 'enrichBubble', label: 'Enrichment Bubble Plot' },
  { key: 'survival', label: 'Survival Curve' },
]

const enabledMetrics = reactive<Record<MetricKey, boolean>>({
  cluster: true,
  clinical: true,
  biology: true,
  awa: true,
})

const enabledCharts = reactive<Record<ChartKey, boolean>>({
  clusterScatter: true,
  diffVolcano: true,
  diffHeatmap: true,
  enrichBar: true,
  enrichBubble: true,
  survival: true,
})

const runDifferential = computed(
  () => enabledCharts.diffVolcano || enabledCharts.diffHeatmap,
)
const runEnrichment = computed(
  () => enabledCharts.enrichBar || enabledCharts.enrichBubble,
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
