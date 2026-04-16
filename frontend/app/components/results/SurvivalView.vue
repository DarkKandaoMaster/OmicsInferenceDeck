<script setup lang="ts">
import * as echarts from 'echarts'
import { useEcharts } from '~/composables/ui/useEcharts'
import { useSurvival } from '~/composables/domain/useSurvival'
import { formatPValue } from '~/utils/formatters'

const survivalChartRef = ref<HTMLElement | null>(null)
const survivalAreaRef = ref<HTMLElement | null>(null)

const survivalChart = useEcharts()
const { survivalResult, isSurvivalLoading, runSurvivalAnalysis } = useSurvival()

function renderSurvivalChart(kmData: any[]) {
  if (!survivalChartRef.value) return
  const myChart = survivalChart.init(survivalChartRef.value)

  const colorPalette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
  const series: any[] = []

  kmData.forEach((group: any, index: number) => {
    const groupColor = colorPalette[index % colorPalette.length]

    series.push({
      name: group.name,
      type: 'line',
      step: 'end',
      data: group.times.map((t: number, i: number) => [t, group.probs[i]]),
      symbol: 'circle',
      symbolSize: 10,
      showSymbol: true,
      itemStyle: { color: groupColor, opacity: 0 },
      emphasis: { itemStyle: { opacity: 1 } },
      lineStyle: { width: 2, color: groupColor },
    })

    const censoredData: number[][] = []
    if (group.censored_times) {
      group.censored_times.forEach((t: number, i: number) => {
        censoredData.push([t, group.censored_probs[i]])
      })
    }
    if (censoredData.length > 0) {
      series.push({
        name: group.name,
        type: 'scatter',
        data: censoredData,
        symbol: 'rect',
        symbolSize: [1, 6],
        itemStyle: { color: groupColor, opacity: 0.7 },
        cursor: 'default',
      })
    }
  })

  myChart.setOption({
    series,
    tooltip: { trigger: 'item', triggerOn: 'none', formatter(params: any) { return `${params.seriesName}<br/>Time: ${params.value[0]}<br/>Probability: ${params.value[1].toFixed(4)}` } },
    legend: { orient: 'horizontal', bottom: '0%' },
    xAxis: { type: 'value', name: 'Time (OS.time)', nameLocation: 'middle', nameGap: 30, min: 0, splitLine: { show: false } },
    yAxis: { type: 'value', name: 'Survival Probability (OS)', nameLocation: 'middle', nameGap: 30, min: 0, max: 1, splitLine: { show: false } },
  })

  myChart.getZr().on('mousemove', (params: any) => {
    const pointInPixel = [params.offsetX, params.offsetY]
    let minDistance = Infinity
    let nearestItem: any = null
    series.forEach((s: any, sIdx: number) => {
      if (s.type === 'scatter') return
      s.data.forEach((d: any, dIdx: number) => {
        const point = myChart.convertToPixel({ seriesIndex: sIdx }, d)
        if (point) {
          const px = point as any
          const dx = px[0] - pointInPixel[0]
          const dy = px[1] - pointInPixel[1]
          const distanceSquared = dx * dx + dy * dy
          if (distanceSquared < minDistance) {
            minDistance = distanceSquared
            nearestItem = { seriesIndex: sIdx, dataIndex: dIdx, distance: Math.sqrt(distanceSquared) }
          }
        }
      })
    })
    if (nearestItem && nearestItem.distance < 100) {
      myChart.dispatchAction({ type: 'downplay' })
      myChart.dispatchAction({ type: 'highlight', seriesIndex: nearestItem.seriesIndex, dataIndex: nearestItem.dataIndex })
      myChart.dispatchAction({ type: 'showTip', seriesIndex: nearestItem.seriesIndex, dataIndex: nearestItem.dataIndex })
    } else {
      myChart.dispatchAction({ type: 'downplay' })
      myChart.dispatchAction({ type: 'hideTip' })
    }
  })
}

async function handleRunSurvival() {
  await runSurvivalAnalysis()
  if (survivalResult.value) {
    await nextTick()
    renderSurvivalChart(survivalResult.value.km_data)
    survivalAreaRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

onUnmounted(() => survivalChart.dispose())
</script>

<template>
  <div ref="survivalAreaRef" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200 bg-amber-50 flex justify-between items-center">
      <h3 class="m-0 text-lg text-amber-700 flex items-center gap-3">
        <span class="bg-amber-700 text-white w-6 h-6 flex items-center justify-center rounded-md text-sm font-bold">D</span>
        临床预后生存分析 (Survival Analysis)
      </h3>
      <button @click="handleRunSurvival" :disabled="isSurvivalLoading" class="border-none rounded-lg text-[13px] font-medium px-4 py-2 cursor-pointer text-white transition-all bg-amber-600 disabled:opacity-60 disabled:cursor-not-allowed">
        {{ isSurvivalLoading ? '计算中...' : '绘制 KM 曲线' }}
      </button>
    </div>
    <div class="p-6">
      <p class="text-slate-500 text-sm m-0 mb-5">基于临床数据 (OS &amp; OS.time) 评估不同分子亚型的预后差异。</p>

      <div v-if="survivalResult">
        <div class="bg-amber-50 border border-amber-200 text-amber-700 p-3 rounded-lg text-[13px] mb-5">
          ⚠️ <strong>提示：</strong>有 <strong>{{ survivalResult.lost_samples }}</strong> 个已聚类的病人因缺少临床数据，在计算生存曲线时被丢弃。
        </div>
        <div class="bg-slate-100 p-5 rounded-lg text-center border border-slate-200" :class="{ '!bg-amber-50 !border-amber-200': survivalResult.p_value < 0.05 }">
          <span class="text-base text-slate-500 mr-3">Log-Rank P-value:</span>
          <span class="text-2xl font-extrabold text-slate-900">{{ formatPValue(survivalResult.p_value) }}</span>
          <span v-if="survivalResult.p_value < 0.05" class="ml-3 bg-amber-500 text-white px-2.5 py-1 rounded-full text-xs font-bold">显著差异 ✨</span>
        </div>
        <div class="border border-slate-200 rounded-xl bg-white overflow-hidden mt-6">
          <div ref="survivalChartRef" class="w-full h-[500px]" />
        </div>
      </div>
    </div>
  </div>
</template>
