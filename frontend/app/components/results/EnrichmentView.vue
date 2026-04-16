<script setup lang="ts">
import { useEcharts } from '~/composables/ui/useEcharts'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useDifferential } from '~/composables/domain/useDifferential'

const enrichmentChartRef = ref<HTMLElement | null>(null)
const enrichmentBubbleChartRef = ref<HTMLElement | null>(null)
const enrichmentAreaRef = ref<HTMLElement | null>(null)

const barChart = useEcharts()
const bubbleChart = useEcharts()

const {
  enrichmentResult, isEnrichmentLoading, enrichmentType,
  selectedEnrichmentCluster, bubbleChartMode,
  runEnrichmentAnalysis,
} = useEnrichment()
const { diffResult } = useDifferential()

function renderEnrichmentChart() {
  if (!enrichmentChartRef.value || !enrichmentResult.value) return
  const clusterId = selectedEnrichmentCluster.value
  const data = enrichmentResult.value?.[clusterId]

  if (!data || data.length === 0) {
    const myChart = barChart.init(enrichmentChartRef.value)
    myChart.clear()
    myChart.setOption({
      title: { text: `Cluster ${clusterId} 未找到显著富集的通路 (基因数量可能不足)`, left: 'center', top: 'center', textStyle: { color: '#888', fontWeight: 'normal' } },
    })
    return
  }

  const myChart = barChart.init(enrichmentChartRef.value)

  let plotData: any[] = []
  if (enrichmentType.value === 'GO') {
    const order: Record<string, number> = { MF: 1, CC: 2, BP: 3 }
    plotData = [...data].sort((a: any, b: any) => (order[a.Category] ?? 0) - (order[b.Category] ?? 0))
  } else {
    plotData = [...data].reverse()
  }

  const terms = plotData.map((item: any) => {
    const name = item.Term.split(' (GO')[0]
    return name.length > 40 ? name.substring(0, 40) + '...' : name
  })

  let categories: string[] = []
  let colorMap: Record<string, string> = {}

  if (enrichmentType.value === 'GO') {
    categories = ['BP', 'CC', 'MF']
    colorMap = { BP: '#6fc3a1', CC: '#8fa5d2', MF: '#fb9570' }
  } else {
    categories = ['KEGG']
    colorMap = { KEGG: '#3498db' }
  }

  const seriesConfig = categories.map(cat => ({
    name: cat,
    type: 'bar' as const,
    barGap: '-100%',
    data: plotData.map((item: any) => item.Category === cat ? item.Gene_Count : '-'),
    itemStyle: { color: colorMap[cat], barBorderRadius: [0, 5, 5, 0] as number[] },
    label: { show: true, position: 'right' as const, formatter: (params: any) => params.value !== '-' ? params.value : '' },
  }))

  myChart.setOption({
    title: { text: `${enrichmentType.value} Enrichment (Cluster ${clusterId})`, left: 'center', textStyle: { fontSize: 16 } },
    tooltip: {
      trigger: 'axis',
      formatter(params: any) {
        const index = params[0].dataIndex
        const item = plotData[index]
        return `<b>${item.Term}</b><br/>P-value: ${item.P_value.toExponential(2)}<br/>`
      },
    },
    legend: { show: true, data: categories, orient: 'vertical', right: '2%', top: 'center' },
    grid: { left: '35%', right: '12%', bottom: '10%', top: '15%' },
    xAxis: { type: 'value', name: 'Gene Number', nameLocation: 'middle', nameGap: 25 },
    yAxis: { type: 'category', data: terms, axisLabel: { interval: 0, fontSize: 11, width: 250, overflow: 'truncate' } },
    series: seriesConfig,
  })
}

