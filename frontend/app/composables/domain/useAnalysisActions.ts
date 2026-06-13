import { computeAwaMetrics, computeBiologyMetrics, computeClinicalMetrics, computeMetrics, evaluateCustom, renderPredClusterScatter, renderInputClusterScatter, runAlgorithm, runParameterSearch, uploadParameterMat } from '~/utils/api'
import { useSession } from '~/composables/core/useSession'
import { useUIState } from '~/composables/core/useUIState'
import { useAnalysisLog } from '~/composables/core/useAnalysisLog'
import { useRunControl } from '~/composables/core/useRunControl'
import { useDataState } from '~/composables/domain/useDataState'
import { useAlgorithmState } from '~/composables/domain/useAlgorithmState'
import { useDifferential } from '~/composables/domain/useDifferential'
import { useEnrichment } from '~/composables/domain/useEnrichment'
import { useSurvival } from '~/composables/domain/useSurvival'
import { useResultSelection } from '~/composables/domain/useResultSelection'

const backendResponse = ref<any>(null)
const clusteringDone = ref(false)
// 运行配置签名：运行开始时记录当时的 (模式, 参数敏感性) 配置。仅当“当前配置仍等于该签名”时，
// 结果区与状态栏才可见——切换模式/PS 即隐藏（修复跨模式残留），切回原配置则恢复。
const runSignature = ref<string | null>(null)
// 停止标记：abortRun 置位，下一轮运行启动时清掉“已上传”缓存以强制从头重跑（而非跳过上传从中断处续跑）。
const wasAborted = ref(false)

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
    captureDataDisplaySnapshot,
    uploadStatus,
    clinicalUploadStatus,
    expressionMatrixUploadStatus,
    expressionMatrixFile,
    isExpressionMatrixUploaded,
    isCustomEvalMode,
    customEvalFile,
    isCustomEvalTestMode,
    customEvalMatFile,
    matXCol,
    matYCol,
    matScoreCol,
    matXLabel,
    matYLabel,
  } = useDataState()
  const {
    selectedAlgorithm,
    kValue,
    maxIter,
    nNeighbors,
    randomSeed,
    inputReduction,
    predReduction,
    isInputReductionLoading,
    isPredReductionLoading,
    testNClusters,
    testMaxIter,
    testNNeighbors,
    psResult,
    isPsLoading,
    psParam1,
    psParam2,
    isTestMode,
    captureAlgorithmDisplaySnapshot,
  } = useAlgorithmState()
  const { enabledMetrics, enabledCharts, runDifferential, runEnrichment, captureSelectionSnapshot } = useResultSelection()
  const { resetLog, startStep, finishStep, failStep, logStep, markRunningAsTerminated } = useAnalysisLog()
  const { startRun, invalidate, isStale } = useRunControl()

  // 当前 (模式, 参数敏感性) 配置签名。自定义模式看 isCustomEvalTestMode，内置模式看 isTestMode。
  const currentSignature = computed(
    () => `${isCustomEvalMode.value ? 'custom' : 'internal'}|${(isCustomEvalMode.value ? isCustomEvalTestMode.value : isTestMode.value) ? 'ps' : 'std'}`,
  )

  // 结果区与状态栏可见的唯一门控：跑过（runSignature 非空）且当前配置仍等于运行时的配置。
  const resultsVisible = computed(
    () => runSignature.value !== null && runSignature.value === currentSignature.value,
  )

  // 运行真正提交时调用：记录当前配置为签名，使结果区与状态栏在该配置下可见。
  function markRunStarted() {
    runSignature.value = currentSignature.value
    // 冻结展示快照：结果区的显示门控（图表选择、组学层下拉选项、富集图癌症亚型）只读这份快照，
    // 之后左侧 Section 1/2/3 的编辑不再改动已展示的结果。run logic 仍读 live 状态（此刻 live==快照）。
    captureSelectionSnapshot()
    captureDataDisplaySnapshot()
    captureAlgorithmDisplaySnapshot()
  }

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

  // 停止后再次运行：清掉“已上传”缓存标记，强制下一轮从头重新上传（重现上传步骤），
  // 而不是因 isXUploaded 仍为 true 跳过上传、看起来像从中断处续跑。
  function resetForFreshRunIfAborted() {
    if (!wasAborted.value) return
    isOmicsUploaded.value = false
    isClinicalUploaded.value = false
    isExpressionMatrixUploaded.value = false
    wasAborted.value = false
  }

  // 上传步骤：进行中 → 直接复用 doUpload* 写入的状态文本（已含 ✅/⚠️/❌ 细节）作为成功/失败文案。
  async function uploadStep(label: string, statusRef: { value: string }, doUpload: () => Promise<void>, token: number) {
    const entry = startStep(label)
    try {
      await doUpload()
      if (isStale(token)) return   // 运行已被停止：跳过 finishStep，保留“已停止”标记
      finishStep(entry, statusRef.value)
    } catch (error) {
      if (isStale(token)) return   // 停止导致的异常：吞掉，不写失败标记
      failStep(entry, statusRef.value)
      throw error
    }
  }

  async function runDownstreamAnalyses(token: number) {
    const { runDifferentialAnalysis, diffResult } = useDifferential()
    const { runEnrichmentAnalysis } = useEnrichment()
    const { runSurvivalAnalysis } = useSurvival()

    // 差异/富集/生存由各自 composable 自报日志，这里不再额外包一层，避免重复行。
    // 生存分析独立于差异/富集（仅依赖临床数据），按图表展示顺序先行绘制。
    if (clinicalFile.value && enabledCharts.survival) {
      if (isStale(token)) return
      await runSurvivalAnalysis({ silent: true, isStale: () => isStale(token) })
    }

    if (runDifferential.value) {
      if (isStale(token)) return
      await runDifferentialAnalysis({ silent: true, isStale: () => isStale(token) })
    }

    if (runEnrichment.value && diffResult.value?.clusters) {
      if (isStale(token)) return
      await runEnrichmentAnalysis({ silent: true, isStale: () => isStale(token) })
    }

    const databases: Array<'GO' | 'KEGG'> = ['GO', 'KEGG']

    if (enabledMetrics.biology) {
      if (isStale(token)) return
      const biologyStep = startStep('正在计算生物学机制指标…')
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
      if (isStale(token)) return
      mergeIntoBackendResponse({ biology_metrics_by_db: biologyMetricsByDb })
      const biologyFailed = databases.every(db => biologyMetricsByDb[db]?.error)
      if (biologyFailed) finishStep(biologyStep, '⚠️ 生物学机制指标计算失败（已跳过）', 'warning')
      else finishStep(biologyStep, '✅ 生物学机制指标已计算')
    }

    if (enabledMetrics.awa) {
      if (isStale(token)) return
      const awaStep = startStep('正在计算 AWA / 3D-AWA 指标…')
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
      if (isStale(token)) return
      mergeIntoBackendResponse({ awa_metrics_by_db: awaMetricsByDb })
      const awaFailed = databases.every(db => awaMetricsByDb[db]?.error)
      if (awaFailed) finishStep(awaStep, '⚠️ AWA / 3D-AWA 指标计算失败（已跳过）', 'warning')
      else finishStep(awaStep, '✅ AWA / 3D-AWA 指标已计算')
    }
  }

  async function loadMetricsAndScatter(token: number) {
    backendResponse.value = { data: {} }

    if (enabledMetrics.cluster) {
      if (isStale(token)) return
      const step = startStep('正在计算聚类评估指标…')
      try {
        const metricsRes = await computeMetrics({
          session_id: sessionId.value,
        })
        if (isStale(token)) return
        const { data: nestedData = {}, ...topLevel } = metricsRes.data || {}
        mergeIntoBackendResponse(nestedData, topLevel)
        finishStep(step, '✅ 聚类评估指标已计算')
      } catch (_error) {
        if (isStale(token)) return
        // 缺失融合特征矩阵等情况下不让异常冒泡，避免中断后续分析
        mergeIntoBackendResponse({ metrics: null, feature_matrix_available: false })
        finishStep(step, '⚠️ 聚类评估指标不可用（缺融合特征矩阵，已跳过）', 'warning')
      }
    }

    if (clinicalFile.value && enabledMetrics.clinical) {
      if (isStale(token)) return
      const step = startStep('正在计算临床评估指标…')
      let clinicalMetrics: any = null
      try {
        const clinicalMetricsRes = await computeClinicalMetrics({
          session_id: sessionId.value,
        })
        if (isStale(token)) return
        clinicalMetrics = clinicalMetricsRes.data?.data?.clinical_metrics || null
        finishStep(step, '✅ 临床评估指标已计算')
      } catch (error: any) {
        if (isStale(token)) return
        clinicalMetrics = {
          error: error.response?.data?.detail || '临床评价指标计算失败',
        }
        finishStep(step, '⚠️ 临床评估指标计算失败（已跳过）', 'warning')
      }
      mergeIntoBackendResponse({ clinical_metrics: clinicalMetrics })
    }

    if (enabledCharts.inputClusterScatter) {
      if (isStale(token)) return
      const step = startStep('正在绘制聚类前散点图…')
      try {
        const inputRes = await renderInputClusterScatter({
          session_id: sessionId.value,
          reduction: inputReduction.value,
          random_state: randomSeed.value,
        })
        if (isStale(token)) return
        mergeIntoBackendResponse({
          plots: {
            ...(backendResponse.value?.data?.plots || {}),
            input_cluster_scatter: inputRes.data.svg,
          },
        })
        finishStep(step, '✅ 聚类前散点图已绘制')
      } catch (_error) {
        if (isStale(token)) return
        // 失败不阻塞主流程
        finishStep(step, '⚠️ 聚类前散点图绘制失败（已跳过）', 'warning')
      }
    }

    if (enabledCharts.predClusterScatter) {
      if (isStale(token)) return
      const step = startStep('正在绘制聚类散点图…')
      try {
        const plotRes = await renderPredClusterScatter({
          session_id: sessionId.value,
          reduction: predReduction.value,
          random_state: randomSeed.value,
        })
        if (isStale(token)) return
        mergeIntoBackendResponse({
          reduction: predReduction.value,
          plots: {
            ...(backendResponse.value?.data?.plots || {}),
            pred_cluster_scatter: plotRes.data.svg,
          },
        })
        finishStep(step, '✅ 聚类散点图已绘制')
      } catch (_error) {
        if (isStale(token)) return
        // 失败不阻塞主流程
        finishStep(step, '⚠️ 聚类散点图绘制失败（已跳过）', 'warning')
      }
    }
  }

  async function runAnalysisFlow() {
    if (isCustomEvalMode.value) {
      // 参数敏感性分析（.mat 上传）：不依赖任何原始组学/临床文件，直接读 .mat 现成列绘图
      if (isCustomEvalTestMode.value) {
        if (!customEvalMatFile.value) { alert('请先选择 .mat 结果文件。'); return }

        const token = startRun()
        isLoading.value = true   // 驱动运行按钮的禁用/转圈，避免重复提交
        isPsLoading.value = true
        psResult.value = null
        resetLog()
        markRunStarted()

        try {
          const formData = new FormData()
          formData.append('file', customEvalMatFile.value)
          formData.append('session_id', sessionId.value)
          formData.append('x_col', String(matXCol.value))
          formData.append('score_col', String(matScoreCol.value))
          formData.append('x_label', matXLabel.value)
          // Y 列号留空（null）则传空字符串 → 后端画 2D 曲线
          formData.append('y_col', matYCol.value == null ? '' : String(matYCol.value))
          formData.append('y_label', matYLabel.value)

          await logStep('正在绘制参数敏感性图…', async () => {
            const res = await uploadParameterMat(formData)
            if (isStale(token)) return   // 停止：丢弃结果，不渲染
            psResult.value = res.data
            psParam1.value = res.data.x_param || matXLabel.value
            psParam2.value = res.data.y_param || ''
          })
        } catch (error: any) {
          if (isStale(token)) return   // 停止导致的异常：不弹 alert
          alert('参数敏感性分析失败: ' + (error.response?.data?.detail || error.message))
        } finally {
          // 仅当前运行才复位 loading；过期（被停止/已被新一轮接管）的旧运行不许动这两个标记，
          // 否则旧请求迟到返回时会把新一轮的 isLoading 清掉，按钮提前恢复可用。
          if (!isStale(token)) {
            isPsLoading.value = false
            isLoading.value = false
          }
        }
        return
      }

      if (!customEvalFile.value) { alert('请先选择结果数据文件。'); return }

      const token = startRun()
      isLoading.value = true
      clearError()
      backendResponse.value = null
      clusteringDone.value = false
      resetLog()
      markRunStarted()
      resetForFreshRunIfAborted()   // 停止后再次运行：强制从头重新上传

      try {
        if (omicsFileConfigs.value.length > 0 && !isOmicsUploaded.value) await uploadStep('正在上传组学数据…', uploadStatus, () => doUploadOmics(sessionId.value), token)
        if (isStale(token)) return
        if (clinicalFile.value && !isClinicalUploaded.value) await uploadStep('正在上传临床数据…', clinicalUploadStatus, () => doUploadClinical(sessionId.value), token)
        if (isStale(token)) return
        if (expressionMatrixFile.value && !isExpressionMatrixUploaded.value) await uploadStep('正在上传 mRNA 表达矩阵…', expressionMatrixUploadStatus, () => doUploadExpressionMatrix(sessionId.value), token)
        if (isStale(token)) return

        const formData = new FormData()
        formData.append('file', customEvalFile.value)
        formData.append('session_id', sessionId.value)

        await logStep('正在评估聚类结果…', () => evaluateCustom(formData).then(() => {}))
        if (isStale(token)) return
        clusteringDone.value = true
        await loadMetricsAndScatter(token)
        if (isStale(token)) return
        await runDownstreamAnalyses(token)
      } catch (error: any) {
        if (isStale(token)) return
        setError(error.response?.data?.detail || '评估失败，请检查数据。')
      } finally {
        if (!isStale(token)) isLoading.value = false   // 过期的旧运行不复位，避免清掉新一轮的 isLoading
      }
      return
    }

    if (omicsFileConfigs.value.length === 0) { alert('请先选择组学数据文件。'); return }
    if (selectedAlgorithm.value.length === 0) { alert('请先选择至少一种算法。'); return }

    const token = startRun()
    isLoading.value = true
    clearError()
    backendResponse.value = null
    clusteringDone.value = false
    resetLog()
    markRunStarted()
    resetForFreshRunIfAborted()   // 停止后再次运行：强制从头重新上传

    try {
      if (!isOmicsUploaded.value) await uploadStep('正在上传组学数据…', uploadStatus, () => doUploadOmics(sessionId.value), token)
      if (isStale(token)) return
      if (clinicalFile.value && !isClinicalUploaded.value) await uploadStep('正在上传临床数据…', clinicalUploadStatus, () => doUploadClinical(sessionId.value), token)
      if (isStale(token)) return
      if (expressionMatrixFile.value && !isExpressionMatrixUploaded.value) await uploadStep('正在上传 mRNA 表达矩阵…', expressionMatrixUploadStatus, () => doUploadExpressionMatrix(sessionId.value), token)
      if (isStale(token)) return

      await logStep('正在运行聚类算法…', () => runAlgorithm({
        algorithm: selectedAlgorithm.value[0]!,
        timestamp: new Date().toISOString(),
        session_id: sessionId.value,
        n_clusters: kValue.value,
        random_state: randomSeed.value,
        max_iter: maxIter.value,
        n_neighbors: nNeighbors.value,
      }))
      if (isStale(token)) return
      clusteringDone.value = true

      await loadMetricsAndScatter(token)
      if (isStale(token)) return
      await runDownstreamAnalyses(token)
    } catch (error: any) {
      if (isStale(token)) return
      setError(error.response?.data?.detail || '连接后端失败或上传出错。')
    } finally {
      if (!isStale(token)) isLoading.value = false   // 过期的旧运行不复位，避免清掉新一轮的 isLoading
    }
  }

  // 仅切换“聚类前散点图”的降维：用各自的 loading 标记，不碰全局 isLoading，避免触发“运行分析”按钮转圈。
  async function switchInputReduction(method: string) {
    if (inputReduction.value === method) return
    inputReduction.value = method

    isInputReductionLoading.value = true
    try {
      const inputRes = await renderInputClusterScatter({
        session_id: sessionId.value,
        reduction: inputReduction.value,
        random_state: randomSeed.value,
      })
      mergeIntoBackendResponse({
        plots: {
          ...(backendResponse.value?.data?.plots || {}),
          input_cluster_scatter: inputRes.data.svg,
        },
      })
    } catch (error: any) {
      setError(error.response?.data?.detail || '降维切换失败。')
    } finally {
      isInputReductionLoading.value = false
    }
  }

  // 仅切换“聚类后散点图”的降维：同样只动自己的 loading，并 merge reduction（下载/展示读这份）。
  async function switchPredReduction(method: string) {
    if (predReduction.value === method) return
    predReduction.value = method

    isPredReductionLoading.value = true
    try {
      const res = await renderPredClusterScatter({
        session_id: sessionId.value,
        reduction: predReduction.value,
        random_state: randomSeed.value,
      })
      mergeIntoBackendResponse({
        reduction: predReduction.value,
        plots: {
          ...(backendResponse.value?.data?.plots || {}),
          pred_cluster_scatter: res.data.svg,
        },
      })
    } catch (error: any) {
      setError(error.response?.data?.detail || '降维切换失败。')
    } finally {
      isPredReductionLoading.value = false
    }
  }

  async function runParameterSearchFlow() {
    if (omicsFileConfigs.value.length === 0 || !clinicalFile.value) {
      alert('测试模式需要组学数据和临床数据。')
      return
    }
    if (selectedAlgorithm.value.length === 0) { alert('请先选择至少一种算法。'); return }
    if (selectedAlgorithm.value.length > 1) { alert('测试模式请只选择一种算法。'); return }

    const token = startRun()
    isPsLoading.value = true
    psResult.value = null
    resetLog()                    // 再次运行先清空状态栏，避免残留上一次旧日志
    markRunStarted()
    resetForFreshRunIfAborted()   // 停止后再次运行：强制从头重新上传

    try {
      if (!isOmicsUploaded.value) await doUploadOmics(sessionId.value)
      if (isStale(token)) return
      if (!isClinicalUploaded.value) await doUploadClinical(sessionId.value)
      if (isStale(token)) return

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
      if (isStale(token)) return   // 停止：丢弃整网格结果，不渲染

      psResult.value = res.data
      psParam1.value = res.data.x_param || psParam1.value
      psParam2.value = res.data.y_param || ''
    } catch (error: any) {
      if (isStale(token)) return   // 停止导致的异常：不弹 alert
      alert('测试模式运行失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      if (!isStale(token)) isPsLoading.value = false   // 过期的旧运行不复位，避免清掉新一轮的 isPsLoading
    }
  }

  function abortRun() {
    invalidate()                 // 作废当前运行：在途请求返回后其结果会被各 stale 检查丢弃
    markRunningAsTerminated()    // 把转圈日志就地标记为“已停止”
    isLoading.value = false
    isPsLoading.value = false
    wasAborted.value = true      // 下一轮运行从头重来（重新上传），而非从中断处续跑
  }

  return {
    backendResponse,
    clusteringDone,
    resultsVisible,
    runAnalysisFlow,
    switchInputReduction,
    switchPredReduction,
    runParameterSearchFlow,
    abortRun,
  }
}
