import { renderBiomarkerClusterScatter } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useAnalysisLog } from '~/composables/core/useAnalysisLog'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const biomarkerSvg = ref('')
const biomarkerGene = ref<string | null>(null)
const selectedBiomarkerCluster = ref(0)
const selectedBiomarkerReduction = ref('t-SNE')
const isBiomarkerLoading = ref(false)
let watcherInstalled = false

export function useBiomarkerScatter() {
  const { sessionId } = useSession()
  const { diffResult } = useDifferential()
  const { displayedCharts } = useResultSelection()
  const { startStep, finishStep } = useAnalysisLog()

  // log=true 时在状态栏记录一行（仅运行流程触发的首次绘制需要）；用户切换降维不记录，与聚类前/后散点图一致。
  async function renderBiomarkerScatter(options: { log?: boolean } = {}) {
    if (!diffResult.value) return
    const step = options.log ? startStep('正在绘制生物标志物簇散点图…') : null
    isBiomarkerLoading.value = true
    try {
      const res = await renderBiomarkerClusterScatter({
        session_id: sessionId.value,
        cluster_id: selectedBiomarkerCluster.value,
        reduction: selectedBiomarkerReduction.value,
      })
      biomarkerSvg.value = res.data.svg
      biomarkerGene.value = res.data.gene
      if (step) finishStep(step, '✅ 生物标志物簇散点图已绘制')
    } catch (error) {
      // 失败不阻塞主流程，与聚类前/后散点图一致
      if (step) finishStep(step, '⚠️ 生物标志物簇散点图绘制失败（已跳过）', 'warning')
      else throw error
    } finally {
      isBiomarkerLoading.value = false
    }
  }

  function switchBiomarkerReduction(reduction: string) {
    if (selectedBiomarkerReduction.value === reduction) return
    selectedBiomarkerReduction.value = reduction
    renderBiomarkerScatter()
  }

  if (!watcherInstalled) {
    watcherInstalled = true
    watch(diffResult, (result) => {
      if (!result || !displayedCharts.biomarkerClusterScatter) return
      const clusters = result.clusters || []
      if (clusters.length === 0) return
      selectedBiomarkerCluster.value = result.selected_cluster ?? clusters[0]
      renderBiomarkerScatter({ log: true })
    }, { immediate: true })
  }

  return {
    biomarkerSvg, biomarkerGene, selectedBiomarkerCluster, selectedBiomarkerReduction, isBiomarkerLoading,
    renderBiomarkerScatter, switchBiomarkerReduction,
  }
}
