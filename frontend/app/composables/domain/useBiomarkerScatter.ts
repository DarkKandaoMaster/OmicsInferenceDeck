import { renderBiomarkerClusterScatter } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const biomarkerSvg = ref('')
const biomarkerGene = ref<string | null>(null)
const selectedBiomarkerCluster = ref(0)
const isBiomarkerLoading = ref(false)
let watcherInstalled = false

export function useBiomarkerScatter() {
  const { sessionId } = useSession()
  const { diffResult } = useDifferential()
  const { enabledCharts } = useResultSelection()

  async function renderBiomarkerScatter() {
    if (!diffResult.value) return
    isBiomarkerLoading.value = true
    try {
      const res = await renderBiomarkerClusterScatter({
        session_id: sessionId.value,
        cluster_id: selectedBiomarkerCluster.value,
      })
      biomarkerSvg.value = res.data.svg
      biomarkerGene.value = res.data.gene
    } finally {
      isBiomarkerLoading.value = false
    }
  }

  if (!watcherInstalled) {
    watcherInstalled = true
    watch(diffResult, (result) => {
      if (!result || !enabledCharts.biomarkerClusterScatter) return
      const clusters = result.clusters || []
      if (clusters.length === 0) return
      selectedBiomarkerCluster.value = result.selected_cluster ?? clusters[0]
      renderBiomarkerScatter()
    })
  }

  return {
    biomarkerSvg, biomarkerGene, selectedBiomarkerCluster, isBiomarkerLoading,
    renderBiomarkerScatter,
  }
}
