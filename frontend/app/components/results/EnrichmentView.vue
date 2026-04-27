<script setup lang="ts">
import { renderEnrichmentBar, renderEnrichmentBubble } from '~/utils/api'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useSession } from '~/composables/core/useSession'

const {
  enrichmentResult, isEnrichmentLoading, enrichmentType,
  selectedEnrichmentCluster, bubbleChartMode, enrichmentErrorMessage,
  runEnrichmentAnalysis,
} = useEnrichment()
const { diffResult } = useDifferential()
const { sessionId } = useSession()

async function handleEnrichmentTypeChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  await runEnrichmentAnalysis(value, { silent: true })
}

async function handleClusterChange() {
  if (!enrichmentResult.value) return
  const res = await renderEnrichmentBar({
    session_id: sessionId.value,
    database: enrichmentResult.value.database || enrichmentType.value || 'GO',
    cluster_id: selectedEnrichmentCluster.value,
  })
  enrichmentResult.value = { ...enrichmentResult.value, bar_svg: res.data.svg }
}

async function handleBubbleModeChange() {
  if (!enrichmentResult.value) return
  const res = await renderEnrichmentBubble({
    session_id: sessionId.value,
    database: enrichmentResult.value.database || enrichmentType.value || 'GO',
    mode: bubbleChartMode.value,
  })
  enrichmentResult.value = { ...enrichmentResult.value, bubble_svg: res.data.svg }
}
</script>

<template>
  <div v-if="diffResult && isEnrichmentLoading" class="result-card col-span-2">
    <div class="p-5 text-sm text-slate-600">正在查询 {{ enrichmentType || 'GO' }} 富集结果...</div>
  </div>

  <div v-if="diffResult && enrichmentErrorMessage" class="result-card col-span-2">
    <div class="p-5 text-sm text-red-700">{{ enrichmentErrorMessage }}</div>
  </div>

  <template v-if="diffResult && enrichmentResult">
    <div class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">富集分析条形图</div>
        <div class="flex items-center gap-3">
          <select :value="enrichmentResult.database || enrichmentType || 'GO'" @change="handleEnrichmentTypeChange" :disabled="isEnrichmentLoading" class="chart-select">
            <option value="GO">GO</option>
            <option value="KEGG">KEGG</option>
          </select>
          <select v-model.number="selectedEnrichmentCluster" @change="handleClusterChange" class="chart-select">
            <option v-for="cid in enrichmentResult.clusters" :key="cid" :value="cid">Cluster {{ cid }}</option>
          </select>
        </div>
      </div>
      <div class="svg-chart" v-html="enrichmentResult.bar_svg" />
    </div>

    <div class="result-card">
      <div class="result-card-header">
        <div class="result-card-title">富集分析气泡图</div>
        <div class="flex gap-4 text-[13px] text-slate-700">
          <label class="flex items-center gap-1.5">
            <input type="radio" v-model="bubbleChartMode" value="combined" @change="handleBubbleModeChange" />
            按簇展示
          </label>
          <label class="flex items-center gap-1.5">
            <input type="radio" v-model="bubbleChartMode" value="by_gene" @change="handleBubbleModeChange" />
            按基因数展示
          </label>
        </div>
      </div>
      <div class="svg-chart" v-html="enrichmentResult.bubble_svg" />
    </div>
  </template>
</template>
