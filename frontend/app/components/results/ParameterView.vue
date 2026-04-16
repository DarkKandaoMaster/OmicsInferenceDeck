<script setup lang="ts">
import { useEcharts } from '~/composables/ui/useEcharts'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'

const psChartRef = ref<HTMLElement | null>(null)
const psChart = useEcharts()
const { psResult, psParam1, psParam2 } = useAlgorithmState()

// Expose a local render function that uses the local DOM ref
function renderPsChart() {
  if (!psChartRef.value || !psResult.value) return
  const myChart = psChart.init(psChartRef.value)

  const allResults = psResult.value.all_results
  const p1 = psParam1.value
  const p2 = psParam2.value

  if (p1 && p2 && p1 !== p2) {
    // 3D surface
    const data = allResults.map((item: any) => [item.params[p1], item.params[p2], item.score])
    myChart.setOption({
      tooltip: {},
      visualMap: {
        show: false,
        min: Math.min(...data.map((d: number[]) => d[2])),
        max: Math.max(...data.map((d: number[]) => d[2])),
        inRange: { color: ['#313695', '#4575b4', '#e0f3f8', '#fee090', '#f46d43', '#a50026'] },
      },
      xAxis3D: { type: 'value', name: p1 },
      yAxis3D: { type: 'value', name: p2 },
      zAxis3D: { type: 'value', name: '-Log10(P)' },
      grid3D: { viewControl: { projection: 'perspective' } },
      series: [{ type: 'surface', data, wireframe: { show: true, lineStyle: { color: 'rgba(0,0,0,0.3)', width: 1 } } }],
    })
  } else if (p1) {
    // 2D line
    const uniqueX = [...new Set(allResults.map((item: any) => item.params[p1] as number))].sort((a: any, b: any) => a - b)
    const yData = uniqueX.map((x) => {
      const matched = allResults.filter((item: any) => item.params[p1] === x)
      return Math.max(...matched.map((m: any) => m.score))
    })
    myChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: uniqueX, name: p1, nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: '-Log10(P-value)', nameLocation: 'middle', nameGap: 40 },
      series: [{ type: 'line', data: yData, smooth: true, lineStyle: { width: 3 } }],
    })
  }
}

// Auto-render when result changes
watch(psResult, async (val) => {
  if (val) {
    await nextTick()
    renderPsChart()
  }
}, { immediate: true })

// Re-render when axes change
watch([psParam1, psParam2], () => {
  if (psResult.value) renderPsChart()
})

onUnmounted(() => psChart.dispose())
</script>

<template>
  <div v-if="psResult" class="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200">
      <h3 class="m-0 text-lg">🔬 参数敏感性分析结果 (Parameter Search)</h3>
    </div>
    <div class="p-6">
      <!-- 最优参数卡片 -->
      <div class="flex gap-4 bg-orange-50 border border-orange-200 p-6 rounded-xl mb-6">
        <div class="text-3xl">🏆</div>
        <div>
          <h4 class="m-0 mb-3 text-lg text-orange-900">最优参数组合</h4>
          <div class="flex gap-5 mb-2">
            <span class="text-[15px] text-orange-700"><strong>参数:</strong> {{ psResult.best_params }}</span>
            <span class="text-[15px] font-bold text-red-600"><strong>-Log10(P):</strong> {{ psResult.best_score.toFixed(4) }}</span>
          </div>
          <p class="m-0 text-[13px] text-orange-300">得分越高，代表该参数组合下聚类生成的生存差异越显著。</p>
        </div>
      </div>

      <!-- 参数敏感性图表 -->
      <div class="border border-slate-200 rounded-xl bg-white overflow-hidden">
        <div class="bg-slate-100 px-5 py-3 border-b border-slate-200 flex justify-between items-center">
          <div class="font-semibold text-sm text-slate-700">📈 参数敏感性分布图</div>
          <div class="flex gap-4">
            <div class="flex items-center gap-1.5">
              <label class="text-xs">X轴:</label>
              <select v-model="psParam1" class="px-2 py-1 border border-slate-200 rounded-lg text-[13px] bg-white cursor-pointer outline-none focus:border-primary">
                <option value="n_clusters">K值 (n_clusters)</option>
                <option value="max_iter">最大迭代 (max_iter)</option>
                <option value="n_neighbors">邻居数 (谱聚类)</option>
              </select>
            </div>
            <div class="flex items-center gap-1.5">
              <label class="text-xs">Y轴:</label>
              <select v-model="psParam2" class="px-2 py-1 border border-slate-200 rounded-lg text-[13px] bg-white cursor-pointer outline-none focus:border-primary">
                <option value="">无 (绘制2D折线图)</option>
                <option value="n_clusters">K值 (n_clusters)</option>
                <option value="max_iter">最大迭代 (max_iter)</option>
                <option value="n_neighbors">邻居数 (谱聚类)</option>
              </select>
            </div>
          </div>
        </div>
        <div ref="psChartRef" class="w-full h-[500px]" />
      </div>
    </div>
  </div>
</template>
