<script setup lang="ts">
import { useEcharts } from '~/composables/ui/useEcharts'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useDataState } from '~/composables/domain/useDataState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'
import { useEnrichment } from '~/composables/domain/useEnrichment'

const volcanoChartRef = ref<HTMLElement | null>(null)
const heatmapChartRef = ref<HTMLElement | null>(null)
const diffAreaRef = ref<HTMLElement | null>(null)

const volcanoChart = useEcharts()
const heatmapChart = useEcharts()

const {
  diffResult, isDiffLoading, selectedVolcanoCluster,
  selectedDiffOmicsType, diffErrorMessage,
  runDifferentialAnalysis,
} = useDifferential()
const { uploadedOmicsTypes } = useDataState()
const { backendResponse } = useAnalysisActions()
const { runEnrichmentAnalysis } = useEnrichment()

function renderVolcanoPlot() {
  if (!volcanoChartRef.value || !diffResult.value) return
  const clusterId = selectedVolcanoCluster.value
  const data = diffResult.value.volcano_data[clusterId]
  if (!data) return

  const myChart = volcanoChart.init(volcanoChartRef.value)

  const significantUp: number[][] = []
  const significantDown: number[][] = []
  const notSignificant: number[][] = []

  data.forEach((item: any) => {
    const point = [item.logFC, item.negLog10P, item.gene]
    if (item.t_pvalue < 0.05 && item.logFC > 0.5) significantUp.push(point)
    else if (item.t_pvalue < 0.05 && item.logFC < -0.5) significantDown.push(point)
    else notSignificant.push(point)
  })

  myChart.setOption({
    title: { text: `Cluster ${clusterId} vs Others`, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'item',
      formatter(params: any) {
        return `<b>${params.data[2]}</b><br/>LogFC: ${params.data[0].toFixed(3)}<br/>-Log10(P): ${params.data[1].toFixed(3)}`
      },
    },
    xAxis: { name: 'Log2 Fold Change', nameLocation: 'middle', nameGap: 25 },
    yAxis: { name: '-Log10(P-value)', nameLocation: 'middle', nameGap: 30 },
    series: [
      { name: 'Up-regulated', type: 'scatter', symbolSize: 6, itemStyle: { color: '#FF4757', opacity: 0.8 }, data: significantUp },
      { name: 'Down-regulated', type: 'scatter', symbolSize: 6, itemStyle: { color: '#1E90FF', opacity: 0.8 }, data: significantDown },
      { name: 'Not Significant', type: 'scatter', symbolSize: 4, itemStyle: { color: '#d1d5db', opacity: 0.5 }, data: notSignificant },
    ],
  })
}

