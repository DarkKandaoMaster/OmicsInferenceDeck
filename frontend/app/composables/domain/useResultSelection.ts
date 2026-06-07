export type MetricKey = 'cluster' | 'clinical' | 'biology' | 'awa'
export type ChartKey =
  | 'inputClusterScatter'
  | 'predClusterScatter'
  | 'diffVolcano'
  | 'diffHeatmap'
  | 'biomarkerClusterScatter'
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
  { key: 'predClusterScatter', label: '聚类后散点图' },
  { key: 'diffVolcano', label: '差异火山图' },
  { key: 'diffHeatmap', label: '差异热图' },
  { key: 'biomarkerClusterScatter', label: '生物标志物簇散点图' },
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
  predClusterScatter: true,
  diffVolcano: true,
  diffHeatmap: true,
  biomarkerClusterScatter: true,
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

// 选项依赖联动
// 依赖来自后端读取的中间文件（上游不算，下游会报错或得 0 分）：
//   awa(综合得分) 依赖 cluster + clinical + biology
//   biology(生物学相关性) 依赖 任一 Enrichment 图（读 enrichment_{GO/KEGG}.parquet）
//   每个 Enrichment 图 依赖 任一 Differential 图（读 differential_volcano.parquet）
// Enrichment / Differential 在后端都是“整组触发一次”，因此是 OR 组依赖。
type SelectionKey = MetricKey | ChartKey

const ENRICH_KEYS: ChartKey[] = ['enrichBarGO', 'enrichBarKEGG', 'enrichBubbleGO', 'enrichBubbleKEGG']
const DIFF_KEYS: ChartKey[] = ['diffVolcano', 'diffHeatmap']

// 勾选某项时需要一并勾选的直接上游依赖（补勾整组全部）。
const CHECK_DEPENDENCIES: Partial<Record<SelectionKey, SelectionKey[]>> = {
  awa: ['cluster', 'clinical', 'biology'],
  biomarkerClusterScatter: [...DIFF_KEYS],
  biology: [...ENRICH_KEYS],
  enrichBarGO: [...DIFF_KEYS],
  enrichBarKEGG: [...DIFF_KEYS],
  enrichBubbleGO: [...DIFF_KEYS],
  enrichBubbleKEGG: [...DIFF_KEYS],
}

function isMetricKey(key: SelectionKey): key is MetricKey {
  return key in enabledMetrics
}

function getEnabled(key: SelectionKey): boolean {
  return isMetricKey(key) ? enabledMetrics[key] : enabledCharts[key]
}

function setEnabled(key: SelectionKey, value: boolean): void {
  if (isMetricKey(key)) enabledMetrics[key] = value
  else enabledCharts[key] = value
}

const anyEnrich = () => ENRICH_KEYS.some(key => enabledCharts[key])
const anyDiff = () => DIFF_KEYS.some(key => enabledCharts[key])

// 勾选方向：沿依赖图向下逐层补勾（awa → biology → enrich → diff）。
function cascadeOn(key: SelectionKey): void {
  const queue: SelectionKey[] = [key]
  while (queue.length) {
    const current = queue.shift()!
    for (const dep of CHECK_DEPENDENCIES[current] ?? []) {
      if (!getEnabled(dep)) {
        setEnabled(dep, true)
        queue.push(dep)
      }
    }
  }
}

// 取消方向：当整组上游被清空时，向上取消依赖它的下游（循环到稳定）。
function cascadeOff(): void {
  let changed = true
  while (changed) {
    changed = false
    if (!anyDiff()) {
      for (const key of ENRICH_KEYS) {
        if (enabledCharts[key]) { enabledCharts[key] = false; changed = true }
      }
      if (enabledCharts.biomarkerClusterScatter) {
        enabledCharts.biomarkerClusterScatter = false
        changed = true
      }
    }
    if (!anyEnrich() && enabledMetrics.biology) {
      enabledMetrics.biology = false
      changed = true
    }
    if ((!enabledMetrics.cluster || !enabledMetrics.clinical || !enabledMetrics.biology) && enabledMetrics.awa) {
      enabledMetrics.awa = false
      changed = true
    }
  }
}

let syncing = false
let prevMetrics: Record<MetricKey, boolean> = { ...enabledMetrics }
let prevCharts: Record<ChartKey, boolean> = { ...enabledCharts }

watch([enabledMetrics, enabledCharts], () => {
  if (syncing) return
  syncing = true
  try {
    const turnedOn: SelectionKey[] = []
    let turnedOff = false

    for (const key of Object.keys(enabledMetrics) as MetricKey[]) {
      if (enabledMetrics[key] && !prevMetrics[key]) turnedOn.push(key)
      else if (!enabledMetrics[key] && prevMetrics[key]) turnedOff = true
    }
    for (const key of Object.keys(enabledCharts) as ChartKey[]) {
      if (enabledCharts[key] && !prevCharts[key]) turnedOn.push(key)
      else if (!enabledCharts[key] && prevCharts[key]) turnedOff = true
    }

    for (const key of turnedOn) cascadeOn(key)
    if (turnedOff) cascadeOff()
  } finally {
    prevMetrics = { ...enabledMetrics }
    prevCharts = { ...enabledCharts }
    syncing = false
  }
}, { deep: true })

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
