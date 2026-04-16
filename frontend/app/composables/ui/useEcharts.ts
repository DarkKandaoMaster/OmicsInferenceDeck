import * as echarts from 'echarts'
import 'echarts-gl'

/**
 * 每个图表组件内调用一次，返回当前组件的 ECharts 实例管家。
 * 内部会自动处理 dispose / 重 init。
 */
export function useEcharts() {
  const chart = shallowRef<echarts.ECharts | null>(null)

  /** 初始化（或重新初始化）一个 echarts 实例并返回 */
  function init(el: HTMLElement): echarts.ECharts {
    const existing = echarts.getInstanceByDom(el)
    if (existing) existing.dispose()
    chart.value = echarts.init(el)
    return chart.value
  }

  function setOption(option: echarts.EChartsOption) {
    chart.value?.setOption(option)
  }

  function resize() {
    chart.value?.resize()
  }

  function dispose() {
    chart.value?.dispose()
    chart.value = null
  }

  return { chart, init, setOption, resize, dispose }
}