function renderHeatmapPlot(heatmapData: any) {
  if (!heatmapChartRef.value) return
  const myChart = heatmapChart.init(heatmapChartRef.value)

  const { samples, genes, values: rawData, sample_labels: labels } = heatmapData

  const markLines: any[] = []
  let currentLabel = labels[0]
  for (let i = 1; i < labels.length; i++) {
    if (labels[i] !== currentLabel) {
      markLines.push({ xAxis: i - 0.5 })
      currentLabel = labels[i]
    }
  }

  const clusterBarData = labels.map((label: number, index: number) => [index, 0, label])

  myChart.setOption({
    grid: [
      { id: 'top_bar', height: '20px', top: '50px', left: '25%', right: '5%' },
      { id: 'main_map', top: '75px', bottom: '50px', left: '25%', right: '5%' },
    ],
    tooltip: {
      position: 'top',
      formatter(params: any) {
        if (params.seriesIndex === 0) {
          return `Sample: <b>${samples[params.data[0]]}</b><br/>Cluster: ${params.data[2]}`
        }
        return `Gene: <b>${genes[params.data[1]]}</b><br/>Sample: ${samples[params.data[0]]}<br/>Z-Score: ${params.data[2].toFixed(3)}`
      },
    },
    xAxis: [
      { type: 'category', data: samples, gridIndex: 0, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
      { type: 'category', data: samples, gridIndex: 1, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
    ],
    yAxis: [
      { type: 'category', data: ['Cluster'], gridIndex: 0, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontWeight: 'bold' } },
      { type: 'category', data: genes, gridIndex: 1, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontSize: 10, interval: 0 }, splitLine: { show: false } },
    ],
    visualMap: [
      { type: 'piecewise', seriesIndex: 0, categories: [...new Set(labels)].sort(), orient: 'horizontal', top: 0, right: 10, dimension: 2, inRange: { color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'] }, text: ['Cluster ID'], itemWidth: 15, itemHeight: 15 },
      { type: 'continuous', seriesIndex: 1, min: -2, max: 2, calculable: true, orient: 'horizontal', top: 0, left: 'center', inRange: { color: ['#313695', '#4575b4', '#e0f3f8', '#fee090', '#f46d43', '#a50026'] }, text: ['High Exp', 'Low Exp'], dimension: 2 },
    ],
    series: [
      { name: 'Cluster Annotation', type: 'heatmap', xAxisIndex: 0, yAxisIndex: 0, data: clusterBarData, label: { show: false }, itemStyle: { borderColor: '#fff', borderWidth: 0.5 } },
      { name: 'Gene Expression', type: 'heatmap', xAxisIndex: 1, yAxisIndex: 1, data: rawData, itemStyle: { borderWidth: 0 }, markLine: { symbol: ['none', 'none'], label: { show: false }, silent: true, lineStyle: { color: '#000', type: 'dashed', width: 1, opacity: 1 }, data: markLines } },
    ],
  })
}

watch(diffResult, async (value) => {
  if (value) {
    await nextTick()
    renderVolcanoPlot()
    renderHeatmapPlot(value.heatmap_data)
  }
}, { immediate: true })

async function handleOmicsTypeChange() {
  if (!backendResponse.value?.data?.plot_data) return
  await runDifferentialAnalysis({ silent: true })
  if (diffResult.value?.volcano_data) await runEnrichmentAnalysis('GO', { silent: true })
}

onUnmounted(() => {
  volcanoChart.dispose()
  heatmapChart.dispose()
})
</script>

<template>
  <div ref="diffAreaRef" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200 bg-purple-50 flex justify-between items-center">
      <h3 class="m-0 text-lg text-purple-700 flex items-center gap-3">
        <span class="bg-purple-700 text-white w-6 h-6 flex items-center justify-center rounded-md text-sm font-bold">B</span>
        差异表达分析 (Differential Expression)
      </h3>
      <div class="flex gap-3 items-center">
        <select v-model="selectedDiffOmicsType" @change="handleOmicsTypeChange" class="min-w-[120px] px-2 py-1.5 border border-slate-200 rounded-lg text-[13px] bg-white cursor-pointer outline-none focus:border-primary">
          <option value="" disabled>请选择组学层</option>
          <option v-for="type in uploadedOmicsTypes" :key="type" :value="type">{{ type }}</option>
        </select>
      </div>
    </div>
    <div class="p-6">
      <p class="text-slate-500 text-sm m-0 mb-5">基于聚类结果执行 One-vs-Rest 差异基因计算，鉴定出每个亚型的特异性高表达基因。</p>

      <div v-if="diffErrorMessage" class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-[13px] mb-5">{{ diffErrorMessage }}</div>

      <div v-if="isDiffLoading" class="bg-slate-50 border border-slate-200 text-slate-600 p-4 rounded-lg text-sm">
        正在计算差异表达结果...
      </div>

      <div v-if="diffResult" class="grid grid-cols-2 gap-6 max-[1100px]:grid-cols-1">
        <div class="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <div class="bg-slate-100 px-5 py-3 border-b border-slate-200 flex justify-between items-center">
            <div class="font-semibold text-sm text-slate-700">🌋 差异火山图</div>
            <select v-model="selectedVolcanoCluster" @change="renderVolcanoPlot" class="px-2 py-1 border border-slate-200 rounded-lg text-[13px] bg-white cursor-pointer outline-none">
              <option v-for="cid in Object.keys(diffResult.volcano_data)" :key="cid" :value="Number(cid)">Cluster {{ cid }}</option>
            </select>
          </div>
          <div ref="volcanoChartRef" class="w-full h-[500px]" />
        </div>

        <div class="border border-slate-200 rounded-xl bg-white overflow-hidden">
          <div class="bg-slate-100 px-5 py-3 border-b border-slate-200 flex justify-between items-center">
            <div class="font-semibold text-sm text-slate-700">🔥 差异基因热图 (Top 10)</div>
          </div>
          <div ref="heatmapChartRef" class="w-full h-[500px]" />
        </div>
      </div>
    </div>
  </div>
</template>
