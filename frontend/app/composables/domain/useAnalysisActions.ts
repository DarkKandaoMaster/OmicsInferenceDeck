import { computeAwaMetrics, computeBiologyMetrics, computeClinicalMetrics, computeMetrics, evaluateCustom, renderPredClusterScatter, renderInputClusterScatter, runAlgorithm, runParameterSearch } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useUIState } from '~/composables/core/useUIState'
import { useDataState } from '~/composables/domain/useDataState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useSurvival } from '~/composables/domain/useSurvival'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const backendResponse = ref<any>(null)
const analysisStatus = ref('')
const clusteringDone = ref(false)

export function useAnalysisActions() {
  const { sessionId } = useSession()
  const { isLoading, setError, clearError } = useUIState()
  const {
    clinicalFile,
    isOmicsUploaded,
    isClinicalUploaded,
    omicsFileConfigs,
    doUploadOmics,
    doUploadClinical,
    doUploadExpressionMatrix,
    expressionMatrixFile,
    isExpressionMatrixUploaded,
    isCustomEvalMode,
    customEvalFile,
  } = useDataState()
  const {
    selectedAlgorithm,
    kValue,
    maxIter,
    nNeighbors,
    randomSeed,
    currentReduction,
    testNClusters,
    testMaxIter,
    testNNeighbors,
    psResult,
    isPsLoading,
    psParam1,
    psParam2,
  } = useAlgorithmState()
  const { enabledMetrics, enabledCharts, runDifferential, runEnrichment } = useResultSelection()

  function ensureBackendResponseShape() {
    if (!backendResponse.value) {
      backendResponse.value = { data: {} }
    } else if (!backendResponse.value.data) {
      backendResponse.value = { ...backendResponse.value, data: {} }
    }
  }

  function mergeIntoBackendResponse(patch: Record<string, any>, topLevel?: Record<string, any>) {
    ensureBackendResponseShape()
    backendResponse.value = {
      ...backendResponse.value,
      ...(topLevel || {}),
      data: {
        ...backendResponse.value.data,
        ...patch,
      },
    }
  }

  async function runDownstreamAnalyses() {
    const { runDifferentialAnalysis, diffResult } = useDifferential()
    const { runEnrichmentAnalysis } = useEnrichment()
    const { runSurvivalAnalysis } = useSurvival()

    if (runDifferential.value) {
      analysisStatus.value = '正在运行差异表达分析...'
      await runDifferentialAnalysis({ silent: true })
    }

    if (runEnrichment.value && diffResult.value?.clusters) {
      analysisStatus.value = '正在运行功能富集分析...'
      await runEnrichmentAnalysis({ silent: true })
    }

    const databases: Array<'GO' | 'KEGG'> = ['GO', 'KEGG']

    if (enabledMetrics.biology) {
      analysisStatus.value = '正在计算生物学机制指标...'
      const results = await Promise.allSettled(
        databases.map(db =>
          computeBiologyMetrics({ session_id: sessionId.value, database: db }),
        ),
      )
      const biologyMetricsByDb: Record<string, any> = {}
      databases.forEach((db, idx) => {
        const r = results[idx]!
        if (r.status === 'fulfilled') {
          biologyMetricsByDb[db] = r.value.data?.data?.biology_metrics || null
        } else {
          const err: any = r.reason
          biologyMetricsByDb[db] = {
            error: err?.response?.data?.detail || '生物学机制指标计算失败',
          }
        }
      })
      mergeIntoBackendResponse({ biology_metrics_by_db: biologyMetricsByDb })
    }

    if (enabledMetrics.awa) {
      analysisStatus.value = '正在计算 AWA / 3D-AWA 指标...'
      const biologyByDb = backendResponse.value?.data?.biology_metrics_by_db || {}
      const results = await Promise.allSettled(
        databases.map(db =>
          computeAwaMetrics({
            session_id: sessionId.value,
            database: db,
            metrics: backendResponse.value?.data?.metrics || {},
            clinical_metrics: backendResponse.value?.data?.clinical_metrics || {},
            biology_metrics: biologyByDb[db] || {},
          }),
        ),
      )
      const awaMetricsByDb: Record<string, any> = {}
      databases.forEach((db, idx) => {
        const r = results[idx]!
        if (r.status === 'fulfilled') {
          awaMetricsByDb[db] = r.value.data?.data?.awa_metrics || null
        } else {
          const err: any = r.reason
          awaMetricsByDb[db] = {
            error: err?.response?.data?.detail || 'AWA / 3D-AWA 指标计算失败',
          }
        }
      })
      mergeIntoBackendResponse({ awa_metrics_by_db: awaMetricsByDb })
    }

    if (clinicalFile.value && enabledCharts.survival) {
      analysisStatus.value = '正在计算生存曲线...'
      await runSurvivalAnalysis({ silent: true })
    }
  }

  async function loadMetricsAndScatter() {
    backendResponse.value = { data: {} }

    if (enabledMetrics.cluster) {
      analysisStatus.value = '正在计算聚类评估指标...'
      try {
        const metricsRes = await computeMetrics({
          session_id: sessionId.value,
        })
        const { data: nestedData = {}, ...topLevel } = metricsRes.data || {}
        mergeIntoBackendResponse(nestedData, topLevel)
      } catch (_error) {
        // 缺失融合特征矩阵等情况下不让异常冒泡，避免中断后续分析
        mergeIntoBackendResponse({ metrics: null, feature_matrix_available: false })
      }
    }

    if (clinicalFile.value && enabledMetrics.clinical) {
      analysisStatus.value = '正在计算临床评估指标...'
      let clinicalMetrics: any = null
      try {
        const clinicalMetricsRes = await computeClinicalMetrics({
          session_id: sessionId.value,
        })
        clinicalMetrics = clinicalMetricsRes.data?.data?.clinical_metrics || null
      } catch (error: any) {
        clinicalMetrics = {
          error: error.response?.data?.detail || '临床评价指标计算失败',
        }
      }
      mergeIntoBackendResponse({ clinical_metrics: clinicalMetrics })
    }

    if (enabledCharts.inputClusterScatter) {
      analysisStatus.value = '正在绘制聚类前散点图...'
      try {
        const inputRes = await renderInputClusterScatter({
          session_id: sessionId.value,
          reduction: currentReduction.value,
          random_state: randomSeed.value,
        })
        mergeIntoBackendResponse({
          plots: {
            ...(backendResponse.value?.data?.plots || {}),
            input_cluster_scatter: inputRes.data.svg,
          },
        })
      } catch (_error) {
        // 失败不阻塞主流程
      }
    }

    if (enabledCharts.predClusterScatter) {
      analysisStatus.value = '正在绘制聚类散点图...'
      try {
        const plotRes = await renderPredClusterScatter({
          session_id: sessionId.value,
          reduction: currentReduction.value,
          random_state: randomSeed.value,
        })
        mergeIntoBackendResponse({
          reduction: currentReduction.value,
          plots: {
            ...(backendResponse.value?.data?.plots || {}),
            pred_cluster_scatter: plotRes.data.svg,
          },
        })
      } catch (_error) {
        // 失败不阻塞主流程
      }
    }
  }

  async function runAnalysisFlow() {
    if (isCustomEvalMode.value) {
      if (!customEvalFile.value) { alert('请先选择结果数据文件。'); return }

      isLoading.value = true
      clearError()
      backendResponse.value = null
      clusteringDone.value = false
      analysisStatus.value = '正在评估聚类结果...'

      try {
        if (omicsFileConfigs.value.length > 0 && !isOmicsUploaded.value) await doUploadOmics(sessionId.value)
        if (clinicalFile.value && !isClinicalUploaded.value) await doUploadClinical(sessionId.value)
        if (expressionMatrixFile.value && !isExpressionMatrixUploaded.value) await doUploadExpressionMatrix(sessionId.value)

        const formData = new FormData()
        formData.append('file', customEvalFile.value)
        formData.append('session_id', sessionId.value)

        await evaluateCustom(formData)
        clusteringDone.value = true
        await loadMetricsAndScatter()
        await runDownstreamAnalyses()
      } catch (error: any) {
        setError(error.response?.data?.detail || '评估失败，请检查数据。')
      } finally {
        analysisStatus.value = ''
        isLoading.value = false
      }
      return
    }

    if (omicsFileConfigs.value.length === 0) { alert('请先选择组学数据文件。'); return }
    if (selectedAlgorithm.value.length === 0) { alert('请先选择至少一种算法。'); return }

    isLoading.value = true
    clearError()
    backendResponse.value = null
    clusteringDone.value = false
    analysisStatus.value = '正在上传数据...'

    try {
      if (!isOmicsUploaded.value) await doUploadOmics(sessionId.value)
      if (clinicalFile.value && !isClinicalUploaded.value) await doUploadClinical(sessionId.value)
      if (expressionMatrixFile.value && !isExpressionMatrixUploaded.value) await doUploadExpressionMatrix(sessionId.value)

      analysisStatus.value = '正在跑算法...'
      await runAlgorithm({
        algorithm: selectedAlgorithm.value[0]!,
        timestamp: new Date().toISOString(),
        session_id: sessionId.value,
        n_clusters: kValue.value,
        random_state: randomSeed.value,
        max_iter: maxIter.value,
        n_neighbors: nNeighbors.value,
      })
      clusteringDone.value = true

      await loadMetricsAndScatter()
      await runDownstreamAnalyses()
    } catch (error: any) {
      setError(error.response?.data?.detail || '连接后端失败或上传出错。')
    } finally {
      analysisStatus.value = ''
      isLoading.value = false
    }
  }

  async function switchReduction(method: string) {
    if (currentReduction.value === method) return
    currentReduction.value = method

    isLoading.value = true
    try {
      const res = await renderPredClusterScatter({
        session_id: sessionId.value,
        reduction: currentReduction.value,
        random_state: randomSeed.value,
      })
      mergeIntoBackendResponse({
        reduction: currentReduction.value,
        plots: {
          ...(backendResponse.value?.data?.plots || {}),
          pred_cluster_scatter: res.data.svg,
        },
      })

      if (enabledCharts.inputClusterScatter) {
        try {
          const inputRes = await renderInputClusterScatter({
            session_id: sessionId.value,
            reduction: currentReduction.value,
            random_state: randomSeed.value,
          })
          mergeIntoBackendResponse({
            plots: {
              ...(backendResponse.value?.data?.plots || {}),
              input_cluster_scatter: inputRes.data.svg,
            },
          })
        } catch (_error) {
          // 失败不阻塞主流程
        }
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || '降维切换失败。')
    } finally {
      isLoading.value = false
    }
  }

  async function runParameterSearchFlow() {
    if (omicsFileConfigs.value.length === 0 || !clinicalFile.value) {
      alert('测试模式需要组学数据和临床数据。')
      return
    }
    if (selectedAlgorithm.value.length === 0) { alert('请先选择至少一种算法。'); return }
    if (selectedAlgorithm.value.length > 1) { alert('测试模式请只选择一种算法。'); return }

    isPsLoading.value = true
    psResult.value = null

    try {
      if (!isOmicsUploaded.value) await doUploadOmics(sessionId.value)
      if (!isClinicalUploaded.value) await doUploadClinical(sessionId.value)

      let paramGridObj: Record<string, number[]> = {}
      if (selectedAlgorithm.value[0] === 'K-means') {
        paramGridObj = {
          n_clusters: testNClusters.value.split(',').map(Number),
          max_iter: testMaxIter.value.split(',').map(Number),
        }
        psParam1.value = 'n_clusters'
        psParam2.value = 'max_iter'
      } else if (selectedAlgorithm.value[0] === 'Spectral Clustering') {
        paramGridObj = {
          n_clusters: testNClusters.value.split(',').map(Number),
          n_neighbors: testNNeighbors.value.split(',').map(Number),
        }
        psParam1.value = 'n_clusters'
        psParam2.value = 'n_neighbors'
      } else if (selectedAlgorithm.value[0] === 'Hclust') {
        paramGridObj = { n_clusters: testNClusters.value.split(',').map(Number) }
        psParam1.value = 'n_clusters'
        psParam2.value = ''
      } else if (selectedAlgorithm.value[0] === 'NEMO') {
        paramGridObj = { n_clusters: testNClusters.value.split(',').map(Number) }
        psParam1.value = 'n_clusters'
        psParam2.value = ''
      } else if (selectedAlgorithm.value[0] === 'SNF') {
        paramGridObj = {
          n_clusters: testNClusters.value.split(',').map(Number),
          n_neighbors: testNNeighbors.value.split(',').map(Number),
        }
        psParam1.value = 'n_clusters'
        psParam2.value = 'n_neighbors'
      } else if (selectedAlgorithm.value[0] === 'PIntMF') {
        paramGridObj = { n_clusters: testNClusters.value.split(',').map(Number) }
        psParam1.value = 'n_clusters'
        psParam2.value = ''
      } else if (selectedAlgorithm.value[0] === 'MOSD') {
        paramGridObj = { n_clusters: testNClusters.value.split(',').map(Number) }
        psParam1.value = 'n_clusters'
        psParam2.value = ''
      } else if (selectedAlgorithm.value[0] === 'Parea') {
        paramGridObj = { n_clusters: testNClusters.value.split(',').map(Number) }
        psParam1.value = 'n_clusters'
        psParam2.value = ''
      }

      const res = await runParameterSearch({
        algorithm: selectedAlgorithm.value[0]!,
        session_id: sessionId.value,
        param_grid: paramGridObj,
        random_state: randomSeed.value,
      })

      psResult.value = res.data
      psParam1.value = res.data.x_param || psParam1.value
      psParam2.value = res.data.y_param || ''
    } catch (error: any) {
      alert('测试模式运行失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      isPsLoading.value = false
    }
  }

  return {
    backendResponse,
    analysisStatus,
    clusteringDone,
    runAnalysisFlow,
    switchReduction,
    runParameterSearchFlow,
  }
}