function renderEnrichmentBubbleChart() {
  if (!enrichmentBubbleChartRef.value || !enrichmentResult.value) return
  const myChart = bubbleChart.init(enrichmentBubbleChartRef.value)
  const result = enrichmentResult.value

  const clusters = Object.keys(result).map(Number).sort()
  const allTermsSet = new Set<string>()
  clusters.forEach(cid => {
    result[cid]!.forEach((item: any) => {
      let name = item.Term.split(' (GO')[0]
      if (name.length > 50) name = name.substring(0, 50) + '...'
      allTermsSet.add(name)
    })
  })
  const allTerms = Array.from(allTermsSet).reverse()

  let scatterSeries: any[] = []
  let xAxisOption: any = {}
  let yAxisOption: any = {}
  let legendOption: any = null
  let minP = 1, maxP = 0

  if (bubbleChartMode.value === 'combined') {
    const scatterData: any[] = []
    const displayClusters = ['', ...clusters.map(String), '']
    const displayTerms = ['', ...allTerms, '']

    clusters.forEach((cid, xIdx) => {
      result[cid]!.forEach((item: any) => {
        let name = item.Term.split(' (GO')[0]
        if (name.length > 50) name = name.substring(0, 50) + '...'
        const yIdx = allTerms.indexOf(name)
        const pVal = item.Adjusted_P || item.P_value
        if (pVal < minP) minP = pVal
        if (pVal > maxP) maxP = pVal
        scatterData.push([xIdx + 1, yIdx + 1, pVal, item.Gene_Count, name, cid])
      })
    })

    scatterSeries = [{ name: 'Enrichment Bubble', type: 'scatter', data: scatterData, itemStyle: { opacity: 0.9, borderColor: 'transparent' } }]
    xAxisOption = { type: 'category', data: displayClusters, boundaryGap: false, name: 'Cluster', nameLocation: 'middle', nameGap: 30, nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' }, axisLine: { show: false }, axisTick: { show: true, alignWithLabel: true, inside: false, lineStyle: { color: '#000' } }, axisLabel: { color: '#000', fontSize: 12, interval: 0, formatter: (val: string) => val === '' ? '' : val }, splitLine: { show: true, lineStyle: { type: 'solid', color: '#eaeaea' } } }
    yAxisOption = { type: 'category', data: displayTerms, boundaryGap: false, name: enrichmentType.value === 'GO' ? 'GO Pathways' : 'KEGG Pathways', nameLocation: 'middle', nameGap: 220, nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' }, axisLine: { show: false }, axisTick: { show: true, alignWithLabel: true, inside: false, lineStyle: { color: '#000' } }, axisLabel: { color: '#000', fontSize: 12, interval: 0, formatter: (val: string) => val === '' ? '' : val }, splitLine: { show: true, lineStyle: { type: 'solid', color: '#eaeaea' } } }
  } else {
    const legendData: string[] = []
    clusters.forEach(cid => {
      const clusterData: any[] = []
      result[cid]!.forEach((item: any) => {
        let name = item.Term.split(' (GO')[0]
        if (name.length > 50) name = name.substring(0, 50) + '...'
        const pVal = item.Adjusted_P || item.P_value
        if (pVal < minP) minP = pVal
        if (pVal > maxP) maxP = pVal
        clusterData.push([item.Gene_Count, name, pVal, item.Gene_Count, name, cid])
      })
      scatterSeries.push({ name: `Cluster ${cid}`, type: 'scatter', data: clusterData, itemStyle: { opacity: 0.9, borderColor: 'transparent' } })
      legendData.push(`Cluster ${cid}`)
    })

    legendOption = { data: legendData, orient: 'vertical', right: '15%', top: '5%', textStyle: { fontWeight: 'bold', color: '#000' } }
    xAxisOption = { type: 'value', name: 'Gene Number', nameLocation: 'middle', nameGap: 30, nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' }, axisLine: { show: true, lineStyle: { color: '#000' } }, axisTick: { show: true, lineStyle: { color: '#000' } }, axisLabel: { color: '#000', fontSize: 12 }, splitLine: { show: true, lineStyle: { type: 'dashed', color: '#eaeaea' } } }
    yAxisOption = { type: 'category', data: allTerms, name: enrichmentType.value === 'GO' ? 'GO Pathways' : 'KEGG Pathways', nameLocation: 'middle', nameGap: 220, nameTextStyle: { fontWeight: 'bold', fontSize: 14, color: '#000' }, axisLine: { show: false }, axisTick: { show: true, alignWithLabel: true, inside: false, lineStyle: { color: '#000' } }, axisLabel: { color: '#000', fontSize: 12, interval: 0 }, splitLine: { show: true, lineStyle: { type: 'solid', color: '#eaeaea' } } }
  }

  if (maxP < 0.05) maxP = 0.05

  myChart.setOption({
    title: { text: `${enrichmentType.value} Pathway Enrichment - All Clusters`, left: 'center', textStyle: { fontSize: 16, fontFamily: 'Arial', fontWeight: 'bold', color: '#000' } },
    legend: legendOption || undefined,
    tooltip: {
      trigger: 'item',
      formatter(params: any) {
        const d = params.data
        return `<b>${d[4]}</b><br/>Cluster: ${d[5]}<br/>p.adjust: ${d[2].toExponential(3)}<br/>Gene Count: ${d[3]}`
      },
    },
    grid: { show: true, borderColor: '#000', borderWidth: 1, left: '25%', right: bubbleChartMode.value === 'combined' ? '15%' : '25%', bottom: '10%', top: '12%' },
    xAxis: xAxisOption,
    yAxis: yAxisOption,
    visualMap: [
      { type: 'continuous', dimension: 2, min: minP, max: maxP, inverse: true, orient: 'vertical', top: '20%', right: '2%', inRange: { color: ['#ff0000', '#0000ff'] }, text: ['p.adjust', ''], textStyle: { fontWeight: 'bold', color: '#000' }, calculable: false, itemWidth: 15, itemHeight: 100, formatter: (value: number) => value < 0.001 ? value.toExponential(2) : value.toFixed(2) },
      { type: 'piecewise', dimension: 3, orient: 'vertical', bottom: '15%', right: '2%', splitNumber: 3, inRange: { symbolSize: [8, 20] }, text: ['\nGene Count', ''], textStyle: { fontWeight: 'bold', color: '#000' }, itemSymbol: 'circle', itemGap: 15 },
    ],
    series: scatterSeries,
  })
}

async function handleRunEnrichment(type: string) {
  await runEnrichmentAnalysis(type)
  if (enrichmentResult.value) {
    await nextTick()
    renderEnrichmentChart()
    renderEnrichmentBubbleChart()
    enrichmentAreaRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

onUnmounted(() => {
  barChart.dispose()
  bubbleChart.dispose()
})
</script>

<template>
  <div v-if="diffResult" ref="enrichmentAreaRef" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200 bg-green-50 flex justify-between items-center">
      <h3 class="m-0 text-lg text-green-700 flex items-center gap-3">
        <span class="bg-green-700 text-white w-6 h-6 flex items-center justify-center rounded-md text-sm font-bold">C</span>
        功能富集分析 (Enrichment Analysis)
      </h3>
      <div class="flex gap-2">
        <button @click="handleRunEnrichment('GO')" :disabled="isEnrichmentLoading" class="border-none rounded-lg text-[13px] font-medium px-4 py-2 cursor-pointer text-white transition-all bg-emerald-600 disabled:opacity-60 disabled:cursor-not-allowed">
          {{ (isEnrichmentLoading && enrichmentType === 'GO') ? '查询中...' : '运行 GO' }}
        </button>
        <button @click="handleRunEnrichment('KEGG')" :disabled="isEnrichmentLoading" class="border-none rounded-lg text-[13px] font-medium px-4 py-2 cursor-pointer text-white transition-all bg-sky-600 disabled:opacity-60 disabled:cursor-not-allowed">
          {{ (isEnrichmentLoading && enrichmentType === 'KEGG') ? '查询中...' : '运行 KEGG' }}
        </button>
      </div>
    </div>
    <div class="p-6">
      <p class="text-slate-500 text-sm m-0 mb-5">针对各个簇的显著上调基因（P&lt;0.05, LogFC&gt;0.5），在数据库中查找显著富集的生物学通路。</p>

      <div v-if="enrichmentResult" class="flex flex-col gap-6">
        <!-- 条形图 -->
        <div class="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <div class="bg-slate-100 px-5 py-3 border-b border-slate-200 flex justify-between items-center">
            <div class="font-semibold text-sm text-slate-700">📊 单簇富集条形图</div>
            <select v-model="selectedEnrichmentCluster" @change="renderEnrichmentChart" class="px-2 py-1 border border-slate-200 rounded-lg text-[13px] bg-white cursor-pointer outline-none">
              <option v-for="cid in Object.keys(enrichmentResult)" :key="cid" :value="Number(cid)">Cluster {{ cid }}</option>
            </select>
          </div>
          <div ref="enrichmentChartRef" class="w-full h-[500px]" />
        </div>

        <!-- 气泡图 -->
        <div class="border border-slate-200 rounded-xl bg-white overflow-hidden mt-6">
          <div class="bg-slate-100 px-5 py-3 border-b border-slate-200 flex justify-between items-center">
            <div class="font-semibold text-sm text-slate-700">🎈 全簇通路富集气泡图</div>
            <div class="flex gap-4">
              <label class="text-[13px] text-slate-700 cursor-pointer flex items-center gap-1.5">
                <input type="radio" v-model="bubbleChartMode" value="combined" @change="renderEnrichmentBubbleChart" /> 按簇平铺
              </label>
              <label class="text-[13px] text-slate-700 cursor-pointer flex items-center gap-1.5">
                <input type="radio" v-model="bubbleChartMode" value="by_gene" @change="renderEnrichmentBubbleChart" /> 按基因分布
              </label>
            </div>
          </div>
          <div ref="enrichmentBubbleChartRef" class="w-full h-[500px]" />
        </div>
      </div>
    </div>
  </div>
</template>
