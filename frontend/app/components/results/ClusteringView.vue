<script setup lang="ts">
import { useEcharts } from '~/composables/ui/useEcharts'
import { useUIState } from '~/composables/core/useUIState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useAnalysisActions } from '~/composables/domain/useAnalysisActions'

const chartRef = ref<HTMLElement | null>(null)
const { init, dispose } = useEcharts()
const { isLoading } = useUIState()
const { currentReduction } = useAlgorithmState()
const { backendResponse, switchReduction } = useAnalysisActions()

function renderChart(plotData: any[]) {
  if (!chartRef.value || !plotData) return
  const myChart = init(chartRef.value)

  const series: any[] = []
  const clusters = [...new Set(plotData.map(item => item.cluster))].sort()
  clusters.forEach(clusterId => {
    const clusterPoints = plotData.filter(item => item.cluster === clusterId)
    series.push({
      name: `Cluster ${clusterId}`,
      type: 'scatter',
      symbolSize: 10,
      data: clusterPoints.map(p => [p.x, p.y, p.name]),
      itemStyle: { opacity: 0.8 },
    })
  })

  let axisPrefix = 'Dim'
  switch (currentReduction.value) {
    case 'PCA': axisPrefix = 'PC'; break
    case 't-SNE': axisPrefix = 't-SNE'; break
    case 'UMAP': axisPrefix = 'UMAP'; break
  }

  myChart.setOption({
    series,
    tooltip: {
      trigger: 'item',
      formatter(params: any) {
        return `<b>${params.data[2]}</b><br/>Cluster: ${params.seriesName}<br/>(x: ${params.data[0].toFixed(2)}, y: ${params.data[1].toFixed(2)})`
      },
    },
    legend: { bottom: '5%', data: clusters.map(c => `Cluster ${c}`) },
    xAxis: { name: `${axisPrefix} 1`, splitLine: { show: false } },
    yAxis: { name: `${axisPrefix} 2`, splitLine: { show: false } },
  })
}

// 监听数据变化自动绘图
watch(backendResponse, async (val) => {
  if (val?.data?.plot_data) {
    await nextTick()
    renderChart(val.data.plot_data)
  }
}, { immediate: true })

onUnmounted(() => dispose())
</script>

<template>
  <div v-if="backendResponse?.data?.plot_data" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200">
      <h3 class="m-0 text-lg flex items-center gap-3">
        <span class="bg-slate-900 text-white w-6 h-6 flex items-center justify-center rounded-md text-sm font-bold">A</span>
        聚类散点图
      </h3>
    </div>
    <div class="p-6">
      <div class="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div class="bg-slate-100 px-5 py-3 border-b border-slate-200 flex justify-between items-center">
          <div class="font-semibold text-sm text-slate-700">🎨 样本聚类分布</div>
          <div class="flex gap-4 items-center">
            <div class="inline-flex rounded-lg overflow-hidden border border-slate-200">
              <button @click="switchReduction('PCA')" :class="currentReduction === 'PCA' ? 'bg-primary text-white font-medium' : 'bg-white text-slate-500 hover:bg-slate-100'" :disabled="isLoading" class="border-none px-4 py-1.5 text-[13px] cursor-pointer border-r border-slate-200">PCA</button>
              <button @click="switchReduction('t-SNE')" :class="currentReduction === 't-SNE' ? 'bg-primary text-white font-medium' : 'bg-white text-slate-500 hover:bg-slate-100'" :disabled="isLoading" class="border-none px-4 py-1.5 text-[13px] cursor-pointer border-r border-slate-200">t-SNE</button>
              <button @click="switchReduction('UMAP')" :class="currentReduction === 'UMAP' ? 'bg-primary text-white font-medium' : 'bg-white text-slate-500 hover:bg-slate-100'" :disabled="isLoading" class="border-none px-4 py-1.5 text-[13px] cursor-pointer">UMAP</button>
            </div>
          </div>
        </div>
        <div ref="chartRef" class="w-full h-[500px]" />
      </div>
    </div>
  </div>
</template>
